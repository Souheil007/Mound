"""Tests for application health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_ok(client: AsyncClient) -> None:
    """Verifies that the /health endpoint responds with status 200 and version.

    Args:
        client: The test HTTP client fixture.
    """
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
