"""Booking router for booking operations."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.exceptions import ProblemDetailsException
from ..schemas.booking import (
    Booking,
    CancelBookingRequest,
    ConfirmBookingRequest,
    CreateHoldRequest,
    GetBookingRequest,
    Hold,
)
from ..services.booking_service import BookingService
from ..services.idempotency_service import IdempotencyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/booking", tags=["booking"])

# Define dependencies to avoid B008 linting errors
DB_DEPENDENCY = Depends(get_db)
IDEMPOTENCY_KEY_DEPENDENCY = Header(..., alias="Idempotency-Key")


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


def _convert_booking_to_schema(booking_model) -> Booking:
    """Convert booking model to schema."""
    return Booking(
        id=str(booking_model.id),
        hold_id=str(booking_model.hold_id),
        code=booking_model.code,
        seats=booking_model.seats,
        customer_ref=booking_model.customer_ref,
        status=booking_model.status,
        created_at=booking_model.created_at
    )


async def _handle_idempotent_operation(
    method: str,
    idempotency_key: str,
    request_body: dict[str, Any],
    operation_func,
    db: AsyncSession
) -> JSONResponse:
    """Handle idempotent operation with caching."""
    idempotency_service = IdempotencyService(db)

    # Check for existing response
    cached_response = await idempotency_service.check_idempotency(
        idempotency_key=idempotency_key,
        method=method,
        request_body=request_body
    )

    if cached_response:
        status_code, response_body, response_headers = cached_response
        return JSONResponse(
            status_code=status_code,
            content=response_body,
            headers=response_headers or {}
        )

    # Execute operation
    try:
        result = await operation_func()

        if isinstance(result, JSONResponse):
            response_data = result.body.decode('utf-8')
            response_dict = eval(response_data)  # In production, use json.loads
            status_code = result.status_code
        else:
            response_dict = result
            status_code = 200

        # Store response for future idempotent requests
        await idempotency_service.store_response(
            idempotency_key=idempotency_key,
            method=method,
            request_body=request_body,
            status_code=status_code,
            response_body=response_dict
        )

        return JSONResponse(
            status_code=status_code,
            content=response_dict
        )

    except ProblemDetailsException as e:
        # Store error response for idempotency
        await idempotency_service.store_response(
            idempotency_key=idempotency_key,
            method=method,
            request_body=request_body,
            status_code=e.status_code,
            response_body=e.problem_details
        )
        raise


@router.post("/hold", response_model=Hold)
async def create_hold(
    request: CreateHoldRequest,
    db: AsyncSession = DB_DEPENDENCY,
    idempotency_key: str = IDEMPOTENCY_KEY_DEPENDENCY
) -> JSONResponse:
    """
    Create or refresh a seat hold.

    This operation is idempotent based on the Idempotency-Key header.
    """
    booking_service = BookingService(db)

    async def operation():
        hold = await booking_service.create_hold(request, idempotency_key)
        response_data = _convert_hold_to_schema(hold)

        logger.info(
            "Hold created successfully",
            extra={
                "hold_id": str(hold.id),
                "departure_id": request.departure_id,
                "seats": request.seats,
                "customer_ref": request.customer_ref,
                "idempotency_key": idempotency_key
            }
        )

        return response_data.model_dump()

    try:
        return await _handle_idempotent_operation(
            method="booking/hold",
            idempotency_key=idempotency_key,
            request_body=request.model_dump(),
            operation_func=operation,
            db=db
        )

    except ProblemDetailsException:
        raise

    except Exception as e:
        logger.error(
            "Unexpected error in hold creation",
            extra={
                "departure_id": request.departure_id,
                "seats": request.seats,
                "customer_ref": request.customer_ref,
                "idempotency_key": idempotency_key,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/confirm", response_model=Booking)
async def confirm_booking(
    request: ConfirmBookingRequest,
    db: AsyncSession = DB_DEPENDENCY,
    idempotency_key: str = IDEMPOTENCY_KEY_DEPENDENCY
) -> JSONResponse:
    """
    Confirm a booking from a hold.

    This operation is idempotent based on the Idempotency-Key header.
    """
    booking_service = BookingService(db)

    async def operation():
        booking = await booking_service.confirm_booking(request, idempotency_key)
        response_data = _convert_booking_to_schema(booking)

        logger.info(
            "Booking confirmed successfully",
            extra={
                "booking_id": str(booking.id),
                "booking_code": booking.code,
                "hold_id": request.hold_id,
                "idempotency_key": idempotency_key
            }
        )

        return response_data.model_dump()

    try:
        return await _handle_idempotent_operation(
            method="booking/confirm",
            idempotency_key=idempotency_key,
            request_body=request.model_dump(),
            operation_func=operation,
            db=db
        )

    except ProblemDetailsException:
        raise

    except Exception as e:
        logger.error(
            "Unexpected error in booking confirmation",
            extra={
                "hold_id": request.hold_id,
                "idempotency_key": idempotency_key,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/cancel", response_model=Booking)
async def cancel_booking(
    request: CancelBookingRequest,
    db: AsyncSession = DB_DEPENDENCY,
    idempotency_key: str = IDEMPOTENCY_KEY_DEPENDENCY
) -> JSONResponse:
    """
    Cancel a booking.

    This operation is idempotent based on the Idempotency-Key header.
    """
    booking_service = BookingService(db)

    async def operation():
        booking = await booking_service.cancel_booking(request, idempotency_key)
        response_data = _convert_booking_to_schema(booking)

        logger.info(
            "Booking cancelled successfully",
            extra={
                "booking_id": request.booking_id,
                "booking_code": booking.code,
                "idempotency_key": idempotency_key
            }
        )

        return response_data.model_dump()

    try:
        return await _handle_idempotent_operation(
            method="booking/cancel",
            idempotency_key=idempotency_key,
            request_body=request.model_dump(),
            operation_func=operation,
            db=db
        )

    except ProblemDetailsException:
        raise

    except Exception as e:
        logger.error(
            "Unexpected error in booking cancellation",
            extra={
                "booking_id": request.booking_id,
                "idempotency_key": idempotency_key,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/get", response_model=Booking)
async def get_booking(
    request: GetBookingRequest,
    db: AsyncSession = DB_DEPENDENCY
) -> JSONResponse:
    """
    Get booking details.

    This is a read operation and does not require idempotency.
    """
    booking_service = BookingService(db)

    try:
        booking = await booking_service.get_booking(request)
        response_data = _convert_booking_to_schema(booking)

        logger.info(
            "Booking retrieved successfully",
            extra={
                "booking_id": request.booking_id,
                "booking_code": booking.code
            }
        )

        return JSONResponse(
            status_code=200,
            content=response_data.model_dump()
        )

    except ProblemDetailsException:
        raise

    except Exception as e:
        logger.error(
            "Unexpected error in booking retrieval",
            extra={
                "booking_id": request.booking_id,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e
