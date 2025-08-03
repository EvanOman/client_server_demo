"""Inventory service for capacity adjustment operations."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.inventory import InventoryAdjustment
from ..models.departure import Departure
from ..models.booking import Hold, HoldStatus
from ..schemas.inventory import AdjustInventoryRequest
from ..core.exceptions import ConflictError, NotFoundError
from .departure_service import DepartureService

logger = logging.getLogger(__name__)


class CapacityConflictError(ConflictError):
    """Exception when capacity adjustment would conflict with active holds."""
    
    def __init__(self, departure_id: str, requested_delta: int, active_holds: int, current_total: int):
        super().__init__(
            detail=f"Cannot reduce capacity by {abs(requested_delta)} seats. "
                   f"Departure {departure_id} has {active_holds} active holds and total capacity {current_total}",
            conflicting_resource={
                "departure_id": departure_id,
                "requested_delta": requested_delta,
                "active_holds": active_holds,
                "current_total_capacity": current_total
            }
        )
        self.problem_details.update({
            "code": "CAPACITY_CONFLICT",
            "retryable": False
        })


class InventoryService:
    """Service for inventory adjustment operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.departure_service = DepartureService(db)
    
    async def adjust_inventory(self, request: AdjustInventoryRequest, actor: str) -> InventoryAdjustment:
        """
        Adjust departure capacity with conflict validation.
        
        Args:
            request: Inventory adjustment request
            actor: User making the adjustment
            
        Returns:
            Created inventory adjustment record
            
        Raises:
            NotFoundError: If departure not found
            CapacityConflictError: If adjustment conflicts with active holds
        """
        departure_id_uuid = UUID(request.departure_id)
        
        # Get departure with lock to prevent race conditions
        departure = await self.departure_service.get_departure_with_lock(departure_id_uuid)
        
        # Calculate new capacity values
        new_total_capacity = departure.capacity_total + request.delta
        
        # Validate new total capacity is non-negative
        if new_total_capacity < 0:
            logger.warning(
                "Inventory adjustment failed - would result in negative total capacity",
                extra={
                    "departure_id": request.departure_id,
                    "current_total": departure.capacity_total,
                    "requested_delta": request.delta,
                    "new_total": new_total_capacity,
                    "actor": actor
                }
            )
            raise CapacityConflictError(
                departure_id=request.departure_id,
                requested_delta=request.delta,
                active_holds=0,  # Not relevant for this validation
                current_total=departure.capacity_total
            )
        
        # If reducing capacity, check if we have enough available capacity
        if request.delta < 0:
            # Count active holds
            active_holds_count = await self._count_active_holds_for_departure(departure_id_uuid)
            reduction_amount = abs(request.delta)
            
            # Check if reduction would conflict with active holds
            # We need to ensure: (current_total - reduction) >= (current_total - current_available)
            # Simplified: reduction <= current_available
            if reduction_amount > departure.capacity_available:
                logger.warning(
                    "Inventory adjustment failed - would conflict with active holds",
                    extra={
                        "departure_id": request.departure_id,
                        "requested_reduction": reduction_amount,
                        "available_capacity": departure.capacity_available,
                        "active_holds": active_holds_count,
                        "actor": actor
                    }
                )
                raise CapacityConflictError(
                    departure_id=request.departure_id,
                    requested_delta=request.delta,
                    active_holds=active_holds_count,
                    current_total=departure.capacity_total
                )
        
        # Store pre-adjustment values for audit
        capacity_total_before = departure.capacity_total
        capacity_available_before = departure.capacity_available
        
        # Apply adjustment
        departure.capacity_total = new_total_capacity
        departure.capacity_available = departure.capacity_available + request.delta
        
        # Ensure available capacity doesn't go negative (should not happen with above validations)
        if departure.capacity_available < 0:
            departure.capacity_available = 0
        
        # Ensure available capacity doesn't exceed total capacity
        if departure.capacity_available > departure.capacity_total:
            departure.capacity_available = departure.capacity_total
        
        # Create audit record
        adjustment = InventoryAdjustment(
            departure_id=departure_id_uuid,
            delta=request.delta,
            reason=request.reason,
            actor=actor,
            capacity_total_before=capacity_total_before,
            capacity_total_after=departure.capacity_total,
            capacity_available_before=capacity_available_before,
            capacity_available_after=departure.capacity_available
        )
        
        # Save changes
        self.db.add(adjustment)
        self.db.add(departure)
        
        await self.db.commit()
        await self.db.refresh(adjustment)
        
        logger.info(
            "Inventory adjustment completed successfully",
            extra={
                "adjustment_id": str(adjustment.id),
                "departure_id": request.departure_id,
                "delta": request.delta,
                "reason": request.reason,
                "actor": actor,
                "capacity_before": f"{capacity_available_before}/{capacity_total_before}",
                "capacity_after": f"{departure.capacity_available}/{departure.capacity_total}"
            }
        )
        
        return adjustment
    
    async def get_adjustment_by_id(self, adjustment_id: UUID) -> Optional[InventoryAdjustment]:
        """Get inventory adjustment by ID."""
        stmt = select(InventoryAdjustment).where(InventoryAdjustment.id == adjustment_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_adjustments_for_departure(self, departure_id: UUID) -> list[InventoryAdjustment]:
        """Get all inventory adjustments for a departure, ordered by creation time."""
        stmt = (
            select(InventoryAdjustment)
            .where(InventoryAdjustment.departure_id == departure_id)
            .order_by(InventoryAdjustment.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def _count_active_holds_for_departure(self, departure_id: UUID) -> int:
        """Count active holds for a departure."""
        stmt = select(func.count(Hold.id)).where(
            Hold.departure_id == departure_id,
            Hold.status == HoldStatus.ACTIVE,
            Hold.expires_at > datetime.utcnow()
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0