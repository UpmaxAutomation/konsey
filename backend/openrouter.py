"""OpenRouter API client for making LLM requests.

BACKWARDS COMPATIBILITY SHIM: This module re-exports everything from
backend.llm for existing code that imports from backend.openrouter.

New code should import directly from backend.llm:
    from backend.llm import query_model, query_model_stream, query_models_parallel
"""

# Re-export everything from the new llm package for backwards compatibility
from .llm import (
    # Core query functions
    query_model,
    query_model_stream,
    stream_model_response,
    query_models_parallel,
    # Cache functions
    get_cached_response as _get_cached_response,
    cache_response as _cache_response,
    get_cache_stats,
    clear_cache,
    # Usage functions
    get_session_usage,
    reset_session_usage,
    get_user_session_usage,
    reset_user_session_usage,
    record_usage as _record_usage,
    calculate_cost,
)

# Also import the cache/usage module internals for tests that access _response_cache etc.
from .llm.cache import _response_cache, CACHE_TTL_SECONDS, CACHE_MAX_SIZE
from .llm.usage import _session_usage

__all__ = [
    "query_model",
    "query_model_stream",
    "stream_model_response",
    "query_models_parallel",
    "get_cache_stats",
    "clear_cache",
    "get_session_usage",
    "reset_session_usage",
    "get_user_session_usage",
    "reset_user_session_usage",
    "calculate_cost",
    # Internal names for backward compat
    "_get_cached_response",
    "_cache_response",
    "_record_usage",
    "_response_cache",
    "_session_usage",
    "CACHE_TTL_SECONDS",
    "CACHE_MAX_SIZE",
]
