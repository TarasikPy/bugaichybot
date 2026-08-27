"""Unit tests for the aiohttp health check server."""

import pytest
from aiohttp.test_utils import TestClient, TestServer

from src.infrastructure.web.health import create_health_app


@pytest.mark.asyncio
async def test_health_endpoints() -> None:
    """Test health check GET and HEAD endpoints."""
    app = create_health_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    try:
        resp_get = await client.get("/")
        assert resp_get.status == 200
        text = await resp_get.text()
        assert text == "OK"

        resp_head = await client.head("/")
        assert resp_head.status == 200

        resp_health = await client.get("/health")
        assert resp_health.status == 200
    finally:
        await client.close()
