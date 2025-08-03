"""Waitlist router for waitlist operations."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.exceptions import ProblemDetailsException
from ..schemas.waitlist import JoinWaitlistRequest, NotifyWaitlistRequest, WaitlistEntry, NotifyWaitlistResponse
from ..schemas.booking import Hold
from ..services.waitlist_service import WaitlistService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/waitlist", tags=["waitlist"])


def _convert_waitlist_entry_to_schema(entry_model) -> WaitlistEntry:
    """Convert waitlist entry model to schema."""
    return WaitlistEntry(
        id=str(entry_model.id),
        departure_id=str(entry_model.departure_id),
        customer_ref=entry_model.customer_ref,
        created_at=entry_model.created_at,
        notified_at=entry_model.notified_at
    )


def _convert_hold_to_schema(hold_model) -> Hold:
    """Convert hold model to schema."""
    return Hold(
        id=str(hold_model.id),
        departure_id=str(hold_model.departure_id),
        seats=hold_model.seats,
        customer_ref=hold_model.customer_ref,
        status=hold_model.status,
        expires_at=hold_model.expires_at
    )


@router.post("/join", response_model=WaitlistEntry) 
async def join_waitlist(
    request: JoinWaitlistRequest,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Join departure waitlist.
    
    This operation is idempotent based on customer_ref + departure_id combination.
    """
    waitlist_service = WaitlistService(db)
    
    try:
        entry = await waitlist_service.join_waitlist(request)
        response_data = _convert_waitlist_entry_to_schema(entry)
        
        logger.info(
            "Customer joined waitlist successfully",
            extra={
                "waitlist_entry_id": str(entry.id),
                "departure_id": request.departure_id,
                "customer_ref": request.customer_ref
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
            "Unexpected error in waitlist join",
            extra={
                "departure_id": request.departure_id,
                "customer_ref": request.customer_ref,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/notify", response_model=NotifyWaitlistResponse)
async def notify_waitlist(
    request: NotifyWaitlistRequest,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Process waitlist notifications (internal operation).
    
    Creates short-TTL holds for waitlisted customers when capacity becomes available.
    This endpoint is typically called by background workers or internal services.
    """
    waitlist_service = WaitlistService(db)
    
    try:
        result = await waitlist_service.notify_waitlist(request)
        
        # Convert holds to schemas
        holds_schema = [
            _convert_hold_to_schema(hold)
            for hold in result.holds_created
        ]
        
        response_data = NotifyWaitlistResponse(
            processed_count=result.processed_count,
            holds_created=holds_schema
        )
        
        logger.info(
            "Waitlist notification processing completed",
            extra={
                "departure_id": request.departure_id,
                "processed_count": result.processed_count,
                "holds_created": len(holds_schema)
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
            "Unexpected error in waitlist notification",
            extra={
                "departure_id": request.departure_id,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )