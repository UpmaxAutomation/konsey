"""Response caching for LLM queries."""

import json
import hashlib
import time
import uuid
from typing import List, Dict, Any, Optional

# Response cache - stores responses to avoid duplicate API calls
# Format: {cache_key: {"response": response, "timestamp": timestamp}}
_response_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # Cache responses for 5 minutes
CACHE_MAX_SIZE = 100  # Maximum number of cached responses


def _get_cache_key(model: str, messages: List[Dict[str, str]], user_id: Optional[uuid.UUID] = None) -> str:
    """Generate a unique cache key for user + model + messages combination.

    Including user_id ensures cache isolation between users - User A cannot
    retrieve User B's cached responses even for identical queries.
    """
    # Include user_id in the key for isolation (None for anonymous users)
    user_key = str(user_id) if user_id else "anonymous"
    content = json.dumps({"user": user_key, "model": model, "messages": messages}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def get_cached_response(model: str, messages: List[Dict[str, str]], user_id: Optional[uuid.UUID] = None) -> Optional[Dict[str, Any]]:
    """Get a cached response if available and not expired (user-isolated)."""
    cache_key = _get_cache_key(model, messages, user_id)
    if cache_key in _response_cache:
        entry = _response_cache[cache_key]
        if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
            return entry["response"]
        else:
            # Expired - remove from cache
            del _response_cache[cache_key]
    return None


def cache_response(model: str, messages: List[Dict[str, str]], response: Dict[str, Any], user_id: Optional[uuid.UUID] = None) -> None:
    """Cache a response with timestamp (user-isolated)."""
    global _response_cache

    # Evict oldest entries if cache is full
    if len(_response_cache) >= CACHE_MAX_SIZE:
        oldest_key = min(_response_cache.keys(), key=lambda k: _response_cache[k]["timestamp"])
        del _response_cache[oldest_key]

    cache_key = _get_cache_key(model, messages, user_id)
    _response_cache[cache_key] = {
        "response": response,
        "timestamp": time.time()
    }


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    now = time.time()
    valid_entries = sum(1 for v in _response_cache.values() if now - v["timestamp"] < CACHE_TTL_SECONDS)
    return {
        "total_entries": len(_response_cache),
        "valid_entries": valid_entries,
        "max_size": CACHE_MAX_SIZE,
        "ttl_seconds": CACHE_TTL_SECONDS
    }


def clear_cache() -> None:
    """Clear the response cache."""
    global _response_cache
    _response_cache = {}
