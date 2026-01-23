"""Tests for OpenRouter API client."""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from backend.openrouter import (
    _get_cache_key,
    _get_cached_response,
    _cache_response,
    get_cache_stats,
    clear_cache,
    reset_session_usage,
    get_session_usage,
    calculate_cost,
    query_model,
    query_model_stream,
    query_models_parallel,
    CACHE_TTL_SECONDS,
    CACHE_MAX_SIZE,
)


# ============ CACHE TESTS ============

class TestCacheKey:
    """Tests for cache key generation."""

    def test_same_input_same_key(self):
        """Same model and messages should produce same cache key."""
        model = "openai/gpt-4"
        messages = [{"role": "user", "content": "Hello"}]

        key1 = _get_cache_key(model, messages)
        key2 = _get_cache_key(model, messages)

        assert key1 == key2

    def test_different_model_different_key(self):
        """Different models should produce different cache keys."""
        messages = [{"role": "user", "content": "Hello"}]

        key1 = _get_cache_key("openai/gpt-4", messages)
        key2 = _get_cache_key("anthropic/claude-3", messages)

        assert key1 != key2

    def test_different_messages_different_key(self):
        """Different messages should produce different cache keys."""
        model = "openai/gpt-4"

        key1 = _get_cache_key(model, [{"role": "user", "content": "Hello"}])
        key2 = _get_cache_key(model, [{"role": "user", "content": "Goodbye"}])

        assert key1 != key2

    def test_key_is_sha256_hex(self):
        """Cache key should be a valid SHA256 hex string."""
        key = _get_cache_key("model", [{"role": "user", "content": "test"}])

        assert len(key) == 64  # SHA256 produces 64 hex characters
        assert all(c in "0123456789abcdef" for c in key)


class TestCacheOperations:
    """Tests for cache get/set/clear operations."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_cache_miss_returns_none(self):
        """Getting uncached response returns None."""
        result = _get_cached_response("model", [{"role": "user", "content": "test"}])
        assert result is None

    def test_cache_hit_returns_response(self):
        """Cached response is returned on cache hit."""
        model = "openai/gpt-4"
        messages = [{"role": "user", "content": "Hello"}]
        response = {"content": "Hi there!", "usage": {"input_tokens": 10, "output_tokens": 5}}

        _cache_response(model, messages, response)
        cached = _get_cached_response(model, messages)

        assert cached == response

    def test_cache_expiry(self):
        """Expired cache entries are not returned."""
        model = "openai/gpt-4"
        messages = [{"role": "user", "content": "Hello"}]
        response = {"content": "Hi there!"}

        # Cache the response
        _cache_response(model, messages, response)

        # Manually expire the entry
        from backend.openrouter import _response_cache
        cache_key = _get_cache_key(model, messages)
        _response_cache[cache_key]["timestamp"] = time.time() - CACHE_TTL_SECONDS - 1

        # Should return None for expired entry
        cached = _get_cached_response(model, messages)
        assert cached is None

    def test_cache_eviction_when_full(self):
        """Oldest entry is evicted when cache is full."""
        # Fill cache to max
        for i in range(CACHE_MAX_SIZE):
            _cache_response(f"model_{i}", [{"role": "user", "content": f"msg_{i}"}], {"content": f"response_{i}"})
            time.sleep(0.001)  # Ensure different timestamps

        stats = get_cache_stats()
        assert stats["total_entries"] == CACHE_MAX_SIZE

        # Add one more - should evict oldest
        _cache_response("new_model", [{"role": "user", "content": "new"}], {"content": "new_response"})

        stats = get_cache_stats()
        assert stats["total_entries"] == CACHE_MAX_SIZE  # Should still be at max

    def test_clear_cache(self):
        """Clear cache removes all entries."""
        _cache_response("model", [{"role": "user", "content": "test"}], {"content": "response"})

        stats = get_cache_stats()
        assert stats["total_entries"] > 0

        clear_cache()

        stats = get_cache_stats()
        assert stats["total_entries"] == 0


class TestCacheStats:
    """Tests for cache statistics."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_stats_initial_state(self):
        """Initial cache stats show empty cache."""
        stats = get_cache_stats()

        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["max_size"] == CACHE_MAX_SIZE
        assert stats["ttl_seconds"] == CACHE_TTL_SECONDS

    def test_stats_after_caching(self):
        """Stats reflect cached entries."""
        _cache_response("model1", [{"role": "user", "content": "a"}], {"content": "r1"})
        _cache_response("model2", [{"role": "user", "content": "b"}], {"content": "r2"})

        stats = get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2


# ============ SESSION USAGE TESTS ============

class TestSessionUsage:
    """Tests for session usage tracking."""

    def setup_method(self):
        """Reset session usage before each test."""
        reset_session_usage()

    def test_initial_session_usage(self):
        """Initial session usage is zeroed."""
        usage = get_session_usage()

        assert usage["total_input_tokens"] == 0
        assert usage["total_output_tokens"] == 0
        assert usage["total_cost"] == 0.0
        assert usage["requests"] == []

    def test_reset_session_usage(self):
        """Reset clears all session tracking."""
        # Manually modify session usage
        from backend.openrouter import _session_usage
        _session_usage["total_input_tokens"] = 1000
        _session_usage["total_cost"] = 0.05

        reset_session_usage()

        usage = get_session_usage()
        assert usage["total_input_tokens"] == 0
        assert usage["total_cost"] == 0.0

    def test_get_session_usage_returns_copy(self):
        """get_session_usage returns a copy, not the original."""
        usage1 = get_session_usage()
        usage1["total_input_tokens"] = 999

        usage2 = get_session_usage()
        assert usage2["total_input_tokens"] == 0  # Original unchanged


# ============ COST CALCULATION TESTS ============

class TestCostCalculation:
    """Tests for cost calculation."""

    def test_unknown_model_returns_zero(self):
        """Unknown model returns zero cost."""
        cost = calculate_cost("unknown/model", 1000, 500)
        assert cost == 0.0

    @patch("backend.openrouter.AVAILABLE_MODELS", {
        "test/model": {"input_cost": 1.0, "output_cost": 2.0}
    })
    def test_cost_calculation_formula(self):
        """Cost is calculated correctly per million tokens."""
        # 1000 input tokens at $1/M = $0.001
        # 500 output tokens at $2/M = $0.001
        cost = calculate_cost("test/model", 1000, 500)
        assert cost == pytest.approx(0.002, rel=1e-6)

    @patch("backend.openrouter.AVAILABLE_MODELS", {
        "test/model": {"input_cost": 0.0, "output_cost": 0.0}
    })
    def test_free_model_zero_cost(self):
        """Free model returns zero cost."""
        cost = calculate_cost("test/model", 10000, 10000)
        assert cost == 0.0


# ============ QUERY MODEL TESTS ============

class TestQueryModel:
    """Tests for single model queries."""

    def setup_method(self):
        """Clear cache and reset session before each test."""
        clear_cache()
        reset_session_usage()

    @pytest.mark.asyncio
    async def test_returns_cached_response_when_available(self):
        """Returns cached response without API call."""
        model = "openai/gpt-4"
        messages = [{"role": "user", "content": "Hello"}]
        cached_response = {"content": "Cached!", "usage": {"input_tokens": 10, "output_tokens": 5}}

        _cache_response(model, messages, cached_response)

        with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
            result = await query_model(model, messages, use_cache=True)

        assert result["content"] == "Cached!"
        assert result.get("from_cache") is True

    @pytest.mark.asyncio
    async def test_bypasses_cache_when_disabled(self):
        """Doesn't use cache when use_cache=False."""
        model = "openai/gpt-4"
        messages = [{"role": "user", "content": "Hello"}]

        _cache_response(model, messages, {"content": "Cached!"})

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Fresh response!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
            with patch("backend.openrouter.get_provider_from_model", return_value="openai"):
                with patch("backend.openrouter.get_api_key", return_value=None):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                    result = await query_model(model, messages, use_cache=False)

        assert result["content"] == "Fresh response!"
        assert result.get("from_cache") is None

    @pytest.mark.asyncio
    async def test_returns_none_on_api_error(self):
        """Returns None when API call fails."""
        model = "openai/gpt-4"
        messages = [{"role": "user", "content": "Hello"}]

        with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
            with patch("backend.openrouter.get_provider_from_model", return_value="openai"):
                with patch("backend.openrouter.get_api_key", return_value=None):
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                            side_effect=httpx.HTTPError("Connection failed")
                        )

                        result = await query_model(model, messages, use_cache=False)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_api_key(self):
        """Returns None when no API key is available."""
        with patch("backend.openrouter.get_openrouter_api_key", return_value=None):
            with patch("backend.openrouter.get_provider_from_model", return_value="openai"):
                with patch("backend.openrouter.get_api_key", return_value=None):
                    result = await query_model("openai/gpt-4", [{"role": "user", "content": "test"}], use_cache=False)

        assert result is None

    @pytest.mark.asyncio
    async def test_extends_timeout_for_reasoning_models(self):
        """Uses extended timeout for reasoning models."""
        model = "deepseek/deepseek-r1"
        messages = [{"role": "user", "content": "Complex math problem"}]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Answer", "reasoning_content": "Thinking..."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("backend.openrouter.is_reasoning_model", return_value=True):
            with patch("backend.openrouter.REASONING_MODEL_CONFIG", {"extended_timeout": 300, "show_thinking": True}):
                with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
                    with patch("backend.openrouter.get_provider_from_model", return_value="deepseek"):
                        with patch("backend.openrouter.get_api_key", return_value=None):
                            with patch("httpx.AsyncClient") as mock_client:
                                mock_instance = MagicMock()
                                mock_instance.post = AsyncMock(return_value=mock_response)
                                mock_client.return_value.__aenter__.return_value = mock_instance

                                result = await query_model(model, messages, use_cache=False)

                                # Verify AsyncClient was called with extended timeout
                                mock_client.assert_called_once()
                                call_kwargs = mock_client.call_args[1]
                                assert call_kwargs["timeout"] == 300

    @pytest.mark.asyncio
    async def test_extracts_thinking_for_reasoning_models(self):
        """Extracts thinking content for reasoning models."""
        model = "deepseek/deepseek-r1"
        messages = [{"role": "user", "content": "Solve this"}]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "The answer is 42", "reasoning_content": "Let me think step by step..."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("backend.openrouter.is_reasoning_model", return_value=True):
            with patch("backend.openrouter.REASONING_MODEL_CONFIG", {"extended_timeout": 120, "show_thinking": True}):
                with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
                    with patch("backend.openrouter.get_provider_from_model", return_value="deepseek"):
                        with patch("backend.openrouter.get_api_key", return_value=None):
                            with patch("httpx.AsyncClient") as mock_client:
                                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                                result = await query_model(model, messages, use_cache=False)

        assert result["content"] == "The answer is 42"
        assert result["thinking"] == "Let me think step by step..."

    @pytest.mark.asyncio
    async def test_updates_session_usage(self):
        """Session usage is updated after successful query."""
        model = "openai/gpt-4"
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hi!"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("backend.openrouter.AVAILABLE_MODELS", {"openai/gpt-4": {"input_cost": 30.0, "output_cost": 60.0}}):
            with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
                with patch("backend.openrouter.get_provider_from_model", return_value="openai"):
                    with patch("backend.openrouter.get_api_key", return_value=None):
                        with patch("httpx.AsyncClient") as mock_client:
                            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                            await query_model(model, messages, use_cache=False)

        usage = get_session_usage()
        assert usage["total_input_tokens"] == 100
        assert usage["total_output_tokens"] == 50
        assert usage["total_cost"] > 0
        assert len(usage["requests"]) == 1


# ============ PARALLEL QUERY TESTS ============

class TestQueryModelsParallel:
    """Tests for parallel model queries."""

    def setup_method(self):
        """Clear cache and reset session before each test."""
        clear_cache()
        reset_session_usage()

    @pytest.mark.asyncio
    async def test_queries_all_models(self):
        """Queries all models and returns results."""
        models = ["openai/gpt-4", "anthropic/claude-3"]
        messages = [{"role": "user", "content": "Hello"}]

        async def mock_query(model, msgs, **kwargs):
            return {"content": f"Response from {model}"}

        with patch("backend.openrouter.query_model", side_effect=mock_query):
            results = await query_models_parallel(models, messages)

        assert len(results) == 2
        assert results["openai/gpt-4"]["content"] == "Response from openai/gpt-4"
        assert results["anthropic/claude-3"]["content"] == "Response from anthropic/claude-3"

    @pytest.mark.asyncio
    async def test_handles_model_specific_messages(self):
        """Supports different messages per model."""
        models = ["model1", "model2"]
        messages = {
            "model1": [{"role": "user", "content": "Question for model 1"}],
            "model2": [{"role": "user", "content": "Question for model 2"}],
        }

        captured_messages = {}

        async def mock_query(model, msgs, **kwargs):
            captured_messages[model] = msgs
            return {"content": f"Response from {model}"}

        with patch("backend.openrouter.query_model", side_effect=mock_query):
            await query_models_parallel(models, messages)

        assert captured_messages["model1"][0]["content"] == "Question for model 1"
        assert captured_messages["model2"][0]["content"] == "Question for model 2"

    @pytest.mark.asyncio
    async def test_handles_partial_failures(self):
        """Handles case where some models fail."""
        models = ["model1", "model2", "model3"]
        messages = [{"role": "user", "content": "Hello"}]

        async def mock_query(model, msgs, **kwargs):
            if model == "model2":
                return None  # Simulate failure
            return {"content": f"Response from {model}"}

        with patch("backend.openrouter.query_model", side_effect=mock_query):
            results = await query_models_parallel(models, messages)

        assert results["model1"] is not None
        assert results["model2"] is None
        assert results["model3"] is not None


# ============ STREAMING TESTS ============

class TestQueryModelStream:
    """Tests for streaming model queries."""

    def setup_method(self):
        """Reset session before each test."""
        reset_session_usage()

    @pytest.mark.asyncio
    async def test_yields_error_when_no_api_key(self):
        """Yields error when no API key is available."""
        with patch("backend.openrouter.get_openrouter_api_key", return_value=None):
            chunks = []
            async for chunk in query_model_stream("openai/gpt-4", [{"role": "user", "content": "test"}]):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].get("error") is True

    @pytest.mark.asyncio
    async def test_yields_chunks_and_done(self):
        """Yields content chunks followed by done message."""
        async def mock_aiter_lines():
            yield "data: {\"choices\": [{\"delta\": {\"content\": \"Hello\"}}]}"
            yield "data: {\"choices\": [{\"delta\": {\"content\": \" World\"}}]}"
            yield "data: {\"usage\": {\"prompt_tokens\": 10, \"completion_tokens\": 5}}"
            yield "data: [DONE]"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_cm = MagicMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.stream = MagicMock(return_value=mock_stream_cm)
                mock_client.return_value.__aenter__.return_value = mock_instance
                mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

                chunks = []
                async for chunk in query_model_stream("openai/gpt-4", [{"role": "user", "content": "test"}]):
                    chunks.append(chunk)

        # Should have content chunks and a done message
        content_chunks = [c for c in chunks if "chunk" in c]
        done_chunks = [c for c in chunks if c.get("done")]

        assert len(content_chunks) == 2
        assert content_chunks[0]["chunk"] == "Hello"
        assert content_chunks[1]["chunk"] == " World"
        assert len(done_chunks) == 1
        assert done_chunks[0]["content"] == "Hello World"

    @pytest.mark.asyncio
    async def test_yields_error_on_exception(self):
        """Yields error message when exception occurs."""
        with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.stream = MagicMock(side_effect=httpx.HTTPError("Connection failed"))
                mock_client.return_value.__aenter__.return_value = mock_instance
                mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

                chunks = []
                async for chunk in query_model_stream("openai/gpt-4", [{"role": "user", "content": "test"}]):
                    chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].get("error") is True
        assert "Connection failed" in chunks[0]["message"]
