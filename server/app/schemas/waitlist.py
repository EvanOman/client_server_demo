"""Waitlist-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from .booking import Hold


class JoinWaitlistRequest(BaseModel):
    """Request schema for joining a waitlist."""

    departure_id: str = Field(..., description="Departure to join waitlist for")
    customer_ref: str = Field(..., max_length=128, description="Customer reference")


class NotifyWaitlistRequest(BaseModel):
    """Request schema for processing waitlist notifications."""

    departure_id: str = Field(..., description="Departure to process waitlist for")


class WaitlistEntry(BaseModel):
    """Waitlist entry response schema."""

    id: str = Field(..., description="Unique waitlist entry ID")
    departure_id: str = Field(..., description="Associated departure ID")
    customer_ref: str = Field(..., description="Customer reference")
    created_at: datetime = Field(..., description="Entry creation time (ISO 8601)")
    notified_at: datetime | None = Field(None, description="Notification time (ISO 8601)")

    class Config:
        from_attributes = True


class NotifyWaitlistResponse(BaseModel):
    """Response schema for waitlist notification processing."""

    processed_count: int = Field(..., description="Number of waitlist entries processed")
    holds_created: list[Hold] = Field(default_factory=list, description="Holds created from waitlist")
