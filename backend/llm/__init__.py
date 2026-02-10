"""
LLM client package for OpenRouter and direct provider APIs.

This package provides the core LLM querying functionality:
- Single model queries (sync and streaming)
- Parallel model queries
- Response caching (user-isolated)
- Usage and cost tracking

Usage:
    from backend.llm import query_model, query_model_stream, query_models_parallel

    # Single query
    response = await query_model("openai/gpt-4o", messages)

    # Streaming query
    async for chunk in query_model_stream("openai/gpt-4o", messages):
        print(chunk)

    # Parallel queries
    responses = await query_models_parallel(["openai/gpt-4o", "anthropic/claude-sonnet-4"], messages)
"""

# Core query functions
from .client import (
    query_model,
    query_model_stream,
    stream_model_response,
    query_models_parallel,
)

# Cache functions
from .cache import (
    get_cached_response,
    cache_response,
    get_cache_stats,
    clear_cache,
)

# Usage functions
from .usage import (
    get_session_usage,
    reset_session_usage,
    get_user_session_usage,
    reset_user_session_usage,
    record_usage,
    calculate_cost,
)

__all__ = [
    # Core query functions
    "query_model",
    "query_model_stream",
    "stream_model_response",
    "query_models_parallel",
    # Cache functions
    "get_cached_response",
    "cache_response",
    "get_cache_stats",
    "clear_cache",
    # Usage functions
    "get_session_usage",
    "reset_session_usage",
    "get_user_session_usage",
    "reset_user_session_usage",
    "record_usage",
    "calculate_cost",
]
