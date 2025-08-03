"""Test configuration and fixtures."""

import asyncio

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.models import *  # noqa: F403 - Import all models

# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_app(test_session):
    """Create a test FastAPI application."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.core.exceptions import ProblemDetailsException, generic_exception_handler, problem_details_handler
    from app.routers import booking, departure, health, inventory, metrics, tour, waitlist

    # Create a simplified test app without lifespan
    app = FastAPI(
        title="Tour Booking API (Test)",
        description="Test version of the API",
        version="1.0.0-test",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Simplified for tests
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register exception handlers
    app.add_exception_handler(ProblemDetailsException, problem_details_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Add inline health endpoints (like in main app)
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "client-server-demo-api",
            "version": "1.0.0",
            "environment": "test",
            "debug": True,
        }

    @app.get("/ready")
    async def readiness_check():
        return {
            "status": "ready",
            "service": "client-server-demo-api",
            "checks": {
                "database": "ok",
                "dependencies": "ok",
            },
        }

    @app.get("/info")
    async def service_info():
        return {
            "service": "client-server-demo-api",
            "version": "1.0.0",
            "description": "A demonstration FastAPI server with proper structure and patterns",
            "environment": "test",
            "debug": True,
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
                "docs": None,
                "redoc": None,
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

    # Override database dependency
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    yield app

    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_client(test_app):
    """Create a test HTTP client."""
    from httpx import ASGITransport
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_tour_data():
    """Sample tour data for testing."""
    return {
        "name": "Northern Lights Adventure",
        "slug": "northern-lights-adventure",
        "description": "Experience the magical Aurora Borealis in Iceland"
    }


@pytest.fixture
def sample_departure_data():
    """Sample departure data for testing."""
    return {
        "tour_id": "tour_123",
        "starts_at": "2024-12-15T09:00:00Z",
        "capacity_total": 40,
        "price": {
            "amount": 29999,
            "currency": "USD"
        }
    }


@pytest.fixture
def sample_hold_data():
    """Sample hold data for testing."""
    return {
        "departure_id": "dep_123",
        "seats": 2,
        "customer_ref": "customer_456",
        "ttl_seconds": 600
    }
