"""Inventory router for capacity adjustment operations."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.exceptions import ProblemDetailsException
from ..schemas.inventory import AdjustInventoryRequest, InventoryAdjustment
from ..services.inventory_service import InventoryService
from ..services.idempotency_service import IdempotencyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/inventory", tags=["inventory"])


def _convert_adjustment_to_schema(adjustment_model) -> InventoryAdjustment:
    """Convert inventory adjustment model to schema."""
    return InventoryAdjustment(
        id=str(adjustment_model.id),
        departure_id=str(adjustment_model.departure_id),
        delta=adjustment_model.delta,
        reason=adjustment_model.reason,
        created_at=adjustment_model.created_at,
        actor=adjustment_model.actor
    )


async def _handle_idempotent_adjustment(
    idempotency_key: str,
    request_body: Dict[str, Any],
    operation_func,
    db: AsyncSession
) -> JSONResponse:
    """Handle idempotent inventory adjustment operation."""
    idempotency_service = IdempotencyService(db)
    
    # Check for existing response
    cached_response = await idempotency_service.check_idempotency(
        idempotency_key=idempotency_key,
        method="inventory/adjust",
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
        response_dict = result if isinstance(result, dict) else result
        status_code = 200
        
        # Store response for future idempotent requests
        await idempotency_service.store_response(
            idempotency_key=idempotency_key,
            method="inventory/adjust",
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
            method="inventory/adjust",
            request_body=request_body,
            status_code=e.status_code,
            response_body=e.problem_details
        )
        raise


@router.post("/adjust", response_model=InventoryAdjustment)
async def adjust_inventory(
    request: AdjustInventoryRequest,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    # In a real implementation, you'd extract actor from authentication context
    actor: str = Header("system", alias="X-Actor")
) -> JSONResponse:
    """
    Adjust departure capacity.
    
    This operation is idempotent based on the Idempotency-Key header.
    Can increase or decrease capacity, but cannot reduce below active holds.
    """
    inventory_service = InventoryService(db)
    
    async def operation():
        adjustment = await inventory_service.adjust_inventory(request, actor)
        response_data = _convert_adjustment_to_schema(adjustment)
        
        logger.info(
            "Inventory adjustment completed successfully",
            extra={
                "adjustment_id": str(adjustment.id),
                "departure_id": request.departure_id,
                "delta": request.delta,
                "reason": request.reason,
                "actor": actor,
                "idempotency_key": idempotency_key
            }
        )
        
        return response_data.model_dump()
    
    try:
        return await _handle_idempotent_adjustment(
            idempotency_key=idempotency_key,
            request_body=request.model_dump(),
            operation_func=operation,
            db=db
        )
    
    except ProblemDetailsException:
        # Re-raise Problem Details exceptions as-is
        raise
    
    except Exception as e:
        logger.error(
            "Unexpected error in inventory adjustment",
            extra={
                "departure_id": request.departure_id,
                "delta": request.delta,
                "reason": request.reason,
                "actor": actor,
                "idempotency_key": idempotency_key,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )