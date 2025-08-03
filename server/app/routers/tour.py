"""Tour router for tour management operations."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.exceptions import ProblemDetailsException
from ..schemas.tour import CreateTourRequest, Tour
from ..services.tour_service import TourService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tour", tags=["tour"])

# Define dependencies to avoid B008 linting errors
DB_DEPENDENCY = Depends(get_db)


@router.post("/create", response_model=Tour)
async def create_tour(
    request: CreateTourRequest,
    db: AsyncSession = DB_DEPENDENCY
) -> JSONResponse:
    """
    Create a new tour.

    This operation is idempotent based on the tour slug.
    """
    tour_service = TourService(db)

    try:
        # For tour creation, we use name+slug as natural idempotency
        # Check if tour with same slug already exists
        existing_tour = await tour_service.get_tour_by_slug(request.slug)
        if existing_tour and existing_tour.name == request.name and existing_tour.description == request.description:
            # Return existing tour if name matches (idempotent)
                logger.info(
                    "Tour creation - returning existing tour (idempotent)",
                    extra={
                        "tour_id": str(existing_tour.id),
                        "slug": request.slug,
                        "tour_name": request.name
                    }
                )

                response_data = Tour(
                    id=str(existing_tour.id),
                    name=existing_tour.name,
                    slug=existing_tour.slug,
                    description=existing_tour.description
                )
                return JSONResponse(
                    status_code=200,
                    content=response_data.model_dump()
                )

        # Create new tour
        tour = await tour_service.create_tour(request)

        response_data = Tour(
            id=str(tour.id),
            name=tour.name,
            slug=tour.slug,
            description=tour.description
        )

        logger.info(
            "Tour created successfully",
            extra={
                "tour_id": str(tour.id),
                "slug": request.slug,
                "tour_name": request.name
            }
        )

        return JSONResponse(
            status_code=200,
            content=response_data.model_dump()
        )

    except ProblemDetailsException:
        # Re-raise Problem Details exceptions as-is
        raise

    except Exception as e:
        logger.error(
            "Unexpected error in tour creation",
            extra={
                "slug": request.slug,
                "name": request.name,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) from e
