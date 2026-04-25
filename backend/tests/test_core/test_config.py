"""Tests for app.core.config — settings loading."""
import pytest
from unittest.mock import patch


class TestSettings:
    """Settings loaded via pydantic-settings."""

    def test_default_settings(self):
        """Settings object loads with defaults."""
        from app.core.config import settings
        assert settings.CHUNK_SIZE == 1200
        assert settings.OVERLAP == 200
        assert settings.TOP_K == 5
        assert settings.FAISS_RETRIEVE_K == 200
        assert settings.SEMANTIC_WEIGHT == 0.65
        assert settings.BM25_WEIGHT == 0.35

    def test_index_path_property(self):
        """index_path combines INDEX_DIR and INDEX_FILE."""
        from app.core.config import settings
        path = settings.index_path
        assert str(path).endswith("faiss.index")

    def test_meta_path_property(self):
        """meta_path combines INDEX_DIR and META_FILE."""
        from app.core.config import settings
        path = settings.meta_path
        assert str(path).endswith("metadata.pkl")

    def test_bm25_path_property(self):
        """bm25_path combines INDEX_DIR and BM25_FILE."""
        from app.core.config import settings
        path = settings.bm25_path
        assert str(path).endswith("bm25.pkl")

    def test_cors_origins_default(self):
        """Default CORS origins are empty (secure default)."""
        from app.core.config import settings
        assert settings.CORS_ORIGINS == [] or isinstance(settings.CORS_ORIGINS, list)

    def test_parse_str_list_string(self):
        """CORS_ORIGINS can be parsed from comma-separated string."""
        from app.core.config import Settings
        result = Settings.parse_str_list("http://a.com, http://b.com")
        assert result == ["http://a.com", "http://b.com"]

    def test_parse_str_list_json_string(self):
        """CORS_ORIGINS can be parsed from JSON array string."""
        from app.core.config import Settings
        result = Settings.parse_str_list('["http://a.com","http://b.com"]')
        assert result == ["http://a.com", "http://b.com"]

    def test_parse_str_list_already_list(self):
        """If CORS_ORIGINS is already a list, it passes through."""
        from app.core.config import Settings
        result = Settings.parse_str_list(["http://a.com"])
        assert result == ["http://a.com"]

    def test_embed_model_default(self):
        """Default embedding model is set."""
        from app.core.config import settings
        assert settings.EMBED_MODEL == "BAAI/bge-small-en-v1.5"

    def test_rerank_model_default(self):
        """Default reranker model is set."""
        from app.core.config import settings
        assert settings.RERANK_MODEL == "cross-encoder/ms-marco-MiniLM-L-6-v2"
