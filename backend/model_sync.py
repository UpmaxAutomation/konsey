"""Automatically sync available models from OpenRouter API."""

import httpx
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

MODELS_CACHE_FILE = "data/models_cache.json"
CACHE_DURATION_HOURS = 6  # Refresh every 6 hours

# Fallback models if API fails
FALLBACK_MODELS = {
    "openai/gpt-4o": {"name": "GPT-4o", "input_cost": 2.50, "output_cost": 10.00},
    "anthropic/claude-sonnet-4": {"name": "Claude Sonnet 4", "input_cost": 3.00, "output_cost": 15.00},
    "google/gemini-2.5-flash": {"name": "Gemini 2.5 Flash", "input_cost": 0.15, "output_cost": 0.60},
    "x-ai/grok-3": {"name": "Grok 3", "input_cost": 3.00, "output_cost": 15.00},
}

# Filter for top providers we want to show
TOP_PROVIDERS = [
    "openai", "anthropic", "google", "x-ai", "meta-llama",
    "deepseek", "mistralai", "qwen", "cohere", "perplexity",
    "inflection", "nvidia", "together"
]


def _load_cache() -> Optional[Dict[str, Any]]:
    """Load cached models."""
    try:
        if os.path.exists(MODELS_CACHE_FILE):
            with open(MODELS_CACHE_FILE, 'r') as f:
                cache = json.load(f)
                # Check if cache is still valid
                cached_at = datetime.fromisoformat(cache.get("cached_at", "2000-01-01"))
                if datetime.now() - cached_at < timedelta(hours=CACHE_DURATION_HOURS):
                    return cache.get("models", {})
    except Exception as e:
        print(f"Error loading models cache: {e}")
    return None


def _save_cache(models: Dict[str, Any]):
    """Save models to cache."""
    try:
        os.makedirs(os.path.dirname(MODELS_CACHE_FILE), exist_ok=True)
        with open(MODELS_CACHE_FILE, 'w') as f:
            json.dump({
                "cached_at": datetime.now().isoformat(),
                "models": models
            }, f, indent=2)
    except Exception as e:
        print(f"Error saving models cache: {e}")


async def fetch_models_from_openrouter() -> Dict[str, Any]:
    """
    Fetch available models from OpenRouter API.

    Returns:
        Dict mapping model ID to model info (name, pricing)
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://openrouter.ai/api/v1/models")
            response.raise_for_status()
            data = response.json()

        models = {}
        for model in data.get("data", []):
            model_id = model.get("id", "")

            # Filter to top providers
            provider = model_id.split("/")[0] if "/" in model_id else ""
            if provider not in TOP_PROVIDERS:
                continue

            # Get pricing (per 1M tokens)
            pricing = model.get("pricing", {})
            input_cost = float(pricing.get("prompt", 0)) * 1_000_000
            output_cost = float(pricing.get("completion", 0)) * 1_000_000

            # Get display name
            name = model.get("name", model_id.split("/")[-1])

            # Skip if no pricing info (likely deprecated)
            if input_cost == 0 and output_cost == 0:
                # Check if it's explicitly free
                if ":free" not in model_id:
                    continue

            models[model_id] = {
                "name": name,
                "input_cost": round(input_cost, 4),
                "output_cost": round(output_cost, 4),
                "context_length": model.get("context_length", 0),
                "description": model.get("description", "")[:200]
            }

        # Sort by provider and name
        sorted_models = dict(sorted(models.items(), key=lambda x: (
            TOP_PROVIDERS.index(x[0].split("/")[0]) if x[0].split("/")[0] in TOP_PROVIDERS else 99,
            x[1]["name"]
        )))

        return sorted_models

    except Exception as e:
        print(f"Error fetching models from OpenRouter: {e}")
        return {}


async def get_available_models(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get available models, using cache if valid.

    Args:
        force_refresh: Force refresh from API even if cache is valid

    Returns:
        Dict of available models
    """
    # Try cache first
    if not force_refresh:
        cached = _load_cache()
        if cached:
            print(f"Using cached models ({len(cached)} models)")
            return cached

    # Fetch from API
    print("Fetching models from OpenRouter API...")
    models = await fetch_models_from_openrouter()

    if models:
        print(f"Fetched {len(models)} models from OpenRouter")
        _save_cache(models)
        return models

    # Fallback if API fails
    print("Using fallback models")
    return FALLBACK_MODELS


def get_cached_models() -> Dict[str, Any]:
    """
    Get cached models synchronously (for startup).
    Returns fallback if no cache exists.
    """
    cached = _load_cache()
    if cached:
        return cached
    return FALLBACK_MODELS


# Sync wrapper for non-async contexts
def sync_get_models() -> Dict[str, Any]:
    """Synchronous wrapper to get models."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, return cached
            return get_cached_models()
        return loop.run_until_complete(get_available_models())
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(get_available_models())
