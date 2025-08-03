"""Booking-related Pydantic schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class HoldStatus(str, Enum):
    """Hold status enumeration."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"


class BookingStatus(str, Enum):
    """Booking status enumeration."""
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"


class CreateHoldRequest(BaseModel):
    """Request schema for creating a hold."""
    
    departure_id: str = Field(..., description="Departure to hold seats for")
    seats: int = Field(..., ge=1, le=10, description="Number of seats to hold")
    customer_ref: str = Field(..., max_length=128, description="Customer reference")
    ttl_seconds: int = Field(600, ge=60, le=3600, description="Hold duration in seconds")


class ConfirmBookingRequest(BaseModel):
    """Request schema for confirming a booking."""
    
    hold_id: str = Field(..., description="Hold to confirm")


class CancelBookingRequest(BaseModel):
    """Request schema for cancelling a booking."""
    
    booking_id: str = Field(..., description="Booking to cancel")


class GetBookingRequest(BaseModel):
    """Request schema for getting a booking."""
    
    booking_id: str = Field(..., description="Booking to retrieve")


class Hold(BaseModel):
    """Hold response schema."""
    
    id: str = Field(..., description="Unique hold ID")
    departure_id: str = Field(..., description="Associated departure ID")
    seats: int = Field(..., ge=1, description="Number of seats held")
    customer_ref: str = Field(..., description="Customer reference")
    status: HoldStatus = Field(..., description="Hold status")
    expires_at: datetime = Field(..., description="Hold expiration time (ISO 8601)")
    
    class Config:
        from_attributes = True


class Booking(BaseModel):
    """Booking response schema."""
    
    id: str = Field(..., description="Unique booking ID")
    hold_id: str = Field(..., description="Associated hold ID")
    code: str = Field(..., description="Booking confirmation code")
    seats: int = Field(..., ge=1, description="Number of seats booked")
    customer_ref: str = Field(..., description="Customer reference")
    status: BookingStatus = Field(..., description="Booking status")
    created_at: datetime = Field(..., description="Booking creation time (ISO 8601)")
    
    class Config:
        from_attributes = True