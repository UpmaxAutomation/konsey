"""Centralized API key resolution for LLM providers.

This module provides a single source of truth for API key resolution,
with a consistent priority order:
1. User-specific key from database
2. System key from database (admin-set)
3. Environment variable fallback

Usage:
    from backend.keys import resolve_api_key, get_provider_from_model

    key = await resolve_api_key(db, user_id, "openai")
    key = await resolve_api_key(db, user_id, "openrouter")
"""

import os
import uuid
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


# Provider to environment variable mapping
PROVIDER_ENV_VARS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
}

# Model prefix to provider mapping
MODEL_PREFIXES = {
    "openai/": "openai",
    "anthropic/": "anthropic",
    "google/": "google",
    "meta-llama/": "meta",
    "mistralai/": "mistral",
    "deepseek/": "deepseek",
    "x-ai/": "xai",
    "perplexity/": "perplexity",
    "cohere/": "cohere",
    "qwen/": "qwen",
}


def get_provider_from_model(model: str) -> str:
    """
    Extract provider name from model identifier.

    Args:
        model: Full model identifier (e.g., "openai/gpt-4o")

    Returns:
        Provider name (e.g., "openai")
    """
    for prefix, provider in MODEL_PREFIXES.items():
        if model.startswith(prefix):
            return provider

    # Default: extract from model string
    if "/" in model:
        return model.split("/")[0]

    return "unknown"


def _get_env_key(provider: str) -> Optional[str]:
    """Get API key from environment variable."""
    env_var = PROVIDER_ENV_VARS.get(provider)
    if env_var:
        return os.getenv(env_var)
    return None


async def resolve_api_key(
    db: Any,
    user_id: Optional[uuid.UUID],
    provider: str,
    allow_system_fallback: bool = True,
    allow_env_fallback: bool = True
) -> Optional[str]:
    """
    Resolve API key for a provider with consistent priority.

    Resolution order:
    1. User-specific key from database (if user_id provided)
    2. System key from database (if allow_system_fallback)
    3. Environment variable (if allow_env_fallback)

    Args:
        db: Database session
        user_id: User UUID (optional)
        provider: Provider name (e.g., "openai", "openrouter")
        allow_system_fallback: Whether to fall back to system keys
        allow_env_fallback: Whether to fall back to environment variables

    Returns:
        API key string or None if not found
    """
    from .database import crud as db_crud

    # 1. Try user-specific key
    if user_id and db:
        try:
            user_key = await db_crud.api_keys.get_user_key(db, user_id, provider)
            if user_key:
                logger.debug(f"Using user-specific key for {provider}")
                return user_key
        except Exception as e:
            logger.warning(f"Error getting user key for {provider}: {e}")

    # 2. Try system key (admin-set)
    if allow_system_fallback and db:
        try:
            system_key = await db_crud.api_keys.get_system_key(db, provider)
            if system_key:
                logger.debug(f"Using system key for {provider}")
                return system_key
        except Exception as e:
            logger.warning(f"Error getting system key for {provider}: {e}")

    # 3. Try environment variable
    if allow_env_fallback:
        env_key = _get_env_key(provider)
        if env_key:
            logger.debug(f"Using environment key for {provider}")
            return env_key

    logger.debug(f"No key found for {provider}")
    return None


async def resolve_openrouter_key(
    db: Any,
    user_id: Optional[uuid.UUID],
) -> Optional[str]:
    """Convenience function to resolve OpenRouter key."""
    return await resolve_api_key(db, user_id, "openrouter")


async def resolve_direct_provider_key(
    db: Any,
    user_id: Optional[uuid.UUID],
    model: str,
) -> Optional[str]:
    """
    Resolve direct API key for a model's provider.

    Use this when you want to call a provider directly (not via OpenRouter).

    Args:
        db: Database session
        user_id: User UUID (optional)
        model: Full model identifier (e.g., "openai/gpt-4o")

    Returns:
        Direct provider API key or None
    """
    provider = get_provider_from_model(model)
    return await resolve_api_key(db, user_id, provider)


async def has_api_key(
    db: Any,
    user_id: Optional[uuid.UUID],
    provider: str,
) -> bool:
    """
    Check if any API key is available for a provider.

    Args:
        db: Database session
        user_id: User UUID (optional)
        provider: Provider name

    Returns:
        True if any key is available
    """
    key = await resolve_api_key(db, user_id, provider)
    return key is not None


async def get_available_providers(
    db: Any,
    user_id: Optional[uuid.UUID],
) -> list[str]:
    """
    Get list of providers with available API keys.

    Args:
        db: Database session
        user_id: User UUID (optional)

    Returns:
        List of provider names with keys
    """
    available = []
    for provider in PROVIDER_ENV_VARS.keys():
        if await has_api_key(db, user_id, provider):
            available.append(provider)
    return available
