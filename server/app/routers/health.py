"""Health check router."""

import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..schemas.health import HealthResponse, HealthStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/health", tags=["health"])


@router.post("/ping", response_model=HealthResponse)
async def health_ping() -> JSONResponse:
    """
    Health check endpoint.

    Returns current service status and timestamp.
    """
    response_data = HealthResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )

    logger.debug(
        "Health check requested",
        extra={
            "status": response_data.status,
            "timestamp": response_data.timestamp.isoformat()
        }
    )

    return JSONResponse(
        status_code=200,
        content=response_data.model_dump()
    )
