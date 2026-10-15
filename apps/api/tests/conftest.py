"""Test configuration and shared fixtures for Mound API tests."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provides an asynchronous test client for the FastAPI application.

    Yields:
        An AsyncClient configured with ASGI transport.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
