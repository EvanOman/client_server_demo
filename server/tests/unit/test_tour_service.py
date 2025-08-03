"""Unit tests for tour service."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.services.tour_service import TourService
from app.models.tour import Tour


@pytest.mark.asyncio
async def test_create_tour(test_session, sample_tour_data):
    """Test creating a tour."""
    service = TourService(test_session)
    
    tour = await service.create_tour(
        name=sample_tour_data["name"],
        slug=sample_tour_data["slug"],
        description=sample_tour_data["description"]
    )
    
    assert tour.name == sample_tour_data["name"]
    assert tour.slug == sample_tour_data["slug"]
    assert tour.description == sample_tour_data["description"]
    assert tour.id is not None


@pytest.mark.asyncio
async def test_create_tour_duplicate_slug(test_session, sample_tour_data):
    """Test creating a tour with duplicate slug raises error."""
    service = TourService(test_session)
    
    # Create first tour
    await service.create_tour(
        name=sample_tour_data["name"],
        slug=sample_tour_data["slug"],
        description=sample_tour_data["description"]
    )
    
    # Try to create second tour with same slug
    with pytest.raises(IntegrityError):
        await service.create_tour(
            name="Different Tour",
            slug=sample_tour_data["slug"],  # Same slug
            description="Different description"
        )


@pytest.mark.asyncio
async def test_get_tour_by_id(test_session, sample_tour_data):
    """Test getting a tour by ID."""
    service = TourService(test_session)
    
    # Create tour
    created_tour = await service.create_tour(
        name=sample_tour_data["name"],
        slug=sample_tour_data["slug"],
        description=sample_tour_data["description"]
    )
    
    # Get tour by ID
    found_tour = await service.get_tour_by_id(created_tour.id)
    
    assert found_tour is not None
    assert found_tour.id == created_tour.id
    assert found_tour.name == sample_tour_data["name"]


@pytest.mark.asyncio
async def test_get_tour_by_id_not_found(test_session):
    """Test getting a non-existent tour returns None."""
    service = TourService(test_session)
    
    tour = await service.get_tour_by_id("non-existent-id")
    assert tour is None


@pytest.mark.asyncio
async def test_get_tour_by_slug(test_session, sample_tour_data):
    """Test getting a tour by slug."""
    service = TourService(test_session)
    
    # Create tour
    created_tour = await service.create_tour(
        name=sample_tour_data["name"],
        slug=sample_tour_data["slug"],
        description=sample_tour_data["description"]
    )
    
    # Get tour by slug
    found_tour = await service.get_tour_by_slug(sample_tour_data["slug"])
    
    assert found_tour is not None
    assert found_tour.id == created_tour.id
    assert found_tour.slug == sample_tour_data["slug"]