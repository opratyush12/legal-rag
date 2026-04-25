"""Tests for app.services.tts_service — text-to-speech."""
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
class TestSynthesize:
    """TTS synthesis with voice fallback chain."""

    async def test_synthesize_success(self):
        """Successful synthesis returns audio bytes."""
        from app.services.tts_service import synthesize
        with patch("app.services.tts_service._try_synthesize", new_callable=AsyncMock) as mock_try:
            mock_try.return_value = b"\xff\xfb\x90\x00" * 50
            result = await synthesize("Hello world test text")
        assert isinstance(result, bytes)
        assert len(result) > 0

    async def test_synthesize_empty_text_raises(self):
        """Empty text → ValueError."""
        from app.services.tts_service import synthesize
        with pytest.raises(ValueError, match="empty"):
            await synthesize("")

    async def test_synthesize_whitespace_only_raises(self):
        """Whitespace-only text → ValueError."""
        from app.services.tts_service import synthesize
        with pytest.raises(ValueError, match="empty"):
            await synthesize("   \n  ")

    async def test_synthesize_fallback_on_failure(self):
        """If primary voice fails, falls back to next voice."""
        from app.services.tts_service import synthesize
        call_count = [0]

        async def mock_try(text, voice):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Voice unavailable")
            return b"\xff\xfb" * 10

        with patch("app.services.tts_service._try_synthesize", side_effect=mock_try):
            result = await synthesize("Test fallback voice")
        assert isinstance(result, bytes)
        assert call_count[0] >= 2

    async def test_synthesize_all_voices_fail(self):
        """All voices failing → RuntimeError."""
        from app.services.tts_service import synthesize

        async def mock_try(text, voice):
            raise RuntimeError("Voice failed")

        with patch("app.services.tts_service._try_synthesize", side_effect=mock_try):
            with pytest.raises(RuntimeError, match="All TTS voices failed"):
                await synthesize("This will fail on all voices")

    async def test_synthesize_with_custom_voice(self):
        """Custom voice parameter is tried first."""
        from app.services.tts_service import synthesize
        voices_tried = []

        async def mock_try(text, voice):
            voices_tried.append(voice)
            return b"\xff\xfb" * 10

        with patch("app.services.tts_service._try_synthesize", side_effect=mock_try):
            await synthesize("Test custom voice", voice="en-US-JennyNeural")
        assert voices_tried[0] == "en-US-JennyNeural"


@pytest.mark.asyncio
class TestListVoices:
    """Voice listing."""

    async def test_list_voices_returns_list(self):
        """Returns a list of voice option dicts."""
        from app.services.tts_service import list_voices
        result = await list_voices()
        assert isinstance(result, list)
        assert len(result) == 5
        for v in result:
            assert "short_name" in v
            assert "friendly_name" in v
            assert "locale" in v
            assert "gender" in v
