"""Simple API health tests without database."""

import pytest
from httpx import AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_api_health_endpoints():
    """Test the health endpoints without database dependency."""
    app = create_app()

    # Use transport for testing FastAPI apps
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test basic health endpoint
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

        # Test ready endpoint
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

        # Test info endpoint
        response = await client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test the metrics endpoint."""
    app = create_app()

    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")


@pytest.mark.asyncio
async def test_openapi_docs():
    """Test that OpenAPI docs are available in development."""
    app = create_app()

    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")
        # Should be available in development mode
        assert response.status_code == 200
