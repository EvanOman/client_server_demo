"""Inventory-related Pydantic schemas."""

from pydantic import BaseModel, Field
from datetime import datetime


class AdjustInventoryRequest(BaseModel):
    """Request schema for adjusting inventory."""
    
    departure_id: str = Field(..., description="Departure to adjust")
    delta: int = Field(..., description="Capacity change (positive or negative)")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for adjustment")


class InventoryAdjustment(BaseModel):
    """Inventory adjustment response schema."""
    
    id: str = Field(..., description="Unique adjustment ID")
    departure_id: str = Field(..., description="Associated departure ID")
    delta: int = Field(..., description="Capacity change (positive or negative)")
    reason: str = Field(..., description="Reason for adjustment")
    created_at: datetime = Field(..., description="Adjustment time (ISO 8601)")
    actor: str = Field(..., description="User who made the adjustment")
    
    class Config:
        from_attributes = True