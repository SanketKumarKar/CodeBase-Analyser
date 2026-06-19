"""
tests/test_health.py — Unit / integration tests for the /health endpoint.

Run with: pytest backend/tests/test_health.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """The /health endpoint must always return HTTP 200 (even if services are down)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape():
    """Response must contain 'status' and 'services' keys with correct service names."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    data = response.json()
    assert "status" in data
    assert "services" in data
    assert data["status"] in ("ok", "error")

    expected_services = {"qdrant", "neo4j", "redis", "postgres", "ollama"}
    assert set(data["services"].keys()) == expected_services

    for name, check in data["services"].items():
        assert "status" in check, f"Service {name} missing 'status'"
        assert check["status"] in ("ok", "error"), f"Service {name} has invalid status"
        assert "latency_ms" in check, f"Service {name} missing 'latency_ms'"
