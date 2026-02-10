"""API key management routes for LLM Council."""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_optional
from ..database.connection import get_db
from ..database import crud as db_crud
from ..database.models import User
from ..config import get_api_keys, set_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["config"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class SetApiKeyRequest(BaseModel):
    """Request to set an API key for a provider."""
    provider: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$', description="Provider name (alphanumeric, max 50 chars)")
    api_key: str = Field(..., min_length=10, max_length=500, description="API key (10-500 chars)")


# ──────────────────────────────────────────────
# Provider API key endpoints
# ──────────────────────────────────────────────

@router.get(
    "/keys",
    tags=["config"],
    summary="Get Configured API Keys",
    response_description="List of configured API keys (masked) and supported providers"
)
async def get_api_keys_endpoint(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all configured API keys (masked for security) - user-specific if authenticated.

    Returns which providers have keys configured. API keys are masked
    to show only the first and last few characters for identification.

    When a provider API key is set, the system will use that provider's
    API directly instead of routing through OpenRouter, potentially
    reducing costs and latency.

    Returns:
        dict: Object containing:
            - api_keys: Dict of provider -> masked key (or empty if not set)
            - providers: List of all supported provider names
    """
    keys = {}
    if current_user:
        # Get user-specific keys from database - optimized single query
        all_providers = [
            "openrouter",
            "openai",
            "anthropic",
            "google",
            "x-ai",
            "deepseek",
            "mistralai",
            "cohere",
            "qwen",
            "perplexity"
        ]

        try:
            # Fetch all user keys in one query
            from sqlalchemy import select
            from ..database.models import UserAPIKey
            result = await db.execute(
                select(UserAPIKey).where(
                    UserAPIKey.user_id == current_user.id,
                    UserAPIKey.is_active == True,
                    UserAPIKey.provider.in_(all_providers)
                )
            )
            user_keys = result.scalars().all()

            # Create a map of provider -> key
            key_map = {key.provider: key for key in user_keys}

            # Decrypt and mask keys
            for provider in all_providers:
                if provider in key_map:
                    try:
                        from ..database.crud.api_keys import _decrypt
                        decrypted = _decrypt(key_map[provider].encrypted_key)
                        # Mask the key
                        if len(decrypted) > 8:
                            keys[provider] = decrypted[:4] + "..." + decrypted[-4:]
                        else:
                            keys[provider] = "***"
                    except Exception as e:
                        keys[provider] = ""
                else:
                    # Fallback to environment variable for OpenRouter if not in DB
                    # ONLY allow this for Admins (BYOK policy for others)
                    if current_user.is_admin and provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
                        env_key = os.getenv("OPENROUTER_API_KEY")
                        if len(env_key) > 8:
                            keys[provider] = env_key[:4] + "..." + env_key[-4:]
                        else:
                            keys[provider] = "***"
                    else:
                        keys[provider] = ""
        except Exception as e:
            logger.error(f"Error fetching API keys from DB: {e}. Falling back to environment variables.")
            # Fallback for all providers if DB fails
            # In crash scenario, we might allow env var for everyone or just admin?
            # Safer to allow only admin or fail safe?
            # If DB is down, we can't check is_admin easily unless we trust the token scopes (if any).
            # For now, let's strictly enforce BYOK: If DB fails, non-admins get nothing.
            is_admin = current_user.is_admin # This might be cached on object

            for provider in all_providers:
                if is_admin and provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
                    env_key = os.getenv("OPENROUTER_API_KEY")
                    if len(env_key) > 8:
                        keys[provider] = env_key[:4] + "..." + env_key[-4:]
                    else:
                        keys[provider] = "***"
                else:
                    keys[provider] = ""
    else:
        # Fallback to global config
        keys = get_api_keys()

    return {
        "api_keys": keys,
        "providers": [
            "openrouter",
            "openai",
            "anthropic",
            "google",
            "x-ai",
            "deepseek",
            "mistralai",
            "cohere",
            "qwen",
            "perplexity"
        ]
    }


@router.post(
    "/keys",
    tags=["config"],
    summary="Set Provider API Key",
    response_description="Confirmation of API key update"
)
async def set_api_key_endpoint(
    request: SetApiKeyRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Set an API key for a specific provider (user-specific if authenticated, global otherwise).

    When set, the system will use the direct provider API instead of
    OpenRouter for that provider's models. This can reduce costs and
    improve latency for high-volume usage.

    Supported providers:
    - openrouter: OpenRouter (for accessing all models via OpenRouter)
    - openai: OpenAI (GPT-4, GPT-3.5, DALL-E)
    - anthropic: Anthropic (Claude models)
    - google: Google (Gemini models)
    - x-ai: xAI (Grok models)
    - deepseek: DeepSeek
    - mistralai: Mistral AI
    - cohere: Cohere

    Args:
        request: SetApiKeyRequest with provider name and API key
        current_user: Authenticated user (optional - if None, uses global config)

    Returns:
        dict: Confirmation with status, message, provider, and has_key flag

    Raises:
        HTTPException 400: If provider name is invalid
    """
    valid_providers = [
        "openrouter",
        "openai",
        "anthropic",
        "google",
        "x-ai",
        "deepseek",
        "mistralai",
        "cohere",
        "qwen",
        "perplexity"
    ]
    if request.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )

    # Require authentication for API key management
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to save API keys. Please log in and try again."
        )

    # Store in database (user-specific)
    try:
        logger.info(f"Saving API key for user {current_user.id}, provider {request.provider}")
        key_record = await db_crud.api_keys.set_user_key(
            db,
            current_user.id,
            request.provider,
            request.api_key or "",
        )
        # Commit the transaction to persist the key
        await db.commit()
        # Verify the key was actually saved by querying it back
        verify_key = await db_crud.api_keys.get_user_key(db, current_user.id, request.provider)
        if not verify_key and request.api_key:
            # Key was saved but can't be retrieved - this is a problem
            logger.warning(f"API key saved but verification failed for user {current_user.id}, provider {request.provider}")
        else:
            logger.info(f"API key saved successfully for user {current_user.id}, provider {request.provider}")
    except Exception as e:
        await db.rollback()
        # Log the actual error for debugging (without sensitive data)
        logger.error(f"Failed to save API key for user {current_user.id}, provider {request.provider}: {type(e).__name__}")
        # Return generic error to client (don't expose internal details)
        raise HTTPException(
            status_code=500,
            detail="Failed to save API key. Please try again."
        )

    return {
        "status": "success",
        "message": f"API key {'set' if request.api_key else 'cleared'} for {request.provider}",
        "provider": request.provider,
        "has_key": bool(request.api_key),
        "user_specific": current_user is not None
    }


@router.delete(
    "/keys/{provider}",
    tags=["config"],
    summary="Delete Provider API Key",
    response_description="Confirmation of API key removal"
)
async def delete_api_key_endpoint(
    provider: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an API key for a provider (user-specific if authenticated).

    After removal, requests for that provider's models will be routed
    through OpenRouter instead of the direct provider API.

    Args:
        provider: Provider name (openrouter, openai, anthropic, google, x-ai, deepseek, mistralai, cohere, qwen)
        current_user: Authenticated user (optional)

    Returns:
        dict: Confirmation with status, message, and provider

    Raises:
        HTTPException 400: If provider name is invalid
    """
    logger.info(f"delete_api_key_endpoint called: provider={provider}, user_authenticated={current_user is not None}")

    valid_providers = [
        "openrouter",
        "openai",
        "anthropic",
        "google",
        "x-ai",
        "deepseek",
        "mistralai",
        "cohere",
        "qwen",
        "perplexity"
    ]
    if provider not in valid_providers:
        logger.warning(f"Invalid provider in delete request: {provider}")
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    if current_user:
        # Delete user-specific key
        logger.info(f"Deleting API key for user {current_user.id}, provider {provider}")
        deleted = await db_crud.api_keys.delete_user_key(db, current_user.id, provider)
        logger.info(f"Delete result: rows_deleted={deleted}")
        # Commit the transaction to persist the deletion
        await db.commit()

        if not deleted:
            logger.warning(f"No API key found to delete for user {current_user.id}, provider {provider}")
            # Still return success - the key doesn't exist, which is the desired state
    else:
        logger.warning(f"No authenticated user for delete request - this may be unexpected")
        # Return an error instead of silently using global config
        raise HTTPException(
            status_code=401,
            detail="Authentication required to delete API keys. Please log in and try again."
        )

    return {
        "status": "success",
        "message": f"API key removed for {provider}",
        "provider": provider,
        "user_specific": current_user is not None
    }


@router.get(
    "/keys/debug",
    tags=["config"],
    summary="Debug API Key Configuration",
    response_description="Diagnostic information about API key setup"
)
async def debug_api_keys(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Debug endpoint to check API key configuration status.

    Helps diagnose issues with API key setup by showing:
    - Whether user is authenticated
    - Which providers have keys configured
    - Whether keys are active
    - Whether system keys exist

    Returns:
        dict: Diagnostic information (no actual key values exposed)
    """
    result = {
        "authenticated": current_user is not None,
        "user_id": str(current_user.id) if current_user else None,
        "providers": {}
    }

    providers = ["openrouter", "openai", "anthropic", "google", "deepseek", "mistralai", "cohere", "qwen", "perplexity"]

    if current_user:
        from sqlalchemy import select
        from ..database.models import UserAPIKey

        # Check each provider
        for provider in providers:
            provider_info = {"has_user_key": False, "is_active": None, "has_system_key": False, "has_env_key": False}

            # Check user key
            key_result = await db.execute(
                select(UserAPIKey).where(
                    UserAPIKey.user_id == current_user.id,
                    UserAPIKey.provider == provider
                )
            )
            key_record = key_result.scalar_one_or_none()
            if key_record:
                provider_info["has_user_key"] = True
                provider_info["is_active"] = key_record.is_active

            # Check system key
            system_key = await db_crud.api_keys.get_system_key(db, provider)
            provider_info["has_system_key"] = system_key is not None

            # Check env key (only for openrouter)
            if provider == "openrouter":
                provider_info["has_env_key"] = bool(os.getenv("OPENROUTER_API_KEY"))

            result["providers"][provider] = provider_info
    else:
        # Not authenticated - check for env/system keys only
        for provider in providers:
            provider_info = {"has_user_key": False, "is_active": None, "has_system_key": False, "has_env_key": False}

            # Check system key
            system_key = await db_crud.api_keys.get_system_key(db, provider)
            provider_info["has_system_key"] = system_key is not None

            if provider == "openrouter":
                provider_info["has_env_key"] = bool(os.getenv("OPENROUTER_API_KEY"))

            result["providers"][provider] = provider_info

    return result
