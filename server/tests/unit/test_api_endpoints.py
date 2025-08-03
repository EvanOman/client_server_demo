"""Integration tests for API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_create_tour_endpoint(test_client, sample_tour_data):
    """Test the tour creation endpoint."""
    response = await test_client.post(
        "/v1/tour/create",
        json=sample_tour_data,
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_tour_data["name"]
    assert data["slug"] == sample_tour_data["slug"]
    assert data["description"] == sample_tour_data["description"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_tour_missing_auth(test_client, sample_tour_data):
    """Test tour creation without authentication."""
    response = await test_client.post("/v1/tour/create", json=sample_tour_data)

    assert response.status_code == 401
    data = response.json()
    assert data["status"] == 401
    assert "authorization" in data["title"].lower()


@pytest.mark.asyncio
async def test_create_tour_invalid_data(test_client):
    """Test tour creation with invalid data."""
    invalid_data = {
        "name": "",  # Empty name should fail validation
        "slug": "test-slug",
        "description": "Test description"
    }

    response = await test_client.post(
        "/v1/tour/create",
        json=invalid_data,
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 422
    data = response.json()
    assert data["status"] == 422
    assert "violations" in data


@pytest.mark.asyncio
async def test_departure_search_endpoint(test_client):
    """Test the departure search endpoint."""
    search_data = {
        "available_only": True,
        "limit": 10
    }

    response = await test_client.post(
        "/v1/departure/search",
        json=search_data,
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_metrics_endpoint(test_client):
    """Test the Prometheus metrics endpoint."""
    response = await test_client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    # Check for some expected metrics
    content = response.text
    assert "http_requests_total" in content or "# HELP" in content
