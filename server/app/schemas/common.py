"""Common Pydantic schemas."""


from pydantic import BaseModel, Field


class Money(BaseModel):
    """Money representation with amount in minor units."""

    amount: int = Field(..., ge=0, description="Amount in minor units (e.g., cents)")
    currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$", description="ISO 4217 currency code")


class Violation(BaseModel):
    """Validation error violation."""

    path: str = Field(..., description="JSON path to the invalid field")
    message: str = Field(..., description="Validation error message")


class Problem(BaseModel):
    """RFC 9457 Problem Details response."""

    type: str | None = Field(None, description="Problem type URI")
    title: str = Field(..., description="Short human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: str | None = Field(None, description="Human-readable explanation")
    instance: str | None = Field(None, description="URI reference for this occurrence")
    code: str | None = Field(None, description="Application-specific error code")
    retryable: bool | None = Field(None, description="Whether the operation can be retried")
    trace_id: str | None = Field(None, description="Trace ID for debugging")
    violations: list[Violation] | None = Field(None, description="Validation errors")


class PaginatedResponse(BaseModel):
    """Base class for paginated responses."""

    next_cursor: str | None = Field(None, description="Cursor for next page")
