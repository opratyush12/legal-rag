"""Tests for app.services.groq_service — LLM interactions."""
import pytest
from unittest.mock import patch, MagicMock
from app.models.schemas import ChatMessage


class TestGroqClient:
    """Groq client initialization."""

    def test_client_raises_without_api_key(self):
        """Missing GROQ_API_KEY → RuntimeError."""
        with patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = ""
            # Clear the lru_cache
            from app.services.groq_service import _client
            _client.cache_clear()
            with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
                _client()
            _client.cache_clear()


class TestChatWithFallback:
    """Model fallback chain for Groq API calls."""

    def test_primary_model_success(self):
        """Primary model works — no fallback needed."""
        from app.services.groq_service import _chat_with_fallback, _client
        _client.cache_clear()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="test reply"))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("app.services.groq_service._client", return_value=mock_client), \
             patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_MODEL = "test-model"
            mock_settings.GROQ_API_KEY = "fake-key"
            result = _chat_with_fallback(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=100,
                temperature=0.5,
            )
        assert result == "test reply"

    def test_fallback_on_decommissioned_model(self):
        """Decommissioned model triggers fallback to next in chain."""
        from app.services.groq_service import _chat_with_fallback, _client
        from groq import BadRequestError
        _client.cache_clear()

        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="fallback reply"))]
        mock_client = MagicMock()

        call_count = [0]
        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise BadRequestError(
                    message="model_not_found",
                    response=MagicMock(status_code=400),
                    body={"error": {"message": "model decommissioned"}},
                )
            return mock_resp

        mock_client.chat.completions.create.side_effect = side_effect

        with patch("app.services.groq_service._client", return_value=mock_client), \
             patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_MODEL = "old-model"
            mock_settings.GROQ_API_KEY = "fake-key"
            result = _chat_with_fallback(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=100,
                temperature=0.5,
            )
        assert result == "fallback reply"

    def test_all_models_fail_raises_runtime_error(self):
        """All models failing → RuntimeError."""
        from app.services.groq_service import _chat_with_fallback, _client
        _client.cache_clear()

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API down")

        with patch("app.services.groq_service._client", return_value=mock_client), \
             patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_MODEL = "fail-model"
            mock_settings.GROQ_API_KEY = "fake-key"
            with pytest.raises(RuntimeError, match="All Groq models failed"):
                _chat_with_fallback(
                    messages=[{"role": "user", "content": "hello"}],
                    max_tokens=100,
                    temperature=0.5,
                )


class TestExpandQuery:
    """Query expansion via Groq."""

    def test_expand_query_no_api_key(self):
        """Without API key, returns original query only."""
        from app.services.groq_service import expand_query
        with patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = ""
            result = expand_query("property dispute", n=3)
        assert result == ["property dispute"]

    def test_expand_query_success(self):
        """Groq returns expanded queries as JSON array."""
        from app.services.groq_service import expand_query
        with patch("app.services.groq_service._chat_with_fallback") as mock_chat, \
             patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "fake-key"
            mock_chat.return_value = '["land ownership case", "immovable property dispute", "property rights IPC"]'
            result = expand_query("property dispute", n=3)
        assert "property dispute" in result  # original always included
        assert len(result) <= 4  # original + up to n variants

    def test_expand_query_groq_failure_returns_original(self):
        """Groq failure → graceful fallback to [original query]."""
        from app.services.groq_service import expand_query
        with patch("app.services.groq_service._chat_with_fallback",
                    side_effect=Exception("API error")), \
             patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "fake-key"
            result = expand_query("property dispute", n=3)
        assert result == ["property dispute"]


class TestGenerateRelevanceSummary:
    """Per-result relevance summary generation."""

    def test_summary_no_api_key(self):
        """Without API key, returns fallback message."""
        from app.services.groq_service import generate_relevance_summary
        with patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = ""
            result = generate_relevance_summary("query", "case text", "100.pdf")
        assert "100.pdf" in result
        assert "GROQ_API_KEY" in result

    def test_summary_success(self):
        """Valid summary generation."""
        from app.services.groq_service import generate_relevance_summary
        with patch("app.services.groq_service._chat_with_fallback",
                    return_value="This case is relevant because..."), \
             patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "fake-key"
            result = generate_relevance_summary("property dispute", "case text", "100.pdf")
        assert result == "This case is relevant because..."

    def test_summary_groq_failure_returns_fallback(self):
        """Groq failure → fallback message (not exception)."""
        from app.services.groq_service import generate_relevance_summary
        with patch("app.services.groq_service._chat_with_fallback",
                    side_effect=Exception("API down")), \
             patch("app.services.groq_service.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "fake-key"
            result = generate_relevance_summary("query", "text", "100.pdf")
        assert "100.pdf" in result


class TestChatWithCase:
    """Case-specific chat via Groq."""

    def test_chat_with_case_returns_reply(self):
        """Valid case chat returns a string reply."""
        from app.services.groq_service import chat_with_case
        messages = [ChatMessage(role="user", content="What is the verdict?")]
        with patch("app.services.groq_service._chat_with_fallback",
                    return_value="The verdict was..."):
            result = chat_with_case("100.pdf", "full case text", messages)
        assert result == "The verdict was..."


class TestGeneralLegalChat:
    """General legal assistant chat."""

    def test_general_chat_returns_reply(self):
        """Valid general chat returns a string reply."""
        from app.services.groq_service import general_legal_chat
        messages = [ChatMessage(role="user", content="What is Article 21?")]
        with patch("app.services.groq_service._chat_with_fallback",
                    return_value="Article 21 protects the right to life."):
            result = general_legal_chat(messages)
        assert result == "Article 21 protects the right to life."
