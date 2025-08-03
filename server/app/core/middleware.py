"""Custom middleware for request tracking, tracing, and logging."""

import time
import uuid
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import re

from .config import settings


logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.
    
    The request ID is either extracted from the X-Request-ID header
    or generated if not present. It's added to the response headers
    and can be used for request correlation across services.
    """
    
    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID."""
        # Get or generate request ID
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store request ID in request state for access in handlers
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers[self.header_name] = request_id
        
        return response


class TraceContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles W3C Trace Context headers.
    
    Extracts and propagates trace context following the W3C Trace Context
    specification for distributed tracing.
    
    https://www.w3.org/TR/trace-context/
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.traceparent_pattern = re.compile(
            r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$"
        )
    
    def _parse_traceparent(self, traceparent: str) -> Optional[dict]:
        """Parse W3C traceparent header."""
        match = self.traceparent_pattern.match(traceparent)
        if not match:
            return None
        
        version, trace_id, parent_id, flags = match.groups()
        
        # Validate version (currently only 00 is supported)
        if version != "00":
            return None
        
        # Validate trace_id (must not be all zeros)
        if trace_id == "0" * 32:
            return None
        
        # Validate parent_id (must not be all zeros)
        if parent_id == "0" * 16:
            return None
        
        return {
            "version": version,
            "trace_id": trace_id,
            "parent_id": parent_id,
            "flags": flags,
        }
    
    def _generate_span_id(self) -> str:
        """Generate a new 16-character hex span ID."""
        return uuid.uuid4().hex[:16]
    
    def _generate_traceparent(self, trace_id: str, span_id: str, flags: str = "01") -> str:
        """Generate W3C traceparent header."""
        return f"00-{trace_id}-{span_id}-{flags}"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle trace context."""
        # Extract incoming trace context
        traceparent = request.headers.get("traceparent")
        tracestate = request.headers.get("tracestate")
        
        trace_context = None
        if traceparent:
            trace_context = self._parse_traceparent(traceparent)
        
        # Generate new span for this request
        if trace_context:
            # Continue existing trace
            trace_id = trace_context["trace_id"]
            parent_span_id = trace_context["parent_id"]
            flags = trace_context["flags"]
        else:
            # Start new trace
            trace_id = uuid.uuid4().hex
            parent_span_id = None
            flags = "01"  # sampled
        
        # Generate new span ID for this request
        span_id = self._generate_span_id()
        
        # Store trace context in request state
        request.state.trace_context = {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "flags": flags,
            "tracestate": tracestate,
        }
        
        # Process request
        response = await call_next(request)
        
        # Add trace context to response headers
        response.headers["traceparent"] = self._generate_traceparent(trace_id, span_id, flags)
        if tracestate:
            response.headers["tracestate"] = tracestate
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs HTTP requests and responses.
    
    Logs request and response information including timing,
    status codes, and correlation IDs for debugging and monitoring.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        log_response_body: bool = False,
        skip_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.skip_paths = skip_paths or ["/health", "/metrics", "/favicon.ico"]
    
    def _should_log(self, path: str) -> bool:
        """Check if request should be logged."""
        return path not in self.skip_paths
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log information."""
        if not self._should_log(request.url.path):
            return await call_next(request)
        
        start_time = time.time()
        
        # Extract request information
        request_id = getattr(request.state, "request_id", "unknown")
        trace_context = getattr(request.state, "trace_context", {})
        trace_id = trace_context.get("trace_id", "unknown")
        span_id = trace_context.get("span_id", "unknown")
        
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Log request
        log_data = {
            "event": "request_started",
            "request_id": request_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "content_type": request.headers.get("Content-Type"),
            "content_length": request.headers.get("Content-Length"),
        }
        
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Note: This consumes the request body, so it may need special handling
                # in production for performance reasons
                body = await request.body()
                if body:
                    log_data["request_body"] = body.decode("utf-8", errors="replace")[:1000]  # Truncate
            except Exception as e:
                log_data["request_body_error"] = str(e)
        
        logger.info("HTTP request started", extra=log_data)
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as e:
            status_code = 500
            error = str(e)
            # Re-raise the exception
            response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "request_id": request_id}
            )
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log response
        log_data.update({
            "event": "request_completed",
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2),
            "response_size": response.headers.get("Content-Length"),
        })
        
        if error:
            log_data["error"] = error
        
        # Log at appropriate level based on status code
        if status_code >= 500:
            logger.error("HTTP request completed with server error", extra=log_data)
        elif status_code >= 400:
            logger.warning("HTTP request completed with client error", extra=log_data)
        else:
            logger.info("HTTP request completed successfully", extra=log_data)
        
        return response


# Middleware configuration helper
def setup_middleware(app, enable_logging: bool = True) -> None:
    """
    Setup all middleware on the FastAPI app.
    
    Args:
        app: FastAPI application instance
        enable_logging: Whether to enable request logging middleware
    """
    # Add middleware in reverse order (last added is first executed)
    
    if enable_logging and not settings.is_production:
        # Only log request/response bodies in development
        app.add_middleware(
            LoggingMiddleware,
            log_request_body=settings.debug,
            log_response_body=settings.debug,
        )
    elif enable_logging:
        # Production logging without bodies
        app.add_middleware(LoggingMiddleware)
    
    # Trace context middleware
    app.add_middleware(TraceContextMiddleware)
    
    # Request ID middleware (should be first/last)
    app.add_middleware(RequestIDMiddleware)