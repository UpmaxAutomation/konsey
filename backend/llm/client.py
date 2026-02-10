"""Core LLM query functions for OpenRouter and direct provider APIs."""

import httpx
import json
import logging
import uuid
from typing import List, Dict, Any, Optional

from .cache import get_cached_response, cache_response
from .usage import record_usage, calculate_cost

logger = logging.getLogger(__name__)


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 60.0,
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
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Returns:
        Response dict with 'content', optional 'thinking', optional 'reasoning_details', and 'usage', or None if failed
    """
    from ..config import (
        OPENROUTER_API_URL,
        is_reasoning_model,
        REASONING_MODEL_CONFIG,
        get_provider_from_model
    )
    from ..database import crud as db_crud
    from ..direct_providers import query_model_direct
    from ..http_client import get_client

    # Disable caching for multimodal content (images are too large to cache efficiently)
    has_multimodal = any(
        isinstance(msg.get("content"), list) for msg in messages
    )
    if has_multimodal:
        use_cache = False

    # Check cache first (if enabled) - user-isolated cache
    if use_cache:
        cached = get_cached_response(model, messages, user_id)
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
            # Calculate cost and record usage
            input_tokens = result['usage'].get('input_tokens', 0)
            output_tokens = result['usage'].get('output_tokens', 0)
            cost = calculate_cost(model, input_tokens, output_tokens)

            await record_usage(model, input_tokens, output_tokens, cost, user_id, db, direct_api=True)

            result['usage']['cost'] = cost

            # Cache the result from direct API (user-isolated)
            if use_cache:
                cache_response(model, messages, result, user_id)

            return result
        # If direct API fails, fall back to OpenRouter
        logger.warning(f"Direct API failed for {model}, falling back to OpenRouter")

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
        logger.warning(f"No OpenRouter API key available for model {model}. User must set their own key or admin must set system key.")
        return None

    # Normalize key to avoid unicode whitespace issues in headers
    if isinstance(openrouter_key, str):
        openrouter_key = openrouter_key.replace("\u2028", "").replace("\u2029", "").strip()

    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        # Use shared HTTP client for connection reuse
        client = get_client()
        response = await client.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()

        data = response.json()
        message = data['choices'][0]['message']

        # Extract usage info
        usage = data.get('usage', {})
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)

        # Calculate cost and record usage
        cost = calculate_cost(model, input_tokens, output_tokens)

        await record_usage(model, input_tokens, output_tokens, cost, user_id, db)

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

        # Cache successful response (user-isolated)
        if use_cache:
            cache_response(model, messages, result, user_id)

        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error querying model {model}: {e.response.status_code} - {e}")
        return None
    except Exception as e:
        logger.error(f"Error querying model {model}: {e}")
        return None


async def query_model_stream(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 60.0,
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
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Yields:
        Dict with 'chunk' (text content) or 'done' (final metadata with usage)
    """
    from ..config import OPENROUTER_API_URL, get_provider_from_model
    from ..database import crud as db_crud
    from ..http_client import get_client

    # Get OpenRouter API key (user-specific or system admin-set)
    openrouter_key = None
    if user_id and db:
        # Try user-specific OpenRouter key first, allow system fallback for all users
        openrouter_key = await db_crud.api_keys.resolve_api_key(db, user_id, "openrouter", allow_system_fallback=True)
        logger.info(f"User key lookup result for openrouter: {'found' if openrouter_key else 'not found'}")
    if not openrouter_key and db:
        # Try system key (admin-set) as fallback
        openrouter_key = await db_crud.api_keys.get_system_key(db, "openrouter")

    if not openrouter_key:
        # Check if user has a direct provider key (to give a better error message)
        provider = get_provider_from_model(model)
        has_direct_key = False
        if user_id and db:
            direct_key = await db_crud.api_keys.resolve_api_key(db, user_id, provider, allow_system_fallback=True)
            has_direct_key = direct_key is not None

        logger.warning(f"No OpenRouter key for streaming: user_id={user_id}, model={model}, provider={provider}, has_direct_key={has_direct_key}")

        if has_direct_key:
            yield {
                "error": True,
                "message": f"You have a {provider} API key, but streaming requires an OpenRouter key. Please add an OpenRouter API key in Settings."
            }
        else:
            yield {
                "error": True,
                "message": f"No API key available for model {model}. Please set your OpenRouter or {provider} API key in Settings."
            }
        return

    # Normalize key to avoid unicode whitespace issues in headers
    if isinstance(openrouter_key, str):
        openrouter_key = openrouter_key.replace("\u2028", "").replace("\u2029", "").strip()

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
        # Use shared HTTP client for connection reuse
        client = get_client()
        async with client.stream(
            "POST",
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        ) as response:
            if response.status_code >= 400:
                # Capture error body for diagnostics
                try:
                    raw_body = await response.aread()
                    body_text = raw_body.decode("utf-8", errors="replace")
                except Exception:
                    body_text = ""
                logger.error(f"OpenRouter error response: status={response.status_code}, body={body_text[:500]}")
                response.raise_for_status()

            full_content = ""
            input_tokens = 0
            output_tokens = 0

            buffer = ""
            async for raw in response.aiter_raw():
                if not raw:
                    continue
                try:
                    buffer += raw.decode("utf-8", errors="replace")
                except Exception:
                    continue
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip("\r")
                    if not line.strip() or line.startswith(":"):
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]

                        if data_str == "[DONE]":
                            buffer = ""
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

            # Calculate cost and record usage
            cost = calculate_cost(model, input_tokens, output_tokens)

            await record_usage(model, input_tokens, output_tokens, cost, user_id, db)

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
        logger.error(f"Error streaming model {model}: {e}")
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
