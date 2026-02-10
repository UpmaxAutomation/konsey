"""Pytest fixtures for LLM Council tests."""

import pytest
from unittest.mock import AsyncMock, patch
from typing import Dict, Any, List


@pytest.fixture
def mock_openrouter_response():
    """Factory fixture to create mock OpenRouter responses."""
    def _create_response(content: str, thinking: str = None) -> Dict[str, Any]:
        response = {"content": content}
        if thinking:
            response["thinking"] = thinking
        return response
    return _create_response


@pytest.fixture
def mock_query_models_parallel():
    """Mock for openrouter.query_models_parallel that returns controlled responses."""
    async def _mock_parallel(models: List[str], messages) -> Dict[str, Dict[str, Any]]:
        responses = {}
        for i, model in enumerate(models):
            responses[model] = {
                "content": f"Response from {model} for the query."
            }
        return responses
    return _mock_parallel


@pytest.fixture
def mock_query_model():
    """Mock for openrouter.query_model that returns a single response."""
    async def _mock_single(model: str, messages, **kwargs) -> Dict[str, Any]:
        return {"content": f"Response from {model}"}
    return _mock_single


@pytest.fixture
def sample_stage1_results():
    """Sample Stage 1 results for testing."""
    return [
        {"model": "openai/gpt-4", "response": "GPT-4 response about Python."},
        {"model": "anthropic/claude-3", "response": "Claude response about Python."},
        {"model": "google/gemini-pro", "response": "Gemini response about Python."},
    ]


@pytest.fixture
def sample_stage2_results():
    """Sample Stage 2 results with rankings."""
    return [
        {
            "model": "openai/gpt-4",
            "ranking": "Response A is good. Response B is better. Response C is best.\n\nFINAL RANKING:\n1. Response C\n2. Response B\n3. Response A",
            "parsed_ranking": ["Response C", "Response B", "Response A"]
        },
        {
            "model": "anthropic/claude-3",
            "ranking": "Analysis complete.\n\nFINAL RANKING:\n1. Response B\n2. Response C\n3. Response A",
            "parsed_ranking": ["Response B", "Response C", "Response A"]
        },
        {
            "model": "google/gemini-pro",
            "ranking": "All responses were helpful.\n\nFINAL RANKING:\n1. Response C\n2. Response A\n3. Response B",
            "parsed_ranking": ["Response C", "Response A", "Response B"]
        },
    ]


@pytest.fixture
def sample_label_to_model():
    """Sample label to model mapping."""
    return {
        "Response A": "openai/gpt-4",
        "Response B": "anthropic/claude-3",
        "Response C": "google/gemini-pro",
    }


@pytest.fixture
def sample_votes():
    """Sample parsed votes for testing."""
    return [
        {"model": "openai/gpt-4", "choice": "Option A", "confidence": 85, "reasoning": "Best choice because..."},
        {"model": "anthropic/claude-3", "choice": "Option A", "confidence": 90, "reasoning": "Clearly the best..."},
        {"model": "google/gemini-pro", "choice": "Option B", "confidence": 75, "reasoning": "More practical..."},
    ]


@pytest.fixture
def sample_options():
    """Sample voting options."""
    return ["Option A", "Option B", "Option C"]


@pytest.fixture
def mock_council_models():
    """Mock council models list."""
    return ["openai/gpt-4", "anthropic/claude-3", "google/gemini-pro"]


@pytest.fixture
def patch_council_models(mock_council_models):
    """Patch get_council_models to return mock models."""
    with patch("backend.council.get_council_models", return_value=mock_council_models):
        yield mock_council_models


@pytest.fixture
def patch_voting_council_models(mock_council_models):
    """Patch get_council_models in voting module."""
    with patch("backend.voting.get_council_models", return_value=mock_council_models):
        yield mock_council_models
