"""Booking service for business logic operations."""

import logging
import secrets
import string
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.exceptions import ConflictError, NotFoundError
from ..models.booking import Booking, BookingStatus, Hold, HoldStatus
from ..schemas.booking import CancelBookingRequest, ConfirmBookingRequest, CreateHoldRequest, GetBookingRequest
from .departure_service import DepartureService

logger = logging.getLogger(__name__)


class CapacityFullError(ConflictError):
    """Exception when departure capacity is full."""

    def __init__(self, departure_id: str, requested_seats: int, available_seats: int):
        super().__init__(
            detail=f"Departure {departure_id} has insufficient capacity. Requested: {requested_seats}, Available: {available_seats}",
            conflicting_resource={
                "departure_id": departure_id,
                "requested_seats": requested_seats,
                "available_seats": available_seats
            }
        )
        self.problem_details.update({
            "code": "FULL",
            "retryable": False
        })


class HoldExpiredError(ConflictError):
    """Exception when hold has expired."""

    def __init__(self, hold_id: str, expired_at: datetime):
        super().__init__(
            detail=f"Hold {hold_id} expired at {expired_at.isoformat()}Z"
        )
        self.problem_details.update({
            "code": "HOLD_EXPIRED",
            "retryable": False,
            "hold_id": hold_id,
            "expired_at": expired_at.isoformat() + "Z"
        })


class BookingService:
    """Service for booking-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.departure_service = DepartureService(db)

    def _generate_booking_code(self, length: int = 8) -> str:
        """Generate a random booking confirmation code."""
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    async def create_hold(self, request: CreateHoldRequest, idempotency_key: str) -> Hold:
        """
        Create a seat hold with capacity validation and atomic updates.

        Args:
            request: Hold creation request
            idempotency_key: Idempotency key for this operation

        Returns:
            Created hold entity

        Raises:
            NotFoundError: If departure not found
            CapacityFullError: If insufficient capacity available
        """
        departure_id_uuid = UUID(request.departure_id)

        # Get departure with advisory lock to prevent race conditions
        departure = await self.departure_service.get_departure_with_lock(departure_id_uuid)

        # Check capacity
        if departure.capacity_available < request.seats:
            logger.warning(
                "Hold creation failed - insufficient capacity",
                extra={
                    "departure_id": request.departure_id,
                    "requested_seats": request.seats,
                    "available_capacity": departure.capacity_available,
                    "idempotency_key": idempotency_key
                }
            )
            raise CapacityFullError(
                departure_id=request.departure_id,
                requested_seats=request.seats,
                available_seats=departure.capacity_available
            )

        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=request.ttl_seconds)

        # Create hold
        hold = Hold(
            departure_id=departure_id_uuid,
            seats=request.seats,
            customer_ref=request.customer_ref,
            expires_at=expires_at,
            status=HoldStatus.ACTIVE,
            idempotency_key=idempotency_key
        )

        # Update departure capacity atomically
        departure.capacity_available -= request.seats

        # Save both entities
        self.db.add(hold)
        self.db.add(departure)

        await self.db.commit()
        await self.db.refresh(hold)

        logger.info(
            "Hold created successfully",
            extra={
                "hold_id": str(hold.id),
                "departure_id": request.departure_id,
                "seats": request.seats,
                "customer_ref": request.customer_ref,
                "expires_at": expires_at.isoformat(),
                "remaining_capacity": departure.capacity_available,
                "idempotency_key": idempotency_key
            }
        )

        return hold

    async def confirm_booking(self, request: ConfirmBookingRequest, idempotency_key: str) -> Booking:
        """
        Confirm a booking from an active hold.

        Args:
            request: Booking confirmation request
            idempotency_key: Idempotency key for this operation

        Returns:
            Created booking entity

        Raises:
            NotFoundError: If hold not found
            HoldExpiredError: If hold has expired
            ConflictError: If hold is not in ACTIVE status
        """
        hold_id_uuid = UUID(request.hold_id)

        # Get hold with related departure
        stmt = select(Hold).options(selectinload(Hold.departure)).where(Hold.id == hold_id_uuid)
        result = await self.db.execute(stmt)
        hold = result.scalar_one_or_none()

        if not hold:
            logger.warning(
                "Hold not found for booking confirmation",
                extra={
                    "hold_id": request.hold_id,
                    "idempotency_key": idempotency_key
                }
            )
            raise NotFoundError(
                resource_type="hold",
                resource_id=request.hold_id
            )

        # Check if hold is expired
        current_time = datetime.utcnow()
        if hold.expires_at <= current_time:
            logger.warning(
                "Booking confirmation failed - hold expired",
                extra={
                    "hold_id": request.hold_id,
                    "expired_at": hold.expires_at.isoformat(),
                    "current_time": current_time.isoformat(),
                    "idempotency_key": idempotency_key
                }
            )
            raise HoldExpiredError(request.hold_id, hold.expires_at)

        # Check hold status
        if hold.status != HoldStatus.ACTIVE:
            logger.warning(
                "Booking confirmation failed - hold not active",
                extra={
                    "hold_id": request.hold_id,
                    "hold_status": hold.status,
                    "idempotency_key": idempotency_key
                }
            )
            raise ConflictError(
                detail=f"Hold {request.hold_id} is not active (status: {hold.status})"
            )

        # Check if booking already exists (idempotent behavior)
        existing_booking = await self.get_booking_by_hold_id(hold_id_uuid)
        if existing_booking:
            logger.info(
                "Booking already exists for hold - returning existing booking",
                extra={
                    "hold_id": request.hold_id,
                    "booking_id": str(existing_booking.id),
                    "idempotency_key": idempotency_key
                }
            )
            return existing_booking

        # Generate unique booking code
        booking_code = self._generate_booking_code()
        while await self.get_booking_by_code(booking_code):
            booking_code = self._generate_booking_code()

        # Create booking
        booking = Booking(
            hold_id=hold_id_uuid,
            departure_id=hold.departure_id,
            code=booking_code,
            seats=hold.seats,
            customer_ref=hold.customer_ref,
            status=BookingStatus.CONFIRMED
        )

        # Update hold status
        hold.status = HoldStatus.CONFIRMED

        # Save entities
        self.db.add(booking)
        self.db.add(hold)

        await self.db.commit()
        await self.db.refresh(booking)

        logger.info(
            "Booking confirmed successfully",
            extra={
                "booking_id": str(booking.id),
                "booking_code": booking.code,
                "hold_id": request.hold_id,
                "seats": booking.seats,
                "customer_ref": booking.customer_ref,
                "idempotency_key": idempotency_key
            }
        )

        return booking

    async def cancel_booking(self, request: CancelBookingRequest, idempotency_key: str) -> Booking:
        """
        Cancel a booking and restore capacity.

        Args:
            request: Booking cancellation request
            idempotency_key: Idempotency key for this operation

        Returns:
            Cancelled booking entity

        Raises:
            NotFoundError: If booking not found
            ConflictError: If booking is already cancelled
        """
        booking_id_uuid = UUID(request.booking_id)

        # Get booking with related entities and lock departure
        booking = await self.get_booking_by_id_or_raise(booking_id_uuid)
        departure = await self.departure_service.get_departure_with_lock(booking.departure_id)

        # Check if already cancelled (idempotent behavior)
        if booking.status == BookingStatus.CANCELED:
            logger.info(
                "Booking already cancelled - returning existing booking",
                extra={
                    "booking_id": request.booking_id,
                    "idempotency_key": idempotency_key
                }
            )
            return booking

        # Cancel booking
        booking.status = BookingStatus.CANCELED

        # Restore capacity
        departure.capacity_available += booking.seats

        # Update hold status
        stmt = update(Hold).where(Hold.id == booking.hold_id).values(status=HoldStatus.CANCELED)
        await self.db.execute(stmt)

        # Save entities
        self.db.add(booking)
        self.db.add(departure)

        await self.db.commit()
        await self.db.refresh(booking)

        logger.info(
            "Booking cancelled successfully",
            extra={
                "booking_id": request.booking_id,
                "booking_code": booking.code,
                "seats_restored": booking.seats,
                "new_available_capacity": departure.capacity_available,
                "idempotency_key": idempotency_key
            }
        )

        return booking

    async def get_booking(self, request: GetBookingRequest) -> Booking:
        """
        Get booking by ID.

        Args:
            request: Get booking request

        Returns:
            Booking entity

        Raises:
            NotFoundError: If booking not found
        """
        booking_id_uuid = UUID(request.booking_id)
        return await self.get_booking_by_id_or_raise(booking_id_uuid)

    async def get_booking_by_id(self, booking_id: UUID) -> Booking | None:
        """Get booking by ID."""
        stmt = select(Booking).where(Booking.id == booking_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_booking_by_id_or_raise(self, booking_id: UUID) -> Booking:
        """Get booking by ID or raise NotFoundError."""
        booking = await self.get_booking_by_id(booking_id)
        if not booking:
            logger.warning(
                "Booking not found",
                extra={"booking_id": str(booking_id)}
            )
            raise NotFoundError(
                resource_type="booking",
                resource_id=str(booking_id)
            )
        return booking

    async def get_booking_by_hold_id(self, hold_id: UUID) -> Booking | None:
        """Get booking by hold ID."""
        stmt = select(Booking).where(Booking.hold_id == hold_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_booking_by_code(self, code: str) -> Booking | None:
        """Get booking by confirmation code."""
        stmt = select(Booking).where(Booking.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_hold_by_id(self, hold_id: UUID) -> Hold | None:
        """Get hold by ID."""
        stmt = select(Hold).where(Hold.id == hold_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def expire_holds(self, batch_size: int = 100) -> int:
        """
        Expire holds that have passed their TTL and restore capacity.

        Args:
            batch_size: Number of holds to process in one batch

        Returns:
            Number of holds expired
        """
        current_time = datetime.utcnow()

        # Find expired active holds
        stmt = (
            select(Hold)
            .options(selectinload(Hold.departure))
            .where(
                Hold.status == HoldStatus.ACTIVE,
                Hold.expires_at <= current_time
            )
            .limit(batch_size)
        )

        result = await self.db.execute(stmt)
        expired_holds = list(result.scalars())

        expired_count = 0

        for hold in expired_holds:
            try:
                # Get departure with lock
                departure = await self.departure_service.get_departure_with_lock(hold.departure_id)

                # Update hold status
                hold.status = HoldStatus.EXPIRED

                # Restore capacity
                departure.capacity_available += hold.seats

                # Save changes
                self.db.add(hold)
                self.db.add(departure)

                expired_count += 1

                logger.info(
                    "Hold expired and capacity restored",
                    extra={
                        "hold_id": str(hold.id),
                        "departure_id": str(hold.departure_id),
                        "seats_restored": hold.seats,
                        "new_available_capacity": departure.capacity_available,
                        "expired_at": hold.expires_at.isoformat()
                    }
                )

            except Exception as e:
                logger.error(
                    "Failed to expire hold",
                    extra={
                        "hold_id": str(hold.id),
                        "error": str(e)
                    }
                )
                await self.db.rollback()
                continue

        if expired_count > 0:
            await self.db.commit()
            logger.info(
                "Hold expiration batch completed",
                extra={
                    "expired_count": expired_count,
                    "batch_size": batch_size
                }
            )

        return expired_count
