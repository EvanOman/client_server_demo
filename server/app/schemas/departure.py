"""Departure-related Pydantic schemas."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from .common import Money, PaginatedResponse


class CreateDepartureRequest(BaseModel):
    """Request schema for creating a departure."""

    tour_id: str = Field(..., description="Associated tour ID")
    starts_at: datetime = Field(..., description="Departure start time (ISO 8601)")
    capacity_total: int = Field(..., ge=1, le=1000, description="Total capacity")
    price: Money = Field(..., description="Price information")


class SearchDeparturesRequest(BaseModel):
    """Request schema for searching departures."""

    tour_id: str | None = Field(None, description="Filter by tour ID")
    date_from: date | None = Field(None, description="Start date filter")
    date_to: date | None = Field(None, description="End date filter")
    available_only: bool = Field(False, description="Only show departures with availability")
    cursor: str | None = Field(None, description="Pagination cursor")
    limit: int = Field(20, ge=1, le=100, description="Results per page")


class Departure(BaseModel):
    """Departure response schema."""

    id: str = Field(..., description="Unique departure ID")
    tour_id: str = Field(..., description="Associated tour ID")
    starts_at: datetime = Field(..., description="Departure start time (ISO 8601)")
    capacity_total: int = Field(..., ge=1, description="Total capacity")
    capacity_available: int = Field(..., ge=0, description="Available capacity")
    price: Money = Field(..., description="Price information")

    class Config:
        from_attributes = True


class SearchDeparturesResponse(PaginatedResponse):
    """Response schema for departure search."""

    items: list[Departure] = Field(..., description="Found departures")
