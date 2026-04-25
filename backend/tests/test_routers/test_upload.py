"""Tests for POST /api/upload/pdf endpoint."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import io


@pytest.mark.asyncio
class TestUploadEndpoint:
    """POST /api/upload/pdf — upload PDF, extract text, search."""

    async def test_upload_index_not_loaded_returns_503(self, client_no_index):
        """Returns 503 if index is not loaded."""
        fake_pdf = io.BytesIO(b"%PDF-1.4 some content here")
        resp = await client_no_index.post(
            "/api/upload/pdf",
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
        )
        assert resp.status_code == 503

    async def test_upload_non_pdf_returns_400(self, client, mock_index_manager):
        """Non-PDF file → 400."""
        fake_txt = io.BytesIO(b"This is not a PDF")
        resp = await client.post(
            "/api/upload/pdf",
            files={"file": ("test.txt", fake_txt, "text/plain")},
        )
        assert resp.status_code == 400

    async def test_upload_oversized_pdf_returns_413(self, client, mock_index_manager):
        """PDF > 20 MB → 413."""
        # Create content just over 20MB
        big_content = b"x" * (21 * 1024 * 1024)
        resp = await client.post(
            "/api/upload/pdf",
            files={"file": ("big.pdf", io.BytesIO(big_content), "application/pdf")},
        )
        assert resp.status_code == 413

    async def test_upload_valid_pdf(self, client, mock_index_manager):
        """Valid PDF → extracted text is used as search query."""
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake legal document about property law")
        with patch("app.routers.upload.extract_text",
                    return_value="A long legal text about property disputes and land ownership rights in India under the Transfer of Property Act."), \
             patch("app.routers.upload.run_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "query": "property disputes and land ownership",
                "expanded_queries": ["property disputes"],
                "results": [],
                "total_candidates_evaluated": 0,
            }
            resp = await client.post(
                "/api/upload/pdf",
                files={"file": ("test.pdf", fake_pdf, "application/pdf")},
            )
        assert resp.status_code == 200

    async def test_upload_unextractable_pdf_returns_422(self, client, mock_index_manager):
        """PDF with no extractable text → 422."""
        from fastapi import HTTPException
        fake_pdf = io.BytesIO(b"%PDF-1.4 image only scan")
        with patch("app.routers.upload.extract_text",
                    side_effect=HTTPException(status_code=422, detail="Could not extract text")):
            resp = await client.post(
                "/api/upload/pdf",
                files={"file": ("scan.pdf", fake_pdf, "application/pdf")},
            )
        assert resp.status_code == 422

    async def test_upload_missing_file(self, client):
        """No file attached → 422."""
        resp = await client.post("/api/upload/pdf")
        assert resp.status_code == 422
