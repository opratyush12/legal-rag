"""Tests for the /health endpoint and app startup."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
class TestHealthEndpoint:
    """GET /health — always available, reports index and model status."""

    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "index_loaded" in data
        assert "model" in data

    async def test_health_shows_index_loaded(self, client):
        resp = await client.get("/health")
        data = resp.json()
        assert data["index_loaded"] is True

    async def test_health_shows_index_not_loaded(self, client_no_index):
        resp = await client_no_index.get("/health")
        data = resp.json()
        assert data["status"] == "ok"  # health still returns 200
        assert data["index_loaded"] is False
