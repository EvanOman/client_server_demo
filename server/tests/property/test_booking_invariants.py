"""Property-based tests for booking system invariants."""

from datetime import datetime, timedelta

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from app.models.booking import HoldStatus
from app.schemas.booking import ConfirmBookingRequest, CreateHoldRequest
from app.schemas.common import Money
from app.schemas.departure import CreateDepartureRequest
from app.schemas.tour import CreateTourRequest
from app.services.booking_service import BookingService
from app.services.departure_service import DepartureService
from app.services.tour_service import TourService

# Strategies for generating test data
tour_names = st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd', 'Zs')))
seat_counts = st.integers(min_value=1, max_value=10)
capacity_values = st.integers(min_value=1, max_value=1000)
ttl_values = st.integers(min_value=60, max_value=3600)


@pytest.mark.asyncio
@given(
    capacity=capacity_values,
    seat_requests=st.lists(seat_counts, min_size=1, max_size=20)
)
async def test_capacity_never_negative(test_session, capacity, seat_requests):
    """Test that departure capacity never goes negative."""
    assume(sum(seat_requests) >= capacity)  # Ensure we test over-capacity scenarios

    # Create services
    tour_service = TourService(test_session)
    departure_service = DepartureService(test_session)
    booking_service = BookingService(test_session)

    # Create tour and departure
    tour = await tour_service.create_tour(
        CreateTourRequest(
            name="Test Tour",
            slug="test-tour",
            description="Test description"
        )
    )

    departure = await departure_service.create_departure(
        CreateDepartureRequest(
            tour_id=tour.id,
            starts_at=datetime.utcnow() + timedelta(days=30),
            capacity_total=capacity,
            price=Money(amount=10000, currency="USD")
        )
    )

    # Try to create holds for all seat requests
    successful_holds = 0
    total_seats_held = 0

    for seats in seat_requests:
        try:
            hold = await booking_service.create_hold(
                CreateHoldRequest(
                    departure_id=departure.id,
                    seats=seats,
                    customer_ref=f"customer_{successful_holds}",
                    ttl_seconds=600
                ),
                idempotency_key=f"key_{successful_holds}"
            )
            if hold.status == HoldStatus.ACTIVE:
                successful_holds += 1
                total_seats_held += seats
        except Exception:
            # Expected when capacity is exceeded
            pass

    # Refresh departure from database
    updated_departure = await departure_service.get_departure_by_id(departure.id)

    # Invariants
    assert updated_departure.capacity_available >= 0
    assert updated_departure.capacity_available <= updated_departure.capacity_total
    assert total_seats_held <= capacity
    assert updated_departure.capacity_available == capacity - total_seats_held


@pytest.mark.asyncio
@given(
    seats=seat_counts,
    ttl=ttl_values
)
async def test_hold_confirm_idempotency(test_session, seats, ttl):
    """Test that confirming the same hold is idempotent."""
    # Setup
    tour_service = TourService(test_session)
    departure_service = DepartureService(test_session)
    booking_service = BookingService(test_session)

    tour = await tour_service.create_tour(
        CreateTourRequest(
            name="Test Tour",
            slug="test-tour-idempotency",
            description="Test description"
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

    # Create hold
    hold = await booking_service.create_hold(
        CreateHoldRequest(
            departure_id=departure.id,
            seats=seats,
            customer_ref="test_customer",
            ttl_seconds=ttl
        ),
        idempotency_key="test_hold_key"
    )

    # Confirm booking multiple times with same idempotency key
    booking1 = await booking_service.confirm_booking(
        ConfirmBookingRequest(
            hold_id=hold.id
        ),
        idempotency_key="test_confirm_key"
    )

    booking2 = await booking_service.confirm_booking(
        ConfirmBookingRequest(
            hold_id=hold.id
        ),
        idempotency_key="test_confirm_key"
    )

    # Should be the same booking
    assert booking1.id == booking2.id
    assert booking1.code == booking2.code
    assert booking1.seats == booking2.seats == seats


@pytest.mark.asyncio
@given(customer_refs=st.lists(st.text(min_size=1, max_size=50), min_size=2, max_size=10, unique=True))
async def test_waitlist_order_preserved(test_session, customer_refs):
    """Test that waitlist maintains FIFO order."""
    from app.services.waitlist_service import WaitlistService

    # Setup
    tour_service = TourService(test_session)
    departure_service = DepartureService(test_session)
    waitlist_service = WaitlistService(test_session)

    tour = await tour_service.create_tour(
        CreateTourRequest(
            name="Test Tour",
            slug="test-tour-waitlist",
            description="Test description"
        )
    )

    # Create departure with very limited capacity
    departure = await departure_service.create_departure(
        CreateDepartureRequest(
            tour_id=tour.id,
            starts_at=datetime.utcnow() + timedelta(days=30),
            capacity_total=1,
            price=Money(amount=10000, currency="USD")
        )
    )

    # Add customers to waitlist in order
    waitlist_entries = []
    for customer_ref in customer_refs:
        entry = await waitlist_service.join_waitlist(
            departure_id=departure.id,
            customer_ref=customer_ref
        )
        waitlist_entries.append(entry)

    # Verify order is preserved
    for i, entry in enumerate(waitlist_entries):
        assert entry.customer_ref == customer_refs[i]
        if i > 0:
            assert entry.created_at >= waitlist_entries[i-1].created_at
