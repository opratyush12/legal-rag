"""Tests for POST /api/chat endpoint."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
class TestChatEndpoint:
    """POST /api/chat — Groq-powered chat grounded in a specific case."""

    async def test_chat_valid_request(self, client, mock_index_manager, mock_groq):
        """Valid chat request returns a reply."""
        with patch("app.routers.chat.chat_with_case", return_value="The court held..."):
            resp = await client.post("/api/chat", json={
                "pdf_index": "100.pdf",
                "messages": [{"role": "user", "content": "What was the verdict?"}],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert data["pdf_index"] == "100.pdf"

    async def test_chat_returns_503_when_index_not_loaded(self, client_no_index):
        """Returns 503 if index is not loaded."""
        resp = await client_no_index.post("/api/chat", json={
            "pdf_index": "100.pdf",
            "messages": [{"role": "user", "content": "What was the verdict?"}],
        })
        assert resp.status_code == 503

    async def test_chat_unknown_case_returns_404(self, client, mock_index_manager):
        """Case not in index → 404."""
        mock_index_manager.chunks_for.return_value = []
        resp = await client.post("/api/chat", json={
            "pdf_index": "999.pdf",
            "messages": [{"role": "user", "content": "What happened?"}],
        })
        assert resp.status_code == 404

    async def test_chat_missing_pdf_index(self, client):
        """Missing pdf_index → 422."""
        resp = await client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hello"}],
        })
        assert resp.status_code == 422

    async def test_chat_missing_messages(self, client):
        """Missing messages → 422."""
        resp = await client.post("/api/chat", json={
            "pdf_index": "100.pdf",
        })
        assert resp.status_code == 422

    async def test_chat_empty_body(self, client):
        """Empty body → 422."""
        resp = await client.post("/api/chat", json={})
        assert resp.status_code == 422

    async def test_chat_groq_failure_returns_503(self, client, mock_index_manager):
        """Groq API failure → 503."""
        with patch("app.routers.chat.chat_with_case", side_effect=RuntimeError("All models failed")):
            resp = await client.post("/api/chat", json={
                "pdf_index": "100.pdf",
                "messages": [{"role": "user", "content": "Explain the case"}],
            })
        assert resp.status_code == 503

    async def test_chat_multiple_messages(self, client, mock_index_manager, mock_groq):
        """Multi-turn conversation should work."""
        with patch("app.routers.chat.chat_with_case", return_value="Follow-up answer."):
            resp = await client.post("/api/chat", json={
                "pdf_index": "100.pdf",
                "messages": [
                    {"role": "user", "content": "What is this case about?"},
                    {"role": "assistant", "content": "It's about property dispute."},
                    {"role": "user", "content": "Who won?"},
                ],
            })
        assert resp.status_code == 200
        assert resp.json()["reply"] == "Follow-up answer."
