"""OpenRouter API client for making LLM requests."""

import httpx
import json
import hashlib
import time
import uuid
from typing import List, Dict, Any, Optional
from .config import get_openrouter_api_key, OPENROUTER_API_URL, AVAILABLE_MODELS, is_reasoning_model, REASONING_MODEL_CONFIG, has_direct_api_key, get_provider_from_model, get_api_key
from .direct_providers import query_model_direct
from .database import crud as db_crud

# Global token tracking for current session
_session_usage = {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost": 0.0,
    "requests": []
}

# Response cache - stores responses to avoid duplicate API calls
# Format: {cache_key: {"response": response, "timestamp": timestamp}}
_response_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # Cache responses for 5 minutes
CACHE_MAX_SIZE = 100  # Maximum number of cached responses


def _get_cache_key(model: str, messages: List[Dict[str, str]]) -> str:
    """Generate a unique cache key for model + messages combination."""
    content = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def _get_cached_response(model: str, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """Get a cached response if available and not expired."""
    cache_key = _get_cache_key(model, messages)
    if cache_key in _response_cache:
        entry = _response_cache[cache_key]
        if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
            return entry["response"]
        else:
            # Expired - remove from cache
            del _response_cache[cache_key]
    return None


def _cache_response(model: str, messages: List[Dict[str, str]], response: Dict[str, Any]) -> None:
    """Cache a response with timestamp."""
    global _response_cache

    # Evict oldest entries if cache is full
    if len(_response_cache) >= CACHE_MAX_SIZE:
        oldest_key = min(_response_cache.keys(), key=lambda k: _response_cache[k]["timestamp"])
        del _response_cache[oldest_key]

    cache_key = _get_cache_key(model, messages)
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

def reset_session_usage():
    """Reset session usage tracking."""
    global _session_usage
    _session_usage = {
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost": 0.0,
        "requests": []
    }

def get_session_usage():
    """Get current session usage."""
    return _session_usage.copy()

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for a model request."""
    if model not in AVAILABLE_MODELS:
        return 0.0

    pricing = AVAILABLE_MODELS[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input_cost"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_cost"]
    return input_cost + output_cost


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    use_cache: bool = True,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API or direct provider API if key is available.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds (auto-extended for reasoning models)
        use_cache: Whether to use response caching (default True)

    Returns:
        Response dict with 'content', optional 'thinking', optional 'reasoning_details', and 'usage', or None if failed
    """
    global _session_usage

    # Check cache first (if enabled)
    if use_cache:
        cached = _get_cached_response(model, messages)
        if cached:
            # Return cached response with cache flag
            cached_copy = cached.copy()
            cached_copy['from_cache'] = True
            return cached_copy

    # Check if we have a direct API key for this provider (user-specific or system)
    provider = get_provider_from_model(model)
    direct_api_key = None
    if user_id and db:
        # Try user-specific key first, allow system fallback for admin-set keys
        direct_api_key = await db_crud.api_keys.resolve_api_key(db, user_id, provider, allow_system_fallback=True)
    if not direct_api_key and db:
        # Try system key (admin-set) as fallback
        direct_api_key = await db_crud.api_keys.get_system_key(db, provider)
    
    if direct_api_key:
        result = await query_model_direct(model, messages, timeout, api_key=direct_api_key)
        if result:
            # Calculate cost and update session tracking
            input_tokens = result['usage'].get('input_tokens', 0)
            output_tokens = result['usage'].get('output_tokens', 0)
            cost = calculate_cost(model, input_tokens, output_tokens)

            _session_usage["total_input_tokens"] += input_tokens
            _session_usage["total_output_tokens"] += output_tokens
            _session_usage["total_cost"] += cost
            _session_usage["requests"].append({
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "direct_api": True
            })

            result['usage']['cost'] = cost

            # Cache the result from direct API
            if use_cache:
                _cache_response(model, messages, result)

            return result
        # If direct API fails, fall back to OpenRouter
        print(f"Direct API failed for {model}, falling back to OpenRouter")

    # Use extended timeout for reasoning models
    if is_reasoning_model(model):
        timeout = REASONING_MODEL_CONFIG["extended_timeout"]

    # Get OpenRouter API key (user-specific or system admin-set)
    openrouter_key = None
    if user_id and db:
        # Try user-specific OpenRouter key first, allow system fallback
        openrouter_key = await db_crud.api_keys.resolve_api_key(db, user_id, "openrouter", allow_system_fallback=True)
    if not openrouter_key and db:
        # Try system key (admin-set) as fallback
        openrouter_key = await db_crud.api_keys.get_system_key(db, "openrouter")
    
    if not openrouter_key:
        # #region agent log
        import os
        import json
        from datetime import datetime
        debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-resolution","hypothesisId":"H4","location":"openrouter.py:189","message":"no_openrouter_key","data":{"model":model,"user_id":str(user_id) if user_id else None,"provider":provider},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        print(f"No OpenRouter API key available for model {model}. User must set their own key or admin must set system key.")
        return None

    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            # Extract usage info
            usage = data.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)

            # Calculate cost
            cost = calculate_cost(model, input_tokens, output_tokens)

            # Update session tracking
            _session_usage["total_input_tokens"] += input_tokens
            _session_usage["total_output_tokens"] += output_tokens
            _session_usage["total_cost"] += cost
            _session_usage["requests"].append({
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost
            })

            # Extract thinking tokens for reasoning models
            thinking = None
            if is_reasoning_model(model) and REASONING_MODEL_CONFIG["show_thinking"]:
                # Check for thinking in various possible locations
                # DeepSeek R1 and similar models may include thinking in different fields
                if 'reasoning_content' in message:
                    thinking = message.get('reasoning_content')
                elif 'thinking' in message:
                    thinking = message.get('thinking')
                elif usage.get('reasoning_tokens', 0) > 0:
                    # Some models report thinking token count but may not expose content
                    thinking = f"[Reasoning performed: {usage.get('reasoning_tokens')} tokens]"

            result = {
                'content': message.get('content'),
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'cost': cost
                }
            }

            # Add thinking if available
            if thinking:
                result['thinking'] = thinking

            # Keep reasoning_details for backward compatibility
            if 'reasoning_details' in message:
                result['reasoning_details'] = message.get('reasoning_details')

            # Cache successful response
            if use_cache:
                _cache_response(model, messages, result)

            return result

    except Exception as e:
        # #region agent log
        import os
        import json
        from datetime import datetime
        import traceback
        debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"query-model-error","hypothesisId":"H9","location":"openrouter.py:269","message":"query_model_exception","data":{"model":model,"error_type":type(e).__name__,"error":str(e),"user_id":str(user_id) if user_id else None},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        print(f"Error querying model {model}: {e}")
        return None


async def query_model_stream(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
):
    """
    Query a single model via OpenRouter API with streaming.
    Yields chunks as they arrive.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Yields:
        Dict with 'chunk' (text content) or 'done' (final metadata with usage)
    """
    global _session_usage

    # Get OpenRouter API key (user-specific or system admin-set)
    openrouter_key = None
    if user_id and db:
        # Try user-specific OpenRouter key first, allow system fallback
        openrouter_key = await db_crud.api_keys.resolve_api_key(db, user_id, "openrouter", allow_system_fallback=True)
    if not openrouter_key and db:
        # Try system key (admin-set) as fallback
        openrouter_key = await db_crud.api_keys.get_system_key(db, "openrouter")
    
    if not openrouter_key:
        yield {
            "error": True,
            "message": f"No OpenRouter API key available for model {model}. Please set your API key in Settings or contact admin."
        }
        return

    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()

                full_content = ""
                input_tokens = 0
                output_tokens = 0

                async for line in response.aiter_lines():
                    if not line.strip() or line.startswith(":"):
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]

                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)

                            # Extract chunk content
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                chunk = delta.get("content", "")

                                if chunk:
                                    full_content += chunk
                                    yield {"chunk": chunk}

                            # Extract usage info if present
                            if "usage" in data:
                                usage = data["usage"]
                                input_tokens = usage.get("prompt_tokens", 0)
                                output_tokens = usage.get("completion_tokens", 0)

                        except json.JSONDecodeError:
                            continue

                # Calculate cost
                cost = calculate_cost(model, input_tokens, output_tokens)

                # Update session tracking
                _session_usage["total_input_tokens"] += input_tokens
                _session_usage["total_output_tokens"] += output_tokens
                _session_usage["total_cost"] += cost
                _session_usage["requests"].append({
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": cost
                })

                # Yield final metadata
                yield {
                    "done": True,
                    "content": full_content,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost": cost
                    }
                }

    except Exception as e:
        print(f"Error streaming model {model}: {e}")
        yield {
            "error": True,
            "message": str(e)
        }


async def stream_model_response(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
):
    """
    Stream a model response token by token using OpenRouter API.

    This is a convenience wrapper around query_model_stream() with a more
    descriptive name for Quick Mode streaming.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Yields:
        Dict with:
        - 'chunk': text token (during streaming)
        - 'done': True with full metadata (at completion)
        - 'error': True with error message (on failure)
    """
    async for chunk in query_model_stream(model, messages, timeout):
        yield chunk


async def query_models_parallel(
    models: List[str],
    messages: Any,  # List[Dict[str, str]] or Dict[str, List[Dict[str, str]]]
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel (with user-specific API keys if provided).

    Args:
        models: List of OpenRouter model identifiers
        messages: Either a list of message dicts to send to all models,
                 or a dict mapping model IDs to their specific message lists
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Check if messages is a dict (per-model messages) or list (same for all)
    if isinstance(messages, dict):
        # Create tasks with model-specific messages
        tasks = [query_model(model, messages.get(model, []), user_id=user_id, db=db) for model in models]
    else:
        # Create tasks for all models with same messages
        tasks = [query_model(model, messages, user_id=user_id, db=db) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
