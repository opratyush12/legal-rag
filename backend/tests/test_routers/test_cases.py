"""Tests for /api/cases endpoints — preview and download."""
import pytest
from pathlib import Path
import tempfile
import os


@pytest.mark.asyncio
class TestCasePreview:
    """GET /api/cases/{pdf_index}/preview — text preview of a case."""

    async def test_preview_valid_case(self, client, mock_index_manager, mock_storage):
        """Returns text preview for a known case."""
        resp = await client.get("/api/cases/100.pdf/preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pdf_index"] == "100.pdf"
        assert len(data["text_preview"]) > 0
        assert "available" in data

    async def test_preview_unknown_case_returns_404(self, client, mock_index_manager):
        """Case not in index → 404."""
        mock_index_manager.chunks_for.return_value = []
        resp = await client.get("/api/cases/999.pdf/preview")
        assert resp.status_code == 404

    async def test_preview_index_not_loaded_returns_503(self, client_no_index):
        """Index not loaded → 503."""
        resp = await client_no_index.get("/api/cases/100.pdf/preview")
        assert resp.status_code == 503

    async def test_preview_truncates_to_4000_chars(self, client, mock_index_manager, mock_storage):
        """Preview text should be truncated to 4000 characters max."""
        long_chunk = "x" * 5000
        mock_index_manager.chunks_for.return_value = [long_chunk]
        resp = await client.get("/api/cases/100.pdf/preview")
        assert resp.status_code == 200
        assert len(resp.json()["text_preview"]) <= 4000

    async def test_preview_url_encoded_pdf_index(self, client, mock_index_manager, mock_storage):
        """URL-encoded pdf_index should be decoded properly."""
        mock_index_manager.chunks_for.return_value = ["some chunk"]
        resp = await client.get("/api/cases/100%2Epdf/preview")
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestCaseDownload:
    """GET /api/cases/{pdf_index}/download — PDF file download."""

    async def test_download_existing_pdf(self, client, mock_storage):
        """Returns PDF file when it exists."""
        # Create a temp file to simulate a real PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake pdf content")
            temp_path = f.name
        try:
            mock_storage.get_pdf_path.return_value = Path(temp_path)
            resp = await client.get("/api/cases/100.pdf/download")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/pdf"
        finally:
            os.unlink(temp_path)

    async def test_download_missing_pdf_returns_404(self, client, mock_storage):
        """PDF not on disk → 404."""
        mock_storage.get_pdf_path.return_value = None
        resp = await client.get("/api/cases/missing.pdf/download")
        assert resp.status_code == 404
