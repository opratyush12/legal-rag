"""Tests for POST /api/search endpoint."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
class TestSearchEndpoint:
    """POST /api/search — semantic + BM25 + rerank search."""

    async def test_search_valid_query(self, client, mock_groq, mock_models, mock_index_manager):
        """Valid query returns 200 with search results."""
        with patch("app.routers.search.run_search", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "query": "property dispute in India regarding land",
                "expanded_queries": ["property dispute in India regarding land"],
                "results": [
                    {
                        "pdf_index": "100.pdf",
                        "relevance_score": 5.0,
                        "confidence": "High",
                        "summary": "Relevant case.",
                        "snippet": "Property dispute text.",
                        "available": True,
                        "chunk_hits": 2,
                    }
                ],
                "total_candidates_evaluated": 20,
            }
            resp = await client.post("/api/search", json={
                "query": "property dispute in India regarding land",
                "top_k": 5,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "property dispute in India regarding land"
        assert len(data["results"]) == 1
        assert data["results"][0]["pdf_index"] == "100.pdf"
        assert "total_candidates_evaluated" in data

    async def test_search_returns_503_when_index_not_loaded(self, client_no_index):
        """Returns 503 if FAISS index is not loaded."""
        resp = await client_no_index.post("/api/search", json={
            "query": "property dispute in India regarding land",
            "top_k": 5,
        })
        assert resp.status_code == 503

    @pytest.mark.parametrize("query", [
        "",
        "short",
        "123456789",  # exactly 9 chars
    ])
    async def test_search_rejects_short_query(self, client, query):
        """Query < 10 chars → 422 validation error."""
        resp = await client.post("/api/search", json={"query": query, "top_k": 5})
        assert resp.status_code == 422

    async def test_search_accepts_minimum_query_length(self, client, mock_index_manager):
        """Query of exactly 10 chars should pass validation."""
        with patch("app.routers.search.run_search", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "query": "1234567890",
                "expanded_queries": ["1234567890"],
                "results": [],
                "total_candidates_evaluated": 0,
            }
            resp = await client.post("/api/search", json={
                "query": "1234567890",
                "top_k": 5,
            })
        assert resp.status_code == 200

    @pytest.mark.parametrize("top_k", [0, -1, 21, 100])
    async def test_search_rejects_invalid_top_k(self, client, top_k):
        """top_k out of range [1, 20] → 422."""
        resp = await client.post("/api/search", json={
            "query": "property dispute in India regarding land",
            "top_k": top_k,
        })
        assert resp.status_code == 422

    async def test_search_uses_default_top_k(self, client, mock_index_manager):
        """If top_k is omitted, defaults to 5."""
        with patch("app.routers.search.run_search", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "query": "property dispute in India regarding land",
                "expanded_queries": [],
                "results": [],
                "total_candidates_evaluated": 0,
            }
            resp = await client.post("/api/search", json={
                "query": "property dispute in India regarding land",
            })
        assert resp.status_code == 200

    async def test_search_missing_query_field(self, client):
        """Missing required field → 422."""
        resp = await client.post("/api/search", json={"top_k": 5})
        assert resp.status_code == 422

    async def test_search_empty_body(self, client):
        """Empty body → 422."""
        resp = await client.post("/api/search", json={})
        assert resp.status_code == 422

    async def test_search_returns_empty_results(self, client, mock_index_manager):
        """Valid query but no matches returns empty list."""
        with patch("app.routers.search.run_search", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "query": "extremely rare hypothetical legal scenario",
                "expanded_queries": ["extremely rare hypothetical legal scenario"],
                "results": [],
                "total_candidates_evaluated": 0,
            }
            resp = await client.post("/api/search", json={
                "query": "extremely rare hypothetical legal scenario",
                "top_k": 5,
            })
        assert resp.status_code == 200
        assert resp.json()["results"] == []
