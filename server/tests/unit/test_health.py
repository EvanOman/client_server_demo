"""Unit tests for health endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_check(test_client):
    """Test the health check endpoint."""
    response = await test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_ready_check(test_client):
    """Test the readiness check endpoint."""
    response = await test_client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data


@pytest.mark.asyncio
async def test_info_endpoint(test_client):
    """Test the service info endpoint."""
    response = await test_client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "features" in data


@pytest.mark.asyncio
async def test_health_ping_rpc(test_client):
    """Test the RPC-style health ping endpoint."""
    response = await test_client.post("/v1/health/ping", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data