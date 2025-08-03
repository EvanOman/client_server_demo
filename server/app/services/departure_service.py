"""Departure service for business logic operations."""

import logging
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.exceptions import NotFoundError
from ..models.departure import Departure
from ..schemas.departure import CreateDepartureRequest, SearchDeparturesRequest, SearchDeparturesResponse
from .tour_service import TourService

logger = logging.getLogger(__name__)


class DepartureService:
    """Service for departure-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tour_service = TourService(db)

    async def create_departure(self, request: CreateDepartureRequest) -> Departure:
        """
        Create a new departure.

        Args:
            request: Departure creation request

        Returns:
            Created departure entity

        Raises:
            NotFoundError: If tour not found
        """
        # Validate tour exists
        tour_id_uuid = UUID(request.tour_id)
        await self.tour_service.get_tour_by_id_or_raise(tour_id_uuid)

        # Create departure
        departure = Departure(
            tour_id=tour_id_uuid,
            starts_at=request.starts_at,
            capacity_total=request.capacity_total,
            capacity_available=request.capacity_total,  # Initially all capacity is available
            price_amount=request.price.amount,
            price_currency=request.price.currency
        )

        self.db.add(departure)
        await self.db.commit()
        await self.db.refresh(departure)

        logger.info(
            "Departure created successfully",
            extra={
                "departure_id": str(departure.id),
                "tour_id": str(departure.tour_id),
                "starts_at": departure.starts_at.isoformat(),
                "capacity_total": departure.capacity_total
            }
        )

        return departure

    async def search_departures(self, request: SearchDeparturesRequest) -> SearchDeparturesResponse:
        """
        Search departures based on criteria.

        Args:
            request: Search criteria

        Returns:
            Search results with pagination
        """
        # Build query
        stmt = select(Departure).options(selectinload(Departure.tour))

        # Apply filters
        conditions = []

        if request.tour_id:
            tour_id_uuid = UUID(request.tour_id)
            conditions.append(Departure.tour_id == tour_id_uuid)

        if request.date_from:
            conditions.append(Departure.starts_at >= request.date_from)

        if request.date_to:
            # Include the entire day by adding 24 hours
            from datetime import datetime, timedelta
            date_to_end = datetime.combine(request.date_to, datetime.min.time()) + timedelta(days=1)
            conditions.append(Departure.starts_at < date_to_end)

        if request.available_only:
            conditions.append(Departure.capacity_available > 0)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Apply cursor-based pagination
        if request.cursor:
            try:
                # Decode cursor (in real implementation, you'd use proper encoding)
                cursor_id = UUID(request.cursor)
                stmt = stmt.where(Departure.id > cursor_id)
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid cursor provided in departure search",
                    extra={"cursor": request.cursor}
                )
                # Invalid cursor, ignore it
                pass

        # Order by ID for consistent pagination
        stmt = stmt.order_by(Departure.id)

        # Limit results (fetch one extra to determine if there's a next page)
        stmt = stmt.limit(request.limit + 1)

        # Execute query
        result = await self.db.execute(stmt)
        departures = list(result.scalars())

        # Determine if there's a next page
        has_next_page = len(departures) > request.limit
        if has_next_page:
            departures = departures[:-1]  # Remove the extra item

        # Generate next cursor
        next_cursor = None
        if has_next_page and departures:
            next_cursor = str(departures[-1].id)

        logger.info(
            "Departure search completed",
            extra={
                "total_found": len(departures),
                "has_next_page": has_next_page,
                "filters": {
                    "tour_id": request.tour_id,
                    "date_from": request.date_from.isoformat() if request.date_from else None,
                    "date_to": request.date_to.isoformat() if request.date_to else None,
                    "available_only": request.available_only
                }
            }
        )

        return SearchDeparturesResponse(
            items=departures,
            next_cursor=next_cursor
        )

    async def get_departure_by_id(self, departure_id: UUID) -> Departure | None:
        """
        Get departure by ID.

        Args:
            departure_id: Departure ID to search for

        Returns:
            Departure if found, None otherwise
        """
        stmt = select(Departure).where(Departure.id == departure_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_departure_by_id_or_raise(self, departure_id: UUID) -> Departure:
        """
        Get departure by ID or raise NotFoundError.

        Args:
            departure_id: Departure ID to search for

        Returns:
            Departure entity

        Raises:
            NotFoundError: If departure not found
        """
        departure = await self.get_departure_by_id(departure_id)
        if not departure:
            logger.warning(
                "Departure not found",
                extra={"departure_id": str(departure_id)}
            )
            raise NotFoundError(
                resource_type="departure",
                resource_id=str(departure_id)
            )
        return departure

    async def get_departure_with_lock(self, departure_id: UUID) -> Departure:
        """
        Get departure by ID with advisory lock for capacity modifications.

        Args:
            departure_id: Departure ID to search for

        Returns:
            Departure entity with lock held

        Raises:
            NotFoundError: If departure not found
        """
        # Use PostgreSQL advisory lock to serialize operations on this departure
        # The lock will be automatically released at transaction end
        # Skip advisory locks for SQLite (used in tests)
        if self.db.bind and "postgresql" in str(self.db.bind.dialect.name):
            from sqlalchemy import text
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:departure_id))"),
                {"departure_id": str(departure_id)}
            )

        departure = await self.get_departure_by_id_or_raise(departure_id)

        logger.debug(
            "Acquired advisory lock for departure",
            extra={"departure_id": str(departure_id)}
        )

        return departure
