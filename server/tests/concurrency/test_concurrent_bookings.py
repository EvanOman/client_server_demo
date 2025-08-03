"""Concurrency tests for booking operations."""

import asyncio
from datetime import datetime, timedelta

import pytest

from app.schemas.booking import CreateHoldRequest, ConfirmBookingRequest, CancelBookingRequest
from app.schemas.departure import CreateDepartureRequest
from app.schemas.tour import CreateTourRequest
from app.schemas.common import Money
from app.services.booking_service import BookingService
from app.services.departure_service import DepartureService
from app.services.tour_service import TourService


@pytest.mark.asyncio
async def test_concurrent_holds_no_overbooking(test_session):
    """Test that concurrent hold requests don't cause overbooking."""
    # Setup
    tour_service = TourService(test_session)
    departure_service = DepartureService(test_session)

    tour = await tour_service.create_tour(
        CreateTourRequest(
            name="Concurrent Test Tour",
            slug="concurrent-test-tour",
            description="Test concurrent holds"
        )
    )

    departure = await departure_service.create_departure(
        CreateDepartureRequest(
            tour_id=tour.id,
            starts_at=datetime.utcnow() + timedelta(days=30),
            capacity_total=50,  # Limited capacity to test race conditions
            price=Money(amount=10000, currency="USD")
        )
    )

    # Create multiple booking services (simulating different requests)
    num_concurrent_requests = 100
    seats_per_request = 1

    async def create_hold(customer_id: int):
        """Create a hold for a specific customer."""
        booking_service = BookingService(test_session)
        try:
            hold = await booking_service.create_hold(
                CreateHoldRequest(
                    departure_id=departure.id,
                    seats=seats_per_request,
                    customer_ref=f"customer_{customer_id}",
                    ttl_seconds=600
                ),
                idempotency_key=f"concurrent_key_{customer_id}"
            )
            return hold
        except Exception:
            # Some requests should fail when capacity is exceeded
            return None

    # Execute concurrent hold requests
    tasks = [create_hold(i) for i in range(num_concurrent_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count successful holds
    successful_holds = [r for r in results if r is not None and not isinstance(r, Exception)]

    # Verify no overbooking occurred
    assert len(successful_holds) <= 50  # Should not exceed capacity

    # Verify final departure state
    final_departure = await departure_service.get_departure_by_id(departure.id)
    assert final_departure.capacity_available >= 0
    assert final_departure.capacity_available == 50 - len(successful_holds)


@pytest.mark.asyncio
async def test_concurrent_hold_and_cancel(test_session):
    """Test concurrent hold creation and cancellation."""
    # Setup
    tour_service = TourService(test_session)
    departure_service = DepartureService(test_session)
    booking_service = BookingService(test_session)

    tour = await tour_service.create_tour(
        CreateTourRequest(
            name="Hold Cancel Test Tour",
            slug="hold-cancel-test-tour",
            description="Test hold and cancel operations"
        )
    )

    departure = await departure_service.create_departure(
        CreateDepartureRequest(
            tour_id=tour.id,
            starts_at=datetime.utcnow() + timedelta(days=30),
            capacity_total=20,
            price=Money(amount=10000, currency="USD")
        )
    )

    # Create initial holds
    initial_holds = []
    for i in range(10):
        hold = await booking_service.create_hold(
            CreateHoldRequest(
                departure_id=departure.id,
                seats=1,
                customer_ref=f"initial_customer_{i}",
                ttl_seconds=600
            ),
            idempotency_key=f"initial_key_{i}"
        )
        initial_holds.append(hold)

    async def create_new_hold(customer_id: int):
        """Try to create a new hold."""
        try:
            hold = await booking_service.create_hold(
                CreateHoldRequest(
                    departure_id=departure.id,
                    seats=1,
                    customer_ref=f"new_customer_{customer_id}",
                    ttl_seconds=600
                ),
                idempotency_key=f"new_key_{customer_id}"
            )
            return ("create", hold)
        except Exception:
            return ("create", None)

    async def cancel_existing_hold(hold_index: int):
        """Cancel an existing hold."""
        try:
            if hold_index < len(initial_holds):
                booking = await booking_service.confirm_booking(
                    ConfirmBookingRequest(
                        hold_id=initial_holds[hold_index].id
                    ),
                    idempotency_key=f"confirm_key_{hold_index}"
                )
                cancelled = await booking_service.cancel_booking(
                    CancelBookingRequest(
                        booking_id=booking.id
                    ),
                    idempotency_key=f"cancel_key_{hold_index}"
                )
                return ("cancel", cancelled)
        except Exception:
            pass
        return ("cancel", None)

    # Mix of create and cancel operations
    tasks = []
    for i in range(20):
        if i % 2 == 0:
            tasks.append(create_new_hold(i))
        else:
            tasks.append(cancel_existing_hold(i // 2))

    await asyncio.gather(*tasks, return_exceptions=True)

    # Verify capacity consistency
    final_departure = await departure_service.get_departure_by_id(departure.id)
    assert final_departure.capacity_available >= 0
    assert final_departure.capacity_available <= final_departure.capacity_total


@pytest.mark.asyncio
async def test_concurrent_idempotent_operations(test_session):
    """Test that idempotent operations work correctly under concurrency."""
    # Setup
    tour_service = TourService(test_session)
    departure_service = DepartureService(test_session)
    booking_service = BookingService(test_session)

    tour = await tour_service.create_tour(
        CreateTourRequest(
            name="Idempotency Test Tour",
            slug="idempotency-test-tour",
            description="Test idempotent operations"
        )
    )

    departure = await departure_service.create_departure(
        CreateDepartureRequest(
            tour_id=tour.id,
            starts_at=datetime.utcnow() + timedelta(days=30),
            capacity_total=100,
            price=Money(amount=10000, currency="USD")
        )
    )

    # Same idempotency key used by multiple concurrent requests
    idempotency_key = "shared_idempotent_key"

    async def create_hold_with_same_key():
        """Create hold with the same idempotency key."""
        try:
            hold = await booking_service.create_hold(
                CreateHoldRequest(
                    departure_id=departure.id,
                    seats=5,
                    customer_ref="shared_customer",
                    ttl_seconds=600
                ),
                idempotency_key=idempotency_key
            )
            return hold
        except Exception:
            return None

    # Execute 10 concurrent requests with same idempotency key
    tasks = [create_hold_with_same_key() for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter successful results
    successful_holds = [r for r in results if r is not None and not isinstance(r, Exception)]

    # All should return the same hold (idempotency)
    if successful_holds:
        first_hold = successful_holds[0]
        for hold in successful_holds[1:]:
            assert hold.id == first_hold.id
            assert hold.seats == first_hold.seats
            assert hold.customer_ref == first_hold.customer_ref

    # Verify only one hold was actually created (capacity should only decrease by 5)
    final_departure = await departure_service.get_departure_by_id(departure.id)
    assert final_departure.capacity_available == 95  # 100 - 5
