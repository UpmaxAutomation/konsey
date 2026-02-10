"""Config, presets, usage, and cache routes for LLM Council."""

import logging
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_optional
from ..config import (
    AVAILABLE_MODELS,
    DEFAULT_CHAIRMAN_MODEL,
    DEFAULT_COUNCIL_MODELS,
    apply_preset,
    get_api_keys,
    get_chairman_model,
    get_council_models,
    get_enhanced_features,
    get_presets,
    set_chairman_model,
    set_council_models,
)
from ..database import crud as db_crud
from ..database.connection import get_db
from ..database.models import User
from ..model_sync import get_available_models
from ..openrouter import (
    clear_cache,
    get_cache_stats,
    get_session_usage,
    reset_session_usage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["config"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class ConfigUpdateRequest(BaseModel):
    """Request to update council configuration."""
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None


class CostEstimateRequest(BaseModel):
    """Request to estimate cost before sending a query."""
    message_length: int
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None


# ──────────────────────────────────────────────
# Shared state helpers
# ──────────────────────────────────────────────
#
# _dynamic_models and _models_last_synced live as module-level globals in
# backend.main.  To avoid circular imports we access them lazily through
# sys.modules when the request handler actually runs (main is always
# loaded before any request arrives).
# ──────────────────────────────────────────────

def _get_main_module():
    """Lazy accessor for the main module to avoid circular imports."""
    import sys
    return sys.modules["backend.main"]


def _get_all_models() -> dict:
    """Get combined models (dynamic + fallback).

    Mirrors ``backend.main.get_all_models`` using the same underlying
    ``_dynamic_models`` global so that values stay consistent.
    """
    main = _get_main_module()
    combined = AVAILABLE_MODELS.copy()
    combined.update(getattr(main, "_dynamic_models", {}))
    return combined


def _get_models_last_synced() -> Optional[str]:
    """Return the ISO timestamp of the last OpenRouter model sync."""
    main = _get_main_module()
    return getattr(main, "_models_last_synced", None)


# ──────────────────────────────────────────────
# Config endpoints
# ──────────────────────────────────────────────

@router.get(
    "/config",
    tags=["config"],
    summary="Get Council Configuration",
    response_description="Current council configuration including models and defaults",
)
async def get_config(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current council configuration (user-specific if authenticated).

    Returns the active council member models, chairman model, all available models,
    default configurations, and sync status.

    The council models are the LLMs that participate in Stage 1 (response collection)
    and Stage 2 (peer review). The chairman model synthesizes the final answer in Stage 3.

    Args:
        current_user: Authenticated user (optional - if None, uses global config)

    Returns:
        dict: Configuration object containing:
            - council_models: List of active council member model IDs
            - chairman_model: The chairman model ID for synthesis
            - available_models: Dict of all available models with metadata
            - defaults: Default council and chairman configurations
            - models_count: Total number of available models
            - last_synced: ISO timestamp of last OpenRouter sync
            - api_keys: Masked API keys (user-specific if authenticated)
    """
    all_models = _get_all_models()

    # Get user-specific config if authenticated
    if current_user:
        settings = await db_crud.settings.get_by_user_id(db, current_user.id)
        if settings:
            council_models = settings.council_models or DEFAULT_COUNCIL_MODELS.copy()
            chairman_model = settings.chairman_model or DEFAULT_CHAIRMAN_MODEL
            base_features = get_enhanced_features()
            user_features = settings.enhanced_features or {}
            enhanced_features = {**base_features, **user_features}
        else:
            # Create default settings for new user
            settings = await db_crud.settings.create(db, current_user.id)
            council_models = settings.council_models
            chairman_model = settings.chairman_model
            enhanced_features = get_enhanced_features()

        # Get user API keys (masked) - optimized single query
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
            "perplexity",
        ]
        api_keys = {}

        # Fetch all user keys in one query
        from sqlalchemy import select

        from ..database.models import UserAPIKey

        result = await db.execute(
            select(UserAPIKey).where(
                UserAPIKey.user_id == current_user.id,
                UserAPIKey.is_active == True,
                UserAPIKey.provider.in_(all_providers),
            )
        )
        user_keys = result.scalars().all()

        # Create a map of provider -> key
        key_map = {key.provider: key for key in user_keys}

        # Decrypt and mask keys
        for provider in all_providers:
            if provider in key_map:
                key_record = key_map[provider]
                # Only include active keys
                if not key_record.is_active:
                    api_keys[provider] = ""
                    continue
                try:
                    from ..database.crud.api_keys import _decrypt

                    decrypted = _decrypt(key_record.encrypted_key)
                    if len(decrypted) > 8:
                        api_keys[provider] = decrypted[:4] + "..." + decrypted[-4:]
                    else:
                        api_keys[provider] = "***"
                except Exception:
                    api_keys[provider] = ""
            else:
                # Fallback to environment variable for OpenRouter
                if provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
                    env_key = os.getenv("OPENROUTER_API_KEY")
                    if len(env_key) > 8:
                        api_keys[provider] = env_key[:4] + "..." + env_key[-4:]
                    else:
                        api_keys[provider] = "***"
                else:
                    api_keys[provider] = ""
    else:
        # Fallback to global config
        council_models = get_council_models()
        chairman_model = get_chairman_model()
        api_keys = get_api_keys()
        enhanced_features = get_enhanced_features()

    return {
        "council_models": council_models,
        "chairman_model": chairman_model,
        "available_models": all_models,
        "defaults": {
            "council_models": DEFAULT_COUNCIL_MODELS,
            "chairman_model": DEFAULT_CHAIRMAN_MODEL,
        },
        "models_count": len(all_models),
        "last_synced": _get_models_last_synced(),
        "api_keys": api_keys,
        "enhanced_features": enhanced_features,
    }


@router.post(
    "/config",
    tags=["config"],
    summary="Update Council Configuration",
    response_description="Updated council configuration",
)
async def update_config(
    request: ConfigUpdateRequest,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the council configuration (user-specific if authenticated).

    Allows changing the council member models and/or the chairman model.
    All model IDs must be valid (exist in available_models).

    Args:
        request: ConfigUpdateRequest with optional council_models and chairman_model
        current_user: Authenticated user (optional - if None, uses global config)

    Returns:
        dict: Updated configuration with council_models and chairman_model

    Raises:
        HTTPException 400: If any specified model ID is invalid
    """
    all_models = _get_all_models()

    if current_user:
        # Update user-specific settings
        settings = await db_crud.settings.get_by_user_id(db, current_user.id)
        if not settings:
            settings = await db_crud.settings.create(db, current_user.id)

        council_models = (
            request.council_models
            if request.council_models is not None
            else settings.council_models
        )
        chairman_model = (
            request.chairman_model
            if request.chairman_model is not None
            else settings.chairman_model
        )

        # Validate models
        if request.council_models is not None:
            for model in request.council_models:
                if model not in all_models:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid model: {model}"
                    )

        if request.chairman_model is not None:
            if request.chairman_model not in all_models:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid chairman model: {request.chairman_model}",
                )

        # Update user settings
        await db_crud.settings.set_council_config(
            db,
            current_user.id,
            council_models,
            chairman_model,
        )

        return {
            "council_models": council_models,
            "chairman_model": chairman_model,
        }
    else:
        # Fallback to global config
        if request.council_models is not None:
            # Validate models
            for model in request.council_models:
                if model not in all_models:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid model: {model}"
                    )
            set_council_models(request.council_models)

        if request.chairman_model is not None:
            if request.chairman_model not in all_models:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid chairman model: {request.chairman_model}",
                )
            set_chairman_model(request.chairman_model)

        return {
            "council_models": get_council_models(),
            "chairman_model": get_chairman_model(),
        }


@router.post(
    "/config/reset",
    tags=["config"],
    summary="Reset Configuration to Defaults",
    response_description="Default council configuration",
)
async def reset_config():
    """
    Reset the council configuration to default values.

    Restores both council member models and chairman model to their
    default configurations as defined in the application settings.

    Returns:
        dict: Default configuration with council_models and chairman_model
    """
    set_council_models(DEFAULT_COUNCIL_MODELS.copy())
    set_chairman_model(DEFAULT_CHAIRMAN_MODEL)
    return {
        "council_models": get_council_models(),
        "chairman_model": get_chairman_model(),
    }


# ──────────────────────────────────────────────
# Cost estimation
# ──────────────────────────────────────────────

@router.post(
    "/estimate-cost",
    tags=["config"],
    summary="Estimate Query Cost",
    response_description="Estimated cost range for a council query",
)
async def estimate_cost(request: CostEstimateRequest):
    """
    Estimate the cost of a council query before sending it.

    Calculates the expected cost based on message length and current model configuration.
    The estimation accounts for all 3 stages of the council deliberation process:

    - **Stage 1**: Each council model receives the user's query
    - **Stage 2**: Each council model receives all Stage 1 responses + ranking prompt (~1500 tokens overhead)
    - **Stage 3**: Chairman receives everything + synthesis prompt (~2000 tokens overhead)

    Token estimation: ~4 characters per token (conservative estimate)

    Args:
        request: CostEstimateRequest containing:
            - message_length: Character length of the user's message
            - council_models: Optional list of model IDs (defaults to current config)
            - chairman_model: Optional chairman model ID (defaults to current config)

    Returns:
        dict: Cost estimate containing:
            - min_cost: Lower bound estimate (USD)
            - max_cost: Upper bound estimate (USD)
            - breakdown: Detailed cost per stage
            - models_used: List of models included in estimate
            - token_estimates: Estimated tokens per stage
    """
    all_models = _get_all_models()

    # Use provided models or fall back to current config
    council_models = request.council_models or get_council_models()
    chairman = request.chairman_model or get_chairman_model()

    # Estimate tokens from message length (~4 chars per token)
    input_tokens = max(request.message_length // 4, 1)

    # Average response length estimate (tokens per model response)
    avg_response_tokens = 500  # Conservative estimate
    response_variance = 200  # For min/max range

    # Stage 1: Each council model receives the query
    stage1_input_tokens = input_tokens
    stage1_output_tokens_min = avg_response_tokens - response_variance
    stage1_output_tokens_max = avg_response_tokens + response_variance

    # Stage 2: Each council model receives all responses + ranking prompt
    num_models = len(council_models)
    ranking_prompt_overhead = 1500  # System prompt + ranking instructions
    stage2_input_tokens = (
        input_tokens
        + (num_models * avg_response_tokens)  # All Stage 1 responses
        + ranking_prompt_overhead
    )
    stage2_output_tokens_min = 300  # Ranking output is typically shorter
    stage2_output_tokens_max = 600

    # Stage 3: Chairman receives everything + synthesis prompt
    synthesis_prompt_overhead = 2000
    stage3_input_tokens = (
        input_tokens
        + (num_models * avg_response_tokens)  # Stage 1 responses
        + (num_models * 400)  # Stage 2 rankings (shorter)
        + synthesis_prompt_overhead
    )
    stage3_output_tokens_min = avg_response_tokens
    stage3_output_tokens_max = (
        avg_response_tokens + response_variance * 2
    )  # Chairman often writes more

    # Calculate costs per stage
    def get_model_cost(model_id: str, input_toks: int, output_toks: int) -> float:
        """Calculate cost for a model query in USD."""
        model_info = all_models.get(
            model_id, {"input_cost": 2.0, "output_cost": 8.0}
        )
        input_cost_per_m = model_info.get("input_cost", 2.0)
        output_cost_per_m = model_info.get("output_cost", 8.0)
        return (input_toks * input_cost_per_m / 1_000_000) + (
            output_toks * output_cost_per_m / 1_000_000
        )

    # Stage 1 costs (all council models)
    stage1_min = sum(
        get_model_cost(m, stage1_input_tokens, stage1_output_tokens_min)
        for m in council_models
    )
    stage1_max = sum(
        get_model_cost(m, stage1_input_tokens, stage1_output_tokens_max)
        for m in council_models
    )

    # Stage 2 costs (all council models evaluate)
    stage2_min = sum(
        get_model_cost(m, stage2_input_tokens, stage2_output_tokens_min)
        for m in council_models
    )
    stage2_max = sum(
        get_model_cost(m, stage2_input_tokens, stage2_output_tokens_max)
        for m in council_models
    )

    # Stage 3 costs (chairman only)
    stage3_min = get_model_cost(chairman, stage3_input_tokens, stage3_output_tokens_min)
    stage3_max = get_model_cost(chairman, stage3_input_tokens, stage3_output_tokens_max)

    # Total costs
    total_min = stage1_min + stage2_min + stage3_min
    total_max = stage1_max + stage2_max + stage3_max

    return {
        "min_cost": round(total_min, 6),
        "max_cost": round(total_max, 6),
        "breakdown": {
            "stage1": {"min": round(stage1_min, 6), "max": round(stage1_max, 6)},
            "stage2": {"min": round(stage2_min, 6), "max": round(stage2_max, 6)},
            "stage3": {"min": round(stage3_min, 6), "max": round(stage3_max, 6)},
        },
        "models_used": {"council": council_models, "chairman": chairman},
        "token_estimates": {
            "stage1": {
                "input": stage1_input_tokens,
                "output_range": [stage1_output_tokens_min, stage1_output_tokens_max],
            },
            "stage2": {
                "input": stage2_input_tokens,
                "output_range": [stage2_output_tokens_min, stage2_output_tokens_max],
            },
            "stage3": {
                "input": stage3_input_tokens,
                "output_range": [stage3_output_tokens_min, stage3_output_tokens_max],
            },
        },
    }


# ──────────────────────────────────────────────
# Preset endpoints
# ──────────────────────────────────────────────

@router.get(
    "/presets",
    tags=["config"],
    summary="List Council Presets",
    response_description="List of available preset configurations",
)
async def list_presets():
    """
    List all available council presets.

    Presets are pre-configured council compositions optimized for different
    use cases. Each preset defines both the council member models and the
    chairman model.

    Available presets typically include:
    - **code_review**: Expert code reviewers for technical analysis
    - **research**: Deep research and analysis models
    - **creative**: Creative writing and brainstorming
    - **reasoning**: Complex logic and mathematics
    - **budget**: Cost-effective model selection

    Returns:
        dict: Object containing:
            - presets: List of preset objects with id, name, description, models, chairman
    """
    presets = get_presets()
    # Transform dict into list with ids
    presets_list = [
        {
            "id": preset_id,
            "name": preset_data["name"],
            "description": preset_data["description"],
            "models": preset_data["models"],
            "chairman": preset_data["chairman"],
        }
        for preset_id, preset_data in presets.items()
    ]
    return {"presets": presets_list}


@router.post(
    "/presets/{preset_id}/apply",
    tags=["config"],
    summary="Apply Council Preset",
    response_description="Confirmation of preset application with new configuration",
)
async def apply_council_preset(preset_id: str):
    """
    Apply a preset configuration to the council.

    This will update both the council member models and the chairman model
    to the preset's configuration. The change takes effect immediately
    for subsequent council queries.

    Args:
        preset_id: The preset identifier (e.g., "code_review", "research")

    Returns:
        dict: Confirmation object containing:
            - status: "success"
            - message: Human-readable confirmation
            - council_models: New council model list
            - chairman_model: New chairman model
            - preset_name: Name of applied preset
            - preset_description: Description of the preset

    Raises:
        HTTPException 404: If preset_id is not found
        HTTPException 500: If preset application fails
    """
    try:
        result = apply_preset(preset_id)
        return {"status": "success", "message": f"Applied preset: {result['preset_name']}", **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to apply preset: {str(e)}"
        )


# ──────────────────────────────────────────────
# Model refresh
# ──────────────────────────────────────────────

@router.post(
    "/models/refresh",
    tags=["config"],
    summary="Refresh Available Models",
    response_description="Updated model list from OpenRouter",
)
async def refresh_models():
    """
    Force refresh of available models from OpenRouter API.

    Fetches the latest model list from OpenRouter, including new models,
    updated pricing, and removed models. This is useful when new models
    are released or pricing changes.

    Returns:
        dict: Object containing:
            - status: "success"
            - models_count: Number of models available
            - last_synced: ISO timestamp of this sync

    Raises:
        HTTPException 500: If refresh fails (e.g., network error)
    """
    main = _get_main_module()
    try:
        main._dynamic_models = await get_available_models()
        main._models_last_synced = datetime.now().isoformat()
        return {
            "status": "success",
            "models_count": len(main._dynamic_models),
            "last_synced": main._models_last_synced,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh models: {str(e)}"
        )


# ──────────────────────────────────────────────
# Usage / cost endpoints
# ──────────────────────────────────────────────

@router.get(
    "/usage",
    tags=["analytics"],
    summary="Get Session Usage Statistics",
    response_description="Current session usage metrics and costs",
)
async def get_usage():
    """
    Get current session usage statistics.

    Returns token usage, cost estimates, and request counts for the
    current session. Use this to monitor API consumption.

    Returns:
        dict: Usage statistics including:
            - total_tokens: Total tokens used
            - prompt_tokens: Input tokens
            - completion_tokens: Output tokens
            - total_cost: Estimated cost in USD
            - request_count: Number of API requests
    """
    return get_session_usage()


@router.post(
    "/usage/reset",
    tags=["analytics"],
    summary="Reset Usage Statistics",
    response_description="Confirmation of usage reset",
)
async def reset_usage():
    """
    Reset session usage statistics.

    Clears all usage counters to start fresh tracking.
    This does not affect billing - only local tracking.

    Returns:
        dict: Confirmation with status "reset"
    """
    reset_session_usage()
    return {"status": "reset"}


# ──────────────────────────────────────────────
# Cache endpoints
# ──────────────────────────────────────────────

@router.get(
    "/cache",
    tags=["analytics"],
    summary="Get Cache Statistics",
    response_description="Cache hit/miss statistics",
)
async def get_cache_status():
    """
    Get response cache statistics.

    Returns cache hit rate, size, and other metrics for the
    response caching system that reduces duplicate API calls.

    Returns:
        dict: Cache statistics including hits, misses, and size
    """
    return get_cache_stats()


@router.post(
    "/cache/clear",
    tags=["analytics"],
    summary="Clear Response Cache",
    response_description="Confirmation of cache clear",
)
async def clear_response_cache():
    """
    Clear the response cache.

    Removes all cached responses, forcing fresh API calls for
    subsequent requests. Use when you need to ensure fresh responses.

    Returns:
        dict: Confirmation with status "cleared"
    """
    clear_cache()
    return {"status": "cleared"}
