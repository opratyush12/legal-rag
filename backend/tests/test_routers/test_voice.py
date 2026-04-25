"""Tests for /api/voice endpoints — TTS and voice listing."""
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
class TestTTSEndpoint:
    """POST /api/voice/tts — text to speech synthesis."""

    async def test_tts_valid_request(self, client, mock_tts):
        """Valid text returns MP3 audio bytes."""
        with patch("app.routers.voice.synthesize", mock_tts["synthesize"]):
            resp = await client.post("/api/voice/tts", json={
                "text": "This is a test sentence for speech synthesis.",
            })
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/mpeg"
        assert len(resp.content) > 0

    async def test_tts_with_voice_param(self, client, mock_tts):
        """Specifying a voice should pass it through."""
        with patch("app.routers.voice.synthesize", mock_tts["synthesize"]):
            resp = await client.post("/api/voice/tts", json={
                "text": "Testing specific voice parameter in request.",
                "voice": "en-IN-NeerjaNeural",
            })
        assert resp.status_code == 200

    async def test_tts_empty_text(self, client):
        """Empty text should fail validation."""
        resp = await client.post("/api/voice/tts", json={"text": ""})
        # FastAPI may return 422 for empty required field or 400 from ValueError
        assert resp.status_code in (400, 422)

    async def test_tts_text_too_long(self, client):
        """Text > 3000 chars → 422."""
        resp = await client.post("/api/voice/tts", json={
            "text": "x" * 3001,
        })
        assert resp.status_code == 422

    async def test_tts_max_length_text(self, client, mock_tts):
        """Text of exactly 3000 chars should be accepted."""
        with patch("app.routers.voice.synthesize", mock_tts["synthesize"]):
            resp = await client.post("/api/voice/tts", json={
                "text": "x" * 3000,
            })
        assert resp.status_code == 200

    async def test_tts_synthesis_failure_returns_500(self, client):
        """TTS engine failure → 500."""
        with patch("app.routers.voice.synthesize", new_callable=AsyncMock) as mock_s:
            mock_s.side_effect = Exception("edge-tts failed")
            resp = await client.post("/api/voice/tts", json={
                "text": "This should fail during synthesis.",
            })
        assert resp.status_code == 500

    async def test_tts_value_error_returns_400(self, client):
        """ValueError from synthesize → 400."""
        with patch("app.routers.voice.synthesize", new_callable=AsyncMock) as mock_s:
            mock_s.side_effect = ValueError("Cannot synthesize empty text.")
            resp = await client.post("/api/voice/tts", json={
                "text": "Some text that triggers value error.",
            })
        assert resp.status_code == 400

    async def test_tts_missing_text_field(self, client):
        """Missing text → 422."""
        resp = await client.post("/api/voice/tts", json={})
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestVoicesEndpoint:
    """GET /api/voice/voices — list available TTS voices."""

    async def test_list_voices(self, client, mock_tts):
        """Returns a list of voice options."""
        with patch("app.routers.voice.list_voices", mock_tts["list_voices"]):
            resp = await client.get("/api/voice/voices")
        assert resp.status_code == 200
        data = resp.json()
        assert "voices" in data
        assert isinstance(data["voices"], list)
        assert len(data["voices"]) >= 1
        assert "short_name" in data["voices"][0]
