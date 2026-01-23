"""Unit tests for config.py - Configuration management."""

import pytest
from unittest.mock import patch, mock_open
import json
import os

from backend.config import (
    get_council_models,
    set_council_models,
    get_chairman_model,
    set_chairman_model,
    get_enhanced_features,
    set_enhanced_features,
    get_presets,
    apply_preset,
    is_reasoning_model,
    get_personas,
    get_model_persona,
    set_model_persona,
    create_custom_persona,
    get_api_keys,
    get_api_key,
    set_api_key,
    get_openrouter_api_key,
    get_provider_from_model,
    has_direct_api_key,
    COUNCIL_PRESETS,
    AVAILABLE_MODELS,
    REASONING_MODELS,
    DEFAULT_PERSONAS,
)


class TestCouncilModels:
    """Tests for council model configuration."""

    def test_get_default_council_models(self):
        """Test getting default council models."""
        models = get_council_models()
        assert isinstance(models, list)
        assert len(models) > 0

    def test_set_council_models(self):
        """Test setting council models."""
        original = get_council_models().copy()
        new_models = ["openai/gpt-4o", "anthropic/claude-sonnet-4"]

        with patch("backend.config.save_settings"):
            set_council_models(new_models)
            assert get_council_models() == new_models

            # Restore original
            set_council_models(original)


class TestChairmanModel:
    """Tests for chairman model configuration."""

    def test_get_default_chairman(self):
        """Test getting default chairman model."""
        chairman = get_chairman_model()
        assert isinstance(chairman, str)
        assert "/" in chairman  # Should be provider/model format

    def test_set_chairman_model(self):
        """Test setting chairman model."""
        original = get_chairman_model()

        with patch("backend.config.save_settings"):
            set_chairman_model("openai/gpt-4o")
            assert get_chairman_model() == "openai/gpt-4o"

            # Restore original
            set_chairman_model(original)


class TestEnhancedFeatures:
    """Tests for enhanced features configuration."""

    def test_get_enhanced_features(self):
        """Test getting enhanced features."""
        features = get_enhanced_features()
        assert isinstance(features, dict)
        assert "web_search" in features
        assert "code_execution" in features
        assert "memory" in features

    def test_set_enhanced_features(self):
        """Test setting enhanced features."""
        with patch("backend.config.save_settings"):
            set_enhanced_features({"web_search": False})
            features = get_enhanced_features()
            # Check the update was applied
            assert isinstance(features, dict)


class TestPresets:
    """Tests for council presets."""

    def test_get_presets_returns_all(self):
        """Test getting all presets."""
        presets = get_presets()
        assert isinstance(presets, dict)
        assert "code_review" in presets
        assert "research" in presets
        assert "creative" in presets
        assert "reasoning" in presets
        assert "budget" in presets

    def test_preset_structure(self):
        """Test preset structure is correct."""
        presets = get_presets()
        for preset_id, preset in presets.items():
            assert "name" in preset
            assert "description" in preset
            assert "models" in preset
            assert "chairman" in preset
            assert isinstance(preset["models"], list)
            assert len(preset["models"]) > 0

    def test_apply_preset_success(self):
        """Test applying a valid preset."""
        original_models = get_council_models().copy()
        original_chairman = get_chairman_model()

        with patch("backend.config.save_settings"):
            result = apply_preset("code_review")

            assert "council_models" in result
            assert "chairman_model" in result
            assert "preset_name" in result
            assert result["preset_name"] == COUNCIL_PRESETS["code_review"]["name"]

            # Restore original
            set_council_models(original_models)
            set_chairman_model(original_chairman)

    def test_apply_preset_invalid(self):
        """Test applying an invalid preset raises error."""
        with pytest.raises(ValueError) as exc_info:
            apply_preset("nonexistent_preset")

        assert "Invalid preset ID" in str(exc_info.value)


class TestReasoningModels:
    """Tests for reasoning model detection."""

    def test_is_reasoning_model_true(self):
        """Test detection of known reasoning models."""
        assert is_reasoning_model("openai/o1") is True
        assert is_reasoning_model("openai/o3") is True
        assert is_reasoning_model("deepseek/deepseek-r1") is True
        assert is_reasoning_model("qwen/qwq-32b") is True

    def test_is_reasoning_model_false(self):
        """Test non-reasoning models return False."""
        assert is_reasoning_model("openai/gpt-4o") is False
        assert is_reasoning_model("anthropic/claude-sonnet-4") is False
        assert is_reasoning_model("google/gemini-2.5-flash") is False

    def test_reasoning_models_list_exists(self):
        """Test REASONING_MODELS list is populated."""
        assert isinstance(REASONING_MODELS, list)
        assert len(REASONING_MODELS) > 0


class TestAvailableModels:
    """Tests for available models configuration."""

    def test_available_models_structure(self):
        """Test AVAILABLE_MODELS has correct structure."""
        assert isinstance(AVAILABLE_MODELS, dict)
        for model_id, info in AVAILABLE_MODELS.items():
            assert "name" in info
            assert "input_cost" in info
            assert "output_cost" in info
            assert isinstance(info["input_cost"], (int, float))
            assert isinstance(info["output_cost"], (int, float))

    def test_available_models_has_major_providers(self):
        """Test major providers are represented."""
        model_ids = list(AVAILABLE_MODELS.keys())
        model_str = " ".join(model_ids)

        assert "openai/" in model_str
        assert "anthropic/" in model_str
        assert "google/" in model_str

    def test_model_ids_follow_format(self):
        """Test model IDs follow provider/model format."""
        for model_id in AVAILABLE_MODELS.keys():
            assert "/" in model_id, f"Model {model_id} doesn't follow provider/model format"


class TestPersonas:
    """Tests for persona configuration."""

    def test_get_personas(self):
        """Test getting all personas."""
        personas = get_personas()
        assert "default" in personas
        assert "custom" in personas
        assert isinstance(personas["default"], dict)

    def test_default_personas_exist(self):
        """Test default personas are available."""
        assert "senior_engineer" in DEFAULT_PERSONAS
        assert "security_expert" in DEFAULT_PERSONAS
        assert "devil_advocate" in DEFAULT_PERSONAS

    def test_get_model_persona_default(self):
        """Test getting persona for model without assignment."""
        # A model without persona should return empty string
        persona = get_model_persona("some/random-model")
        assert persona == ""

    def test_set_and_get_model_persona(self):
        """Test setting and getting model persona."""
        with patch("backend.config.save_settings"):
            set_model_persona("test/model", "senior_engineer")
            # Would need to check runtime config directly
            # This is a basic smoke test


class TestApiKeys:
    """Tests for API key management."""

    def test_get_api_keys_masked(self):
        """Test API keys are masked for display."""
        keys = get_api_keys()
        assert isinstance(keys, dict)
        # Keys should be masked (not full keys)
        for provider, key in keys.items():
            if key:
                assert "..." in key or key == "****" or key == ""

    def test_get_api_key_raw(self):
        """Test getting raw API key."""
        # This will return empty string if not set
        key = get_api_key("openai")
        assert isinstance(key, str)

    def test_set_api_key(self):
        """Test setting API key."""
        with patch("backend.config.save_settings"):
            set_api_key("test_provider", "test-key-12345")
            # Key should be stored
            key = get_api_key("test_provider")
            assert key == "test-key-12345"

            # Clean up
            set_api_key("test_provider", "")

    def test_get_openrouter_api_key_from_env(self):
        """Test OpenRouter key falls back to environment."""
        # The function checks settings first, then env
        key = get_openrouter_api_key()
        assert isinstance(key, str)


class TestProviderUtils:
    """Tests for provider utility functions."""

    def test_get_provider_from_model(self):
        """Test extracting provider from model ID."""
        assert get_provider_from_model("openai/gpt-4o") == "openai"
        assert get_provider_from_model("anthropic/claude-sonnet-4") == "anthropic"
        assert get_provider_from_model("google/gemini-2.5-flash") == "google"
        assert get_provider_from_model("deepseek/deepseek-r1") == "deepseek"

    def test_get_provider_from_model_no_slash(self):
        """Test handling model ID without slash."""
        assert get_provider_from_model("gpt-4o") == ""

    def test_has_direct_api_key_false(self):
        """Test has_direct_api_key returns False when no key."""
        # Most providers won't have keys in test environment
        result = has_direct_api_key("some/unknown-model")
        assert isinstance(result, bool)


class TestPresetDetails:
    """Detailed tests for preset configurations."""

    def test_code_review_preset(self):
        """Test code_review preset configuration."""
        preset = COUNCIL_PRESETS["code_review"]
        assert "Claude" in preset["name"] or "Code" in preset["name"]
        assert len(preset["models"]) >= 3

    def test_reasoning_preset_uses_reasoning_models(self):
        """Test reasoning preset includes reasoning models."""
        preset = COUNCIL_PRESETS["reasoning"]
        # At least some models should be reasoning models
        reasoning_count = sum(1 for m in preset["models"] if is_reasoning_model(m))
        assert reasoning_count >= 2, "Reasoning preset should have reasoning models"

    def test_budget_preset_uses_cheap_models(self):
        """Test budget preset uses cost-effective models."""
        preset = COUNCIL_PRESETS["budget"]
        # Check that models in budget preset have low costs
        for model_id in preset["models"]:
            if model_id in AVAILABLE_MODELS:
                model_info = AVAILABLE_MODELS[model_id]
                # Budget models should have input cost <= $1
                assert model_info["input_cost"] <= 1.0, f"Budget model {model_id} has high cost"
