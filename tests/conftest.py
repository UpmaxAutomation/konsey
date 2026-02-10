"""Pytest configuration and fixtures for LLM Council tests."""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-minimum-32-characters"
os.environ["OPENROUTER_API_KEY"] = "test-openrouter-key"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for API calls."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_instance


@pytest.fixture
def mock_openrouter_key():
    """Mock OpenRouter API key."""
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
        yield


@pytest.fixture
def mock_openai_key():
    """Mock OpenAI API key."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-openai-key"}):
        yield


@pytest.fixture
def mock_anthropic_key():
    """Mock Anthropic API key."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-anthropic-key"}):
        yield


@pytest.fixture
def mock_council_models():
    """Mock council model configuration."""
    models = ["openai/gpt-4o", "anthropic/claude-3-sonnet", "google/gemini-pro"]
    with patch("backend.config.get_council_models", return_value=models):
        yield models


@pytest.fixture
def mock_chairman_model():
    """Mock chairman model configuration."""
    chairman = "google/gemini-2.5-flash"
    with patch("backend.config.get_chairman_model", return_value=chairman):
        yield chairman


@pytest.fixture
def mock_storage():
    """Mock storage adapter for conversation operations."""
    with patch("backend.main.storage") as mock:
        mock.list_conversations.return_value = []
        mock.create_conversation.return_value = {
            "id": "test-conv-123",
            "created_at": "2025-01-01T00:00:00",
            "title": "New Conversation",
            "messages": [],
        }
        mock.get_conversation.return_value = {
            "id": "test-conv-123",
            "created_at": "2025-01-01T00:00:00",
            "title": "Test Conversation",
            "messages": [],
        }
        mock.add_message.return_value = True
        mock.update_conversation.return_value = True
        mock.delete_conversation.return_value = True
        yield mock


@pytest.fixture
def sample_stage1_results():
    """Sample Stage 1 results for testing."""
    return [
        {
            "model": "openai/gpt-4o",
            "response": "The meaning of life is a philosophical question...",
        },
        {
            "model": "anthropic/claude-3-sonnet",
            "response": "This profound question touches on existentialism...",
        },
        {
            "model": "google/gemini-pro",
            "response": "The meaning of life varies by individual...",
        },
    ]


@pytest.fixture
def sample_stage2_results():
    """Sample Stage 2 results for testing."""
    return [
        {
            "model": "openai/gpt-4o",
            "ranking": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C",
            "parsed_ranking": ["Response B", "Response A", "Response C"],
        },
        {
            "model": "anthropic/claude-3-sonnet",
            "ranking": "FINAL RANKING:\n1. Response A\n2. Response C\n3. Response B",
            "parsed_ranking": ["Response A", "Response C", "Response B"],
        },
    ]


@pytest.fixture
def sample_label_to_model():
    """Sample label to model mapping for testing."""
    return {
        "Response A": "openai/gpt-4o",
        "Response B": "anthropic/claude-3-sonnet",
        "Response C": "google/gemini-pro",
    }


@pytest.fixture
def mock_query_model():
    """Mock the query_model function."""
    async def _mock_query(model, messages, **kwargs):
        return {
            "content": f"Response from {model}",
            "usage": {"input_tokens": 100, "output_tokens": 200, "cost": 0.001},
        }

    with patch("backend.openrouter.query_model", side_effect=_mock_query):
        yield _mock_query


@pytest.fixture
def mock_query_models_parallel():
    """Mock the query_models_parallel function."""
    async def _mock_parallel(models, messages):
        return {
            model: {
                "content": f"Response from {model}",
                "usage": {"input_tokens": 100, "output_tokens": 200, "cost": 0.001},
            }
            for model in models
        }

    with patch("backend.openrouter.query_models_parallel", side_effect=_mock_parallel):
        yield _mock_parallel


@pytest.fixture
def test_client():
    """Create FastAPI test client with mocked dependencies."""
    with patch("backend.main.init_db", new_callable=AsyncMock):
        with patch("backend.main.get_available_models", new_callable=AsyncMock, return_value={}):
            from fastapi.testclient import TestClient
            from backend.main import app
            with TestClient(app) as client:
                yield client
