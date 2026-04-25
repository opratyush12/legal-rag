"""Tests for app.services.search_service — retrieval pipeline."""
import pytest
from unittest.mock import patch, MagicMock
from app.models.schemas import SearchRequest


class TestConfidenceLabel:
    """Confidence labelling based on reranker scores."""

    def test_high_confidence(self):
        from app.services.search_service import _confidence
        assert _confidence(5.0) == "High"
        assert _confidence(4.0) == "High"

    def test_medium_confidence(self):
        from app.services.search_service import _confidence
        assert _confidence(2.0) == "Medium"
        assert _confidence(0.0) == "Medium"

    def test_low_confidence(self):
        from app.services.search_service import _confidence
        assert _confidence(-1.0) == "Low"
        assert _confidence(-10.0) == "Low"


@pytest.mark.asyncio
class TestRunSearch:
    """End-to-end search pipeline (all external deps mocked)."""

    async def test_search_pipeline_returns_results(
        self, mock_index_manager, mock_groq, mock_models, mock_storage
    ):
        """Full pipeline with mocked deps returns valid SearchResponse."""
        from app.services.search_service import run_search

        with patch("app.services.search_service.IndexManager", mock_index_manager), \
             patch("app.services.search_service.get_embed_model", mock_models["embed"]), \
             patch("app.services.search_service.get_reranker", mock_models["reranker"]), \
             patch("app.services.search_service.expand_query", mock_groq["expand_query"]), \
             patch("app.services.search_service.generate_relevance_summary",
                   mock_groq["generate_relevance_summary"]), \
             patch("app.services.search_service.storage", mock_storage):
            request = SearchRequest(query="property dispute in India for land", top_k=2)
            result = await run_search(request)

        assert result.query == "property dispute in India for land"
        assert isinstance(result.results, list)
        assert isinstance(result.expanded_queries, list)
        assert isinstance(result.total_candidates_evaluated, int)

    async def test_search_pipeline_empty_results(self, mock_index_manager, mock_models, mock_storage):
        """When FAISS returns no valid indices, result is empty."""
        from app.services.search_service import run_search

        # Make FAISS return all -1 (no match)
        mock_index_manager.index.search.return_value = ([[-1, -1]], [[-1, -1]])
        mock_index_manager.bm25_search.return_value = []

        with patch("app.services.search_service.IndexManager", mock_index_manager), \
             patch("app.services.search_service.get_embed_model", mock_models["embed"]), \
             patch("app.services.search_service.get_reranker", mock_models["reranker"]), \
             patch("app.services.search_service.expand_query", return_value=["rare query"]), \
             patch("app.services.search_service.generate_relevance_summary",
                   return_value="No match."), \
             patch("app.services.search_service.storage", mock_storage), \
             patch("app.services.search_service.settings") as mock_settings:
            mock_settings.USE_QUERY_EXPANSION = False
            mock_settings.GROQ_API_KEY = ""
            mock_settings.USE_BM25 = False
            mock_settings.FAISS_RETRIEVE_K = 10
            mock_settings.SEMANTIC_WEIGHT = 0.65
            mock_settings.BM25_WEIGHT = 0.35
            mock_settings.CHUNK_COUNT_BOOST = 0.15
            mock_settings.CANDIDATE_PDFS = 20
            mock_settings.RERANK_CHUNKS = 4

            request = SearchRequest(query="extremely rare hypothetical query", top_k=5)
            result = await run_search(request)

        assert result.results == []
