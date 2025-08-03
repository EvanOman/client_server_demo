"""Tour router for tour management operations."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.exceptions import ProblemDetailsException
from ..schemas.tour import CreateTourRequest, Tour
from ..services.tour_service import TourService
from ..services.idempotency_service import IdempotencyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tour", tags=["tour"])


@router.post("/create", response_model=Tour)
async def create_tour(
    request: CreateTourRequest,
    db: AsyncSession = Depends(get_db)
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
        if existing_tour:
            # Return existing tour if name matches (idempotent)
            if existing_tour.name == request.name and existing_tour.description == request.description:
                logger.info(
                    "Tour creation - returning existing tour (idempotent)",
                    extra={
                        "tour_id": str(existing_tour.id),
                        "slug": request.slug,
                        "name": request.name
                    }
                )
                
                response_data = Tour.model_validate(existing_tour)
                return JSONResponse(
                    status_code=200,
                    content=response_data.model_dump()
                )
        
        # Create new tour
        tour = await tour_service.create_tour(request)
        
        response_data = Tour.model_validate(tour)
        
        logger.info(
            "Tour created successfully",
            extra={
                "tour_id": str(tour.id),
                "slug": request.slug,
                "name": request.name
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
        )