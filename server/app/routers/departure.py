"""Departure router for departure management operations."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.exceptions import ProblemDetailsException
from ..schemas.departure import CreateDepartureRequest, SearchDeparturesRequest, Departure, SearchDeparturesResponse
from ..schemas.common import Money
from ..services.departure_service import DepartureService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/departure", tags=["departure"])


def _convert_departure_to_schema(departure_model) -> Departure:
    """Convert departure model to schema with Money conversion."""
    return Departure(
        id=str(departure_model.id),
        tour_id=str(departure_model.tour_id),
        starts_at=departure_model.starts_at,
        capacity_total=departure_model.capacity_total,
        capacity_available=departure_model.capacity_available,
        price=Money(
            amount=departure_model.price_amount,
            currency=departure_model.price_currency
        )
    )


@router.post("/create", response_model=Departure)
async def create_departure(
    request: CreateDepartureRequest,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Create a new departure.
    
    This operation is idempotent based on tour_id + starts_at combination.
    """
    departure_service = DepartureService(db)
    
    try:
        # Create departure
        departure = await departure_service.create_departure(request)
        
        response_data = _convert_departure_to_schema(departure)
        
        logger.info(
            "Departure created successfully",
            extra={
                "departure_id": str(departure.id),
                "tour_id": request.tour_id,
                "starts_at": request.starts_at.isoformat(),
                "capacity_total": request.capacity_total
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
            "Unexpected error in departure creation",
            extra={
                "tour_id": request.tour_id,
                "starts_at": request.starts_at.isoformat(),
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/search", response_model=SearchDeparturesResponse)
async def search_departures(
    request: SearchDeparturesRequest,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Search departures based on criteria.
    
    Supports filtering by tour, date range, and availability.
    Uses cursor-based pagination.
    """
    departure_service = DepartureService(db)
    
    try:
        # Search departures
        result = await departure_service.search_departures(request)
        
        # Convert models to schemas
        departure_schemas = [
            _convert_departure_to_schema(departure)
            for departure in result.items
        ]
        
        response_data = SearchDeparturesResponse(
            items=departure_schemas,
            next_cursor=result.next_cursor
        )
        
        logger.info(
            "Departure search completed",
            extra={
                "total_found": len(departure_schemas),
                "has_next_page": result.next_cursor is not None,
                "filters": {
                    "tour_id": request.tour_id,
                    "date_from": request.date_from.isoformat() if request.date_from else None,
                    "date_to": request.date_to.isoformat() if request.date_to else None,
                    "available_only": request.available_only,
                    "limit": request.limit
                }
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
            "Unexpected error in departure search",
            extra={
                "filters": {
                    "tour_id": request.tour_id,
                    "date_from": request.date_from.isoformat() if request.date_from else None,
                    "date_to": request.date_to.isoformat() if request.date_to else None,
                    "available_only": request.available_only
                },
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )