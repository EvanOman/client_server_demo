"""FastAPI application initialization and configuration."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import close_db, init_db
from .core.exceptions import (
    ProblemDetailsException,
    generic_exception_handler,
    problem_details_handler,
)
from .core.middleware import setup_middleware
from .core.observability import (
    instrument_fastapi,
    instrument_sqlalchemy,
    setup_metrics,
    setup_structured_logging,
    setup_tracing,
)
from .routers import booking, departure, health, inventory, metrics, tour, waitlist
from .workers.manager import worker_manager

# Configure structured logging
setup_structured_logging()

# Configure traditional logging for compatibility
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting FastAPI application")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    try:
        # Setup observability
        setup_tracing("tour-booking-api")
        setup_metrics("tour-booking-api")
        instrument_sqlalchemy()
        logger.info("Observability setup completed")

        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")

        # Start background workers
        await worker_manager.start_all()
        logger.info("Background workers started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application")

    try:
        # Stop background workers
        await worker_manager.stop_all()
        logger.info("Background workers stopped")

        # Close database connections
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during application cleanup: {e}")

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Tour Booking API",
        description="RPC-over-HTTP API for seat-limited tour bookings with time-bound reservation holds, waitlists, and inventory adjustments",
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan,
        # Disable default exception handlers to use our custom ones
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "traceparent", "tracestate"],
    )

    # Setup custom middleware
    setup_middleware(app, enable_logging=True)

    # Instrument FastAPI with OpenTelemetry
    instrument_fastapi(app)

    # Register exception handlers
    app.add_exception_handler(ProblemDetailsException, problem_details_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Health check endpoint (inline)
    @app.get(
        "/health",
        status_code=status.HTTP_200_OK,
        tags=["Health"],
        summary="Health Check",
        description="Check if the service is healthy and responsive",
        response_model=dict,
    )
    async def health_check():
        """
        Health check endpoint that returns service status.

        Returns:
            dict: Health status information
        """
        return {
            "status": "healthy",
            "service": "client-server-demo-api",
            "version": "1.0.0",
            "environment": settings.environment,
            "debug": settings.debug,
        }

    # Readiness check endpoint (inline)
    @app.get(
        "/ready",
        status_code=status.HTTP_200_OK,
        tags=["Health"],
        summary="Readiness Check",
        description="Check if the service is ready to accept requests",
        response_model=dict,
    )
    async def readiness_check():
        """
        Readiness check endpoint that verifies service dependencies.

        Returns:
            dict: Readiness status information
        """
        # TODO: Add actual dependency checks (database, external services, etc.)
        return {
            "status": "ready",
            "service": "client-server-demo-api",
            "checks": {
                "database": "ok",  # Would check actual database connection
                "dependencies": "ok",  # Would check external service dependencies
            },
        }

    # Info endpoint (inline)
    @app.get(
        "/info",
        status_code=status.HTTP_200_OK,
        tags=["Info"],
        summary="Service Information",
        description="Get detailed information about the service",
        response_model=dict,
    )
    async def service_info():
        """
        Service information endpoint.

        Returns:
            dict: Detailed service information
        """
        return {
            "service": "client-server-demo-api",
            "version": "1.0.0",
            "description": "A demonstration FastAPI server with proper structure and patterns",
            "environment": settings.environment,
            "debug": settings.debug,
            "features": {
                "authentication": True,
                "idempotency": True,
                "tracing": True,
                "problem_details": True,
            },
            "endpoints": {
                "health": "/health",
                "readiness": "/ready",
                "info": "/info",
                "docs": "/docs" if settings.debug else None,
                "redoc": "/redoc" if settings.debug else None,
            },
        }

    # Register API routers
    app.include_router(health.router)
    app.include_router(tour.router)
    app.include_router(departure.router)
    app.include_router(booking.router)
    app.include_router(waitlist.router)
    app.include_router(inventory.router)
    app.include_router(metrics.router)

    logger.info("FastAPI application created and configured")

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )
