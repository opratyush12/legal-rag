"""Tests for app.core.index_manager — FAISS + BM25 index singleton."""
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path


class TestIndexManagerState:
    """IndexManager readiness and accessor tests."""

    def test_not_ready_by_default(self):
        """Fresh IndexManager should not be ready."""
        from app.core.index_manager import _IndexManager
        im = _IndexManager()
        assert im.is_ready() is False

    def test_is_ready_when_loaded(self):
        """IndexManager is ready when index + metadata are set."""
        from app.core.index_manager import _IndexManager
        im = _IndexManager()
        im._index = MagicMock()
        im._metadata = [{"pdf_index": "1.pdf", "chunk": "text"}]
        assert im.is_ready() is True

    def test_index_property_raises_when_not_loaded(self):
        """Accessing .index when not loaded → RuntimeError."""
        from app.core.index_manager import _IndexManager
        im = _IndexManager()
        with pytest.raises(RuntimeError, match="FAISS index not loaded"):
            _ = im.index

    def test_metadata_property_raises_when_not_loaded(self):
        """Accessing .metadata when not loaded → RuntimeError."""
        from app.core.index_manager import _IndexManager
        im = _IndexManager()
        with pytest.raises(RuntimeError, match="Metadata not loaded"):
            _ = im.metadata

    def test_has_bm25_false_by_default(self):
        """No BM25 loaded by default."""
        from app.core.index_manager import _IndexManager
        im = _IndexManager()
        assert im.has_bm25 is False

    def test_has_bm25_true_when_loaded(self):
        """has_bm25 returns True when BM25 is loaded."""
        from app.core.index_manager import _IndexManager
        im = _IndexManager()
        im._bm25 = MagicMock()
        assert im.has_bm25 is True


class TestChunksFor:
    """IndexManager.chunks_for() method."""

    def test_chunks_for_known_pdf(self):
        """Returns chunks matching the given pdf_index."""
        from app.core.index_manager import _IndexManager
        im = _IndexManager()
        im._index = MagicMock()
        im._metadata = [
            {"pdf_index": "100.pdf", "chunk": "chunk 1"},
            {"pdf_index": "100.pdf", "chunk": "chunk 2"},
            {"pdf_index": "200.pdf", "chunk": "other chunk"},
        ]
        result = im.chunks_for("100.pdf")
        assert len(result) == 2
        assert "chunk 1" in result
        assert "chunk 2" in result

    def test_chunks_for_unknown_pdf(self):
        """Returns empty list for unknown pdf_index."""
        from app.core.index_manager import _IndexManager
        im = _IndexManager()
        im._index = MagicMock()
        im._metadata = [{"pdf_index": "100.pdf", "chunk": "chunk"}]
        result = im.chunks_for("999.pdf")
        assert result == []


class TestBM25Search:
    """BM25 search method."""

    def test_bm25_search_returns_empty_when_no_bm25(self):
        """No BM25 loaded → empty list."""
        from app.core.index_manager import _IndexManager
        im = _IndexManager()
        result = im.bm25_search("property dispute", top_k=10)
        assert result == []

    def test_bm25_search_returns_results(self):
        """BM25 returns scored results when BM25 index is available."""
        import sys
        from app.core.index_manager import _IndexManager

        # Create a numpy stub with working argsort for this test
        import types
        real_np = types.ModuleType("numpy")

        def _argsort(arr):
            return sorted(range(len(arr)), key=lambda i: arr[i])

        real_np.argsort = _argsort
        old_np = sys.modules.get("numpy")
        sys.modules["numpy"] = real_np
        try:
            im = _IndexManager()
            mock_bm25 = MagicMock()
            scores = [0.5, 0.0, 0.8, 0.1]
            mock_bm25.get_scores.return_value = scores
            im._bm25 = mock_bm25
            im._bm25_chunks = ["a", "b", "c", "d"]

            result = im.bm25_search("test query", top_k=2)

            assert len(result) == 2
            assert result[0][0] == 2  # index 2 has score 0.8 (highest)
            assert result[0][1] > result[1][1]
        finally:
            if old_np is not None:
                sys.modules["numpy"] = old_np


class TestSimpleTokenize:
    """Internal tokenizer used for BM25."""

    def test_tokenize_basic(self):
        from app.core.index_manager import _simple_tokenize
        tokens = _simple_tokenize("Hello World Test")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens

    def test_tokenize_filters_short_words(self):
        """Words < 2 chars are filtered out."""
        from app.core.index_manager import _simple_tokenize
        tokens = _simple_tokenize("I am a test")
        assert "i" not in tokens
        assert "a" not in tokens
        assert "am" in tokens
        assert "test" in tokens

    def test_tokenize_strips_numbers_and_symbols(self):
        """Numbers and special chars are excluded."""
        from app.core.index_manager import _simple_tokenize
        tokens = _simple_tokenize("Article 21 protects rights! @#$")
        assert "article" in tokens
        assert "protects" in tokens
        assert "rights" in tokens
        assert "21" not in tokens
