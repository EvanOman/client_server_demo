"""Tour-related Pydantic schemas."""


from pydantic import BaseModel, Field


class CreateTourRequest(BaseModel):
    """Request schema for creating a tour."""

    name: str = Field(..., min_length=1, max_length=255, description="Tour name")
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$", description="URL-friendly slug")
    description: str = Field(..., min_length=1, max_length=2000, description="Tour description")


class Tour(BaseModel):
    """Tour response schema."""

    id: str = Field(..., description="Unique tour ID")
    name: str = Field(..., description="Tour name")
    slug: str = Field(..., description="URL-friendly slug")
    description: str = Field(..., description="Tour description")

    class Config:
        from_attributes = True
