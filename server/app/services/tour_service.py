"""Tour service for business logic operations."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ..models.tour import Tour
from ..schemas.tour import CreateTourRequest
from ..core.exceptions import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


class TourService:
    """Service for tour-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_tour(self, request: CreateTourRequest) -> Tour:
        """
        Create a new tour.
        
        Args:
            request: Tour creation request
            
        Returns:
            Created tour entity
            
        Raises:
            ConflictError: If tour with same slug already exists
        """
        # Check if tour with same slug already exists
        existing_tour = await self.get_tour_by_slug(request.slug)
        if existing_tour:
            logger.warning(
                "Tour creation failed - slug already exists",
                extra={
                    "slug": request.slug,
                    "existing_tour_id": str(existing_tour.id)
                }
            )
            raise ConflictError(
                detail=f"Tour with slug '{request.slug}' already exists",
                conflicting_resource={
                    "id": str(existing_tour.id),
                    "slug": existing_tour.slug,
                    "name": existing_tour.name
                }
            )
        
        # Create new tour
        tour = Tour(
            name=request.name,
            slug=request.slug,
            description=request.description
        )
        
        try:
            self.db.add(tour)
            await self.db.commit()
            await self.db.refresh(tour)
            
            logger.info(
                "Tour created successfully",
                extra={
                    "tour_id": str(tour.id),
                    "slug": tour.slug,
                    "name": tour.name
                }
            )
            
            return tour
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(
                "Tour creation failed due to integrity constraint",
                extra={
                    "slug": request.slug,
                    "name": request.name,
                    "error": str(e)
                }
            )
            # Try to get the conflicting tour for better error message
            existing_tour = await self.get_tour_by_slug(request.slug)
            if existing_tour:
                raise ConflictError(
                    detail=f"Tour with slug '{request.slug}' already exists",
                    conflicting_resource={
                        "id": str(existing_tour.id),
                        "slug": existing_tour.slug,
                        "name": existing_tour.name
                    }
                )
            else:
                # Some other constraint violation
                raise ConflictError(
                    detail="Tour creation failed due to constraint violation"
                )
    
    async def get_tour_by_id(self, tour_id: UUID) -> Optional[Tour]:
        """
        Get tour by ID.
        
        Args:
            tour_id: Tour ID to search for
            
        Returns:
            Tour if found, None otherwise
        """
        stmt = select(Tour).where(Tour.id == tour_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_tour_by_slug(self, slug: str) -> Optional[Tour]:
        """
        Get tour by slug.
        
        Args:
            slug: Tour slug to search for
            
        Returns:
            Tour if found, None otherwise
        """
        stmt = select(Tour).where(Tour.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_tour_by_id_or_raise(self, tour_id: UUID) -> Tour:
        """
        Get tour by ID or raise NotFoundError.
        
        Args:
            tour_id: Tour ID to search for
            
        Returns:
            Tour entity
            
        Raises:
            NotFoundError: If tour not found
        """
        tour = await self.get_tour_by_id(tour_id)
        if not tour:
            logger.warning(
                "Tour not found",
                extra={"tour_id": str(tour_id)}
            )
            raise NotFoundError(
                resource_type="tour",
                resource_id=str(tour_id)
            )
        return tour