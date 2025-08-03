"""Health-related Pydantic schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: HealthStatus = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current server time (ISO 8601)")
    version: str = Field("1.0.0", description="API version")
