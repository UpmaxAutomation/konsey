"""Unit tests for openrouter.py - OpenRouter API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from backend.openrouter import (
    query_model,
    query_models_parallel,
    calculate_cost,
    get_session_usage,
    reset_session_usage,
    _get_cache_key,
    _cache_response,
    _get_cached_response,
    clear_cache,
    get_cache_stats,
)


class TestCalculateCost:
    """Tests for cost calculation function."""

    def test_calculate_cost_known_model(self):
        """Test cost calculation for a known model."""
        with patch("backend.openrouter.AVAILABLE_MODELS", {
            "openai/gpt-4o": {"input_cost": 5.0, "output_cost": 15.0}
        }):
            cost = calculate_cost("openai/gpt-4o", 1000, 500)
            # (1000/1M * 5.0) + (500/1M * 15.0) = 0.005 + 0.0075 = 0.0125
            assert abs(cost - 0.0125) < 0.0001

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation returns 0 for unknown model."""
        with patch("backend.openrouter.AVAILABLE_MODELS", {}):
            cost = calculate_cost("unknown/model", 1000, 500)
            assert cost == 0.0

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        with patch("backend.openrouter.AVAILABLE_MODELS", {
            "openai/gpt-4o": {"input_cost": 5.0, "output_cost": 15.0}
        }):
            cost = calculate_cost("openai/gpt-4o", 0, 0)
            assert cost == 0.0


class TestCaching:
    """Tests for response caching functionality."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_cache_key_generation(self):
        """Test cache key is consistent for same inputs."""
        messages = [{"role": "user", "content": "Hello"}]
        key1 = _get_cache_key("model-a", messages)
        key2 = _get_cache_key("model-a", messages)
        assert key1 == key2

    def test_cache_key_differs_by_model(self):
        """Test cache keys differ by model."""
        messages = [{"role": "user", "content": "Hello"}]
        key1 = _get_cache_key("model-a", messages)
        key2 = _get_cache_key("model-b", messages)
        assert key1 != key2

    def test_cache_key_differs_by_message(self):
        """Test cache keys differ by message content."""
        key1 = _get_cache_key("model-a", [{"role": "user", "content": "Hello"}])
        key2 = _get_cache_key("model-a", [{"role": "user", "content": "Goodbye"}])
        assert key1 != key2

    def test_cache_store_and_retrieve(self):
        """Test storing and retrieving from cache."""
        messages = [{"role": "user", "content": "Test"}]
        response = {"content": "Cached response", "usage": {}}

        _cache_response("model", messages, response)
        cached = _get_cached_response("model", messages)

        assert cached == response

    def test_cache_miss(self):
        """Test cache miss returns None."""
        messages = [{"role": "user", "content": "Not cached"}]
        cached = _get_cached_response("model", messages)
        assert cached is None

    def test_cache_stats(self):
        """Test cache statistics."""
        messages = [{"role": "user", "content": "Test"}]
        _cache_response("model", messages, {"content": "Response"})

        stats = get_cache_stats()
        assert stats["total_entries"] == 1
        assert stats["valid_entries"] == 1


class TestSessionUsage:
    """Tests for session usage tracking."""

    def setup_method(self):
        """Reset session usage before each test."""
        reset_session_usage()

    def test_initial_session_usage(self):
        """Test initial session usage is zero."""
        usage = get_session_usage()
        assert usage["total_input_tokens"] == 0
        assert usage["total_output_tokens"] == 0
        assert usage["total_cost"] == 0.0
        assert usage["requests"] == []

    def test_reset_session_usage(self):
        """Test resetting session usage."""
        # Manually set some usage (simulating after requests)
        reset_session_usage()
        usage = get_session_usage()
        assert usage["total_cost"] == 0.0


@pytest.mark.asyncio
class TestQueryModel:
    """Tests for single model query function."""

    async def test_query_model_success(self):
        """Test successful model query."""
        mock_response = {
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        with patch("backend.openrouter.has_direct_api_key", return_value=False):
            with patch("backend.openrouter.is_reasoning_model", return_value=False):
                with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
                    with patch("backend.openrouter.AVAILABLE_MODELS", {"test/model": {"input_cost": 1.0, "output_cost": 2.0}}):
                        with patch("httpx.AsyncClient") as mock_client:
                            mock_instance = AsyncMock()
                            mock_client.return_value.__aenter__.return_value = mock_instance
                            mock_instance.post.return_value = MagicMock(
                                json=lambda: mock_response,
                                raise_for_status=lambda: None
                            )

                            result = await query_model(
                                "test/model",
                                [{"role": "user", "content": "Hello"}],
                                use_cache=False
                            )

        assert result is not None
        assert result["content"] == "Test response"

    async def test_query_model_with_cache_hit(self):
        """Test query returns cached response."""
        clear_cache()
        messages = [{"role": "user", "content": "Cached query"}]
        cached_response = {"content": "Cached!", "usage": {"input_tokens": 10, "output_tokens": 20, "cost": 0.001}}

        _cache_response("test/model", messages, cached_response)

        # Should return cached response without making API call
        with patch("backend.openrouter.has_direct_api_key", return_value=False):
            result = await query_model("test/model", messages, use_cache=True)

        assert result["content"] == "Cached!"
        assert result.get("from_cache") is True

    async def test_query_model_error_handling(self):
        """Test error handling returns None."""
        with patch("backend.openrouter.has_direct_api_key", return_value=False):
            with patch("backend.openrouter.is_reasoning_model", return_value=False):
                with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
                    with patch("httpx.AsyncClient") as mock_client:
                        mock_instance = AsyncMock()
                        mock_client.return_value.__aenter__.return_value = mock_instance
                        mock_instance.post.side_effect = Exception("API Error")

                        result = await query_model(
                            "test/model",
                            [{"role": "user", "content": "Hello"}],
                            use_cache=False
                        )

        assert result is None

    async def test_query_model_reasoning_extended_timeout(self):
        """Test reasoning models use extended timeout."""
        mock_response = {
            "choices": [{"message": {"content": "Response", "reasoning_content": "Thinking..."}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        with patch("backend.openrouter.has_direct_api_key", return_value=False):
            with patch("backend.openrouter.is_reasoning_model", return_value=True):
                with patch("backend.openrouter.REASONING_MODEL_CONFIG", {"extended_timeout": 300, "show_thinking": True}):
                    with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
                        with patch("backend.openrouter.AVAILABLE_MODELS", {"deepseek/r1": {"input_cost": 1.0, "output_cost": 2.0}}):
                            with patch("httpx.AsyncClient") as mock_client:
                                mock_instance = AsyncMock()
                                mock_client.return_value.__aenter__.return_value = mock_instance
                                mock_instance.post.return_value = MagicMock(
                                    json=lambda: mock_response,
                                    raise_for_status=lambda: None
                                )

                                result = await query_model(
                                    "deepseek/r1",
                                    [{"role": "user", "content": "Complex question"}],
                                    use_cache=False
                                )

        assert result is not None
        assert result.get("thinking") == "Thinking..."


@pytest.mark.asyncio
class TestQueryModelsParallel:
    """Tests for parallel model queries."""

    async def test_parallel_queries_same_messages(self):
        """Test parallel queries with same messages for all models."""
        models = ["model-a", "model-b"]
        messages = [{"role": "user", "content": "Hello"}]

        async def mock_query(model, msgs, **kwargs):
            return {"content": f"Response from {model}", "usage": {}}

        with patch("backend.openrouter.query_model", side_effect=mock_query):
            results = await query_models_parallel(models, messages)

        assert len(results) == 2
        assert results["model-a"]["content"] == "Response from model-a"
        assert results["model-b"]["content"] == "Response from model-b"

    async def test_parallel_queries_per_model_messages(self):
        """Test parallel queries with different messages per model."""
        models = ["model-a", "model-b"]
        messages_dict = {
            "model-a": [{"role": "user", "content": "Hello A"}],
            "model-b": [{"role": "user", "content": "Hello B"}],
        }

        async def mock_query(model, msgs, **kwargs):
            return {"content": msgs[0]["content"], "usage": {}}

        with patch("backend.openrouter.query_model", side_effect=mock_query):
            results = await query_models_parallel(models, messages_dict)

        assert results["model-a"]["content"] == "Hello A"
        assert results["model-b"]["content"] == "Hello B"

    async def test_parallel_queries_partial_failure(self):
        """Test parallel queries handle partial failures."""
        models = ["model-a", "model-b"]
        messages = [{"role": "user", "content": "Hello"}]

        async def mock_query(model, msgs, **kwargs):
            if model == "model-a":
                return {"content": "Success", "usage": {}}
            return None  # model-b fails

        with patch("backend.openrouter.query_model", side_effect=mock_query):
            results = await query_models_parallel(models, messages)

        assert results["model-a"] is not None
        assert results["model-b"] is None
