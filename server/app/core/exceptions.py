"""Custom exceptions following RFC 9457 Problem Details for HTTP APIs."""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import uuid
from datetime import datetime


class ProblemDetailsException(HTTPException):
    """
    Base exception class following RFC 9457 Problem Details for HTTP APIs.
    
    https://tools.ietf.org/rfc/rfc9457.txt
    """
    
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: Optional[str] = None,
        type_uri: Optional[str] = None,
        instance: Optional[str] = None,
        extensions: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize Problem Details exception.
        
        Args:
            status_code: HTTP status code
            title: Short, human-readable summary of the problem type
            detail: Human-readable explanation specific to this occurrence
            type_uri: URI reference that identifies the problem type
            instance: URI reference that identifies the specific occurrence
            extensions: Additional problem-specific information
            headers: HTTP headers to include in response
        """
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_uri = type_uri or f"about:blank#{status_code}"
        self.instance = instance
        self.extensions = extensions or {}
        
        # Create the problem details object
        self.problem_details = {
            "type": self.type_uri,
            "title": self.title,
            "status": self.status_code,
        }
        
        if self.detail:
            self.problem_details["detail"] = self.detail
            
        if self.instance:
            self.problem_details["instance"] = self.instance
            
        # Add extensions
        self.problem_details.update(self.extensions)
        
        super().__init__(
            status_code=status_code,
            detail=self.problem_details,
            headers=headers
        )


class ValidationError(ProblemDetailsException):
    """Exception for request validation errors."""
    
    def __init__(
        self,
        detail: str = "The request data failed validation",
        errors: Optional[Dict[str, Any]] = None,
        instance: Optional[str] = None,
    ):
        extensions = {}
        if errors:
            extensions["errors"] = errors
            
        super().__init__(
            status_code=400,
            title="Validation Error",
            detail=detail,
            type_uri="https://example.com/problems/validation-error",
            instance=instance,
            extensions=extensions,
        )


class AuthenticationError(ProblemDetailsException):
    """Exception for authentication errors."""
    
    def __init__(
        self,
        detail: str = "Authentication credentials are required",
        instance: Optional[str] = None,
    ):
        super().__init__(
            status_code=401,
            title="Authentication Required",
            detail=detail,
            type_uri="https://example.com/problems/authentication-required",
            instance=instance,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(ProblemDetailsException):
    """Exception for authorization errors."""
    
    def __init__(
        self,
        detail: str = "Insufficient permissions to access this resource",
        required_permissions: Optional[list] = None,
        instance: Optional[str] = None,
    ):
        extensions = {}
        if required_permissions:
            extensions["required_permissions"] = required_permissions
            
        super().__init__(
            status_code=403,
            title="Access Forbidden",
            detail=detail,
            type_uri="https://example.com/problems/access-forbidden",
            instance=instance,
            extensions=extensions,
        )


class NotFoundError(ProblemDetailsException):
    """Exception for resource not found errors."""
    
    def __init__(
        self,
        resource_type: str = "resource",
        resource_id: Optional[str] = None,
        detail: Optional[str] = None,
        instance: Optional[str] = None,
    ):
        if not detail:
            detail = f"The requested {resource_type}"
            if resource_id:
                detail += f" with ID '{resource_id}'"
            detail += " could not be found"
            
        extensions = {
            "resource_type": resource_type,
        }
        if resource_id:
            extensions["resource_id"] = resource_id
            
        super().__init__(
            status_code=404,
            title="Resource Not Found",
            detail=detail,
            type_uri="https://example.com/problems/resource-not-found",
            instance=instance,
            extensions=extensions,
        )


class ConflictError(ProblemDetailsException):
    """Exception for resource conflict errors."""
    
    def __init__(
        self,
        detail: str = "The request conflicts with the current state of the resource",
        conflicting_resource: Optional[Dict[str, Any]] = None,
        instance: Optional[str] = None,
    ):
        extensions = {}
        if conflicting_resource:
            extensions["conflicting_resource"] = conflicting_resource
            
        super().__init__(
            status_code=409,
            title="Resource Conflict",
            detail=detail,
            type_uri="https://example.com/problems/resource-conflict",
            instance=instance,
            extensions=extensions,
        )


class RateLimitError(ProblemDetailsException):
    """Exception for rate limit errors."""
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        instance: Optional[str] = None,
    ):
        extensions = {}
        if limit:
            extensions["limit"] = limit
        if window:
            extensions["window_seconds"] = window
            
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            extensions["retry_after_seconds"] = retry_after
            
        super().__init__(
            status_code=429,
            title="Rate Limit Exceeded",
            detail=detail,
            type_uri="https://example.com/problems/rate-limit-exceeded",
            instance=instance,
            extensions=extensions,
            headers=headers,
        )


class InternalServerError(ProblemDetailsException):
    """Exception for internal server errors."""
    
    def __init__(
        self,
        detail: str = "An unexpected error occurred while processing the request",
        error_id: Optional[str] = None,
        instance: Optional[str] = None,
    ):
        if not error_id:
            error_id = str(uuid.uuid4())
            
        extensions = {
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        super().__init__(
            status_code=500,
            title="Internal Server Error",
            detail=detail,
            type_uri="https://example.com/problems/internal-server-error",
            instance=instance,
            extensions=extensions,
        )


# Business logic exceptions

class CapacityFullError(ProblemDetailsException):
    """Exception when capacity is full and no more items can be held."""
    
    def __init__(
        self,
        current_capacity: int,
        max_capacity: int,
        detail: Optional[str] = None,
        instance: Optional[str] = None,
    ):
        if not detail:
            detail = f"Capacity is full ({current_capacity}/{max_capacity}). Cannot hold additional items."
            
        super().__init__(
            status_code=409,
            title="Capacity Full",
            detail=detail,
            type_uri="https://example.com/problems/capacity-full",
            instance=instance,
            extensions={
                "current_capacity": current_capacity,
                "max_capacity": max_capacity,
            },
        )


class HoldExpiredError(ProblemDetailsException):
    """Exception when a hold has expired and items are no longer reserved."""
    
    def __init__(
        self,
        hold_id: str,
        expired_at: datetime,
        detail: Optional[str] = None,
        instance: Optional[str] = None,
    ):
        if not detail:
            detail = f"Hold {hold_id} expired at {expired_at.isoformat()}Z"
            
        super().__init__(
            status_code=410,
            title="Hold Expired",
            detail=detail,
            type_uri="https://example.com/problems/hold-expired",
            instance=instance,
            extensions={
                "hold_id": hold_id,
                "expired_at": expired_at.isoformat() + "Z",
            },
        )


class InsufficientQuantityError(ProblemDetailsException):
    """Exception when requested quantity exceeds available quantity."""
    
    def __init__(
        self,
        requested_quantity: int,
        available_quantity: int,
        item_id: Optional[str] = None,
        detail: Optional[str] = None,
        instance: Optional[str] = None,
    ):
        if not detail:
            detail = f"Requested quantity ({requested_quantity}) exceeds available quantity ({available_quantity})"
            if item_id:
                detail += f" for item {item_id}"
                
        extensions = {
            "requested_quantity": requested_quantity,
            "available_quantity": available_quantity,
        }
        if item_id:
            extensions["item_id"] = item_id
            
        super().__init__(
            status_code=409,
            title="Insufficient Quantity",
            detail=detail,
            type_uri="https://example.com/problems/insufficient-quantity",
            instance=instance,
            extensions=extensions,
        )


async def problem_details_handler(request: Request, exc: ProblemDetailsException) -> JSONResponse:
    """
    Exception handler for Problem Details exceptions.
    
    Args:
        request: FastAPI request object
        exc: Problem Details exception
        
    Returns:
        JSONResponse: Problem Details formatted response
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.problem_details,
        headers=exc.headers,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Generic exception handler that converts unhandled exceptions to Problem Details format.
    
    Args:
        request: FastAPI request object
        exc: Unhandled exception
        
    Returns:
        JSONResponse: Problem Details formatted response
    """
    error_id = str(uuid.uuid4())
    
    problem_details = {
        "type": "https://example.com/problems/internal-server-error",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred while processing the request",
        "instance": str(request.url),
        "error_id": error_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    return JSONResponse(
        status_code=500,
        content=problem_details,
    )