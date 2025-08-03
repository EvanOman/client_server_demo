"""Waitlist service for business logic operations."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..models.waitlist import WaitlistEntry
from ..models.booking import Hold, HoldStatus
from ..schemas.waitlist import JoinWaitlistRequest, NotifyWaitlistRequest, NotifyWaitlistResponse
from ..schemas.booking import CreateHoldRequest
from ..core.exceptions import NotFoundError
from .departure_service import DepartureService
from .booking_service import BookingService

logger = logging.getLogger(__name__)


class WaitlistService:
    """Service for waitlist-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.departure_service = DepartureService(db)
        self.booking_service = BookingService(db)
    
    async def join_waitlist(self, request: JoinWaitlistRequest) -> WaitlistEntry:
        """
        Join departure waitlist (idempotent by customer_ref + departure_id).
        
        Args:
            request: Waitlist join request
            
        Returns:
            Waitlist entry (existing or new)
            
        Raises:
            NotFoundError: If departure not found
        """
        departure_id_uuid = UUID(request.departure_id)
        
        # Validate departure exists
        await self.departure_service.get_departure_by_id_or_raise(departure_id_uuid)
        
        # Check if customer is already on waitlist (idempotent behavior)
        existing_entry = await self.get_waitlist_entry_by_customer_and_departure(
            request.customer_ref, departure_id_uuid
        )
        
        if existing_entry:
            logger.info(
                "Customer already on waitlist - returning existing entry",
                extra={
                    "waitlist_entry_id": str(existing_entry.id),
                    "departure_id": request.departure_id,
                    "customer_ref": request.customer_ref,
                    "created_at": existing_entry.created_at.isoformat()
                }
            )
            return existing_entry
        
        # Create new waitlist entry
        entry = WaitlistEntry(
            departure_id=departure_id_uuid,
            customer_ref=request.customer_ref
        )
        
        try:
            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)
            
            logger.info(
                "Customer joined waitlist successfully",
                extra={
                    "waitlist_entry_id": str(entry.id),
                    "departure_id": request.departure_id,
                    "customer_ref": request.customer_ref
                }
            )
            
            return entry
            
        except IntegrityError:
            # Race condition - another request created the entry
            await self.db.rollback()
            
            # Fetch the existing entry
            existing_entry = await self.get_waitlist_entry_by_customer_and_departure(
                request.customer_ref, departure_id_uuid
            )
            
            if existing_entry:
                logger.info(
                    "Waitlist entry created by concurrent request - returning existing",
                    extra={
                        "waitlist_entry_id": str(existing_entry.id),
                        "departure_id": request.departure_id,
                        "customer_ref": request.customer_ref
                    }
                )
                return existing_entry
            else:
                # Unexpected integrity error
                logger.error(
                    "Unexpected integrity error when joining waitlist",
                    extra={
                        "departure_id": request.departure_id,
                        "customer_ref": request.customer_ref
                    }
                )
                raise
    
    async def notify_waitlist(self, request: NotifyWaitlistRequest) -> NotifyWaitlistResponse:
        """
        Process waitlist notifications when capacity becomes available.
        Creates short-TTL holds for waitlisted customers.
        
        Args:
            request: Waitlist notification request
            
        Returns:
            Notification processing results
        """
        departure_id_uuid = UUID(request.departure_id)
        
        # Get departure with lock
        departure = await self.departure_service.get_departure_with_lock(departure_id_uuid)
        
        # Get unnotified waitlist entries in FIFO order
        stmt = (
            select(WaitlistEntry)
            .where(
                WaitlistEntry.departure_id == departure_id_uuid,
                WaitlistEntry.notified_at.is_(None)
            )
            .order_by(WaitlistEntry.created_at)
            .limit(departure.capacity_available)  # Only process as many as we have capacity
        )
        
        result = await self.db.execute(stmt)
        waitlist_entries = list(result.scalars())
        
        if not waitlist_entries:
            logger.info(
                "No unnotified waitlist entries to process",
                extra={
                    "departure_id": request.departure_id,
                    "available_capacity": departure.capacity_available
                }
            )
            return NotifyWaitlistResponse(
                processed_count=0,
                holds_created=[]
            )
        
        # Create short-TTL holds for waitlisted customers
        holds_created = []
        processed_count = 0
        current_time = datetime.utcnow()
        
        for entry in waitlist_entries:
            if departure.capacity_available <= 0:
                # No more capacity available
                break
            
            try:
                # Create a short-TTL hold (5 minutes) for waitlisted customer
                hold_request = CreateHoldRequest(
                    departure_id=request.departure_id,
                    seats=1,  # Waitlist typically handles 1 seat at a time
                    customer_ref=entry.customer_ref,
                    ttl_seconds=300  # 5 minutes
                )
                
                # Generate idempotency key for the hold
                idempotency_key = f"waitlist-{entry.id}-{int(current_time.timestamp())}"
                
                # Create hold
                hold = await self.booking_service.create_hold(hold_request, idempotency_key)
                holds_created.append(hold)
                
                # Mark waitlist entry as notified
                entry.notified_at = current_time
                self.db.add(entry)
                
                # Update available capacity (already updated by create_hold)
                departure.capacity_available -= 1
                
                processed_count += 1
                
                logger.info(
                    "Created hold for waitlisted customer",
                    extra={
                        "waitlist_entry_id": str(entry.id),
                        "hold_id": str(hold.id),
                        "customer_ref": entry.customer_ref,
                        "departure_id": request.departure_id,
                        "expires_at": hold.expires_at.isoformat()
                    }
                )
                
            except Exception as e:
                logger.error(
                    "Failed to create hold for waitlisted customer",
                    extra={
                        "waitlist_entry_id": str(entry.id),
                        "customer_ref": entry.customer_ref,
                        "departure_id": request.departure_id,
                        "error": str(e)
                    }
                )
                # Continue processing other entries
                continue
        
        if processed_count > 0:
            await self.db.commit()
            
            logger.info(
                "Waitlist notification processing completed",
                extra={
                    "departure_id": request.departure_id,
                    "processed_count": processed_count,
                    "holds_created": len(holds_created),
                    "remaining_capacity": departure.capacity_available
                }
            )
        
        return NotifyWaitlistResponse(
            processed_count=processed_count,
            holds_created=holds_created
        )
    
    async def get_waitlist_entry_by_id(self, entry_id: UUID) -> Optional[WaitlistEntry]:
        """Get waitlist entry by ID."""
        stmt = select(WaitlistEntry).where(WaitlistEntry.id == entry_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_waitlist_entry_by_customer_and_departure(
        self, customer_ref: str, departure_id: UUID
    ) -> Optional[WaitlistEntry]:
        """Get waitlist entry by customer reference and departure ID."""
        stmt = select(WaitlistEntry).where(
            WaitlistEntry.customer_ref == customer_ref,
            WaitlistEntry.departure_id == departure_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_waitlist_for_departure(self, departure_id: UUID) -> List[WaitlistEntry]:
        """Get all waitlist entries for a departure, ordered by creation time."""
        stmt = (
            select(WaitlistEntry)
            .where(WaitlistEntry.departure_id == departure_id)
            .order_by(WaitlistEntry.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def get_unnotified_waitlist_count(self, departure_id: UUID) -> int:
        """Get count of unnotified waitlist entries for a departure."""
        from sqlalchemy import func
        
        stmt = select(func.count(WaitlistEntry.id)).where(
            WaitlistEntry.departure_id == departure_id,
            WaitlistEntry.notified_at.is_(None)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0