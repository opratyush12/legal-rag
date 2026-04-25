"""Tests for POST /api/assistant endpoint."""
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
class TestAssistantEndpoint:
    """POST /api/assistant — general legal assistant chat (no case context)."""

    async def test_assistant_valid_request(self, client, mock_groq):
        """Valid request returns a legal assistant reply."""
        with patch("app.routers.assistant.general_legal_chat",
                    mock_groq["general_legal_chat"]):
            resp = await client.post("/api/assistant", json={
                "messages": [{"role": "user", "content": "What is Article 21?"}],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert len(data["reply"]) > 0

    async def test_assistant_empty_messages_returns_400(self, client):
        """Empty messages list → 400."""
        resp = await client.post("/api/assistant", json={"messages": []})
        assert resp.status_code == 400

    async def test_assistant_missing_messages_returns_422(self, client):
        """Missing messages field → 422."""
        resp = await client.post("/api/assistant", json={})
        assert resp.status_code == 422

    async def test_assistant_groq_failure_returns_503(self, client):
        """Groq API failure → 503."""
        with patch("app.routers.assistant.general_legal_chat",
                    side_effect=RuntimeError("All Groq models failed")):
            resp = await client.post("/api/assistant", json={
                "messages": [{"role": "user", "content": "What is habeas corpus?"}],
            })
        assert resp.status_code == 503

    async def test_assistant_multi_turn_conversation(self, client, mock_groq):
        """Multi-turn chat should work."""
        with patch("app.routers.assistant.general_legal_chat",
                    return_value="Follow-up legal answer."):
            resp = await client.post("/api/assistant", json={
                "messages": [
                    {"role": "user", "content": "What is Article 14?"},
                    {"role": "assistant", "content": "Right to equality."},
                    {"role": "user", "content": "How does it differ from Article 15?"},
                ],
            })
        assert resp.status_code == 200
        assert resp.json()["reply"] == "Follow-up legal answer."

    async def test_assistant_hindi_query(self, client, mock_groq):
        """Hindi language query should be accepted."""
        with patch("app.routers.assistant.general_legal_chat",
                    return_value="अनुच्छेद 21 जीवन का अधिकार देता है।"):
            resp = await client.post("/api/assistant", json={
                "messages": [{"role": "user", "content": "अनुच्छेद 21 क्या है?"}],
            })
        assert resp.status_code == 200
