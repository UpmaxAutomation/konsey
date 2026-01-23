"""Integration tests for conversation API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def client():
    """Create test client with mocked database."""
    with patch("backend.main.init_db", new_callable=AsyncMock):
        with patch("backend.main.get_available_models", new_callable=AsyncMock, return_value={}):
            from backend.main import app
            with TestClient(app) as test_client:
                yield test_client


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
        mock.delete_conversation.return_value = True
        yield mock


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_root_returns_ok(self, client):
        """Test root endpoint returns health status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "LLM Council API"


class TestConversationEndpoints:
    """Tests for conversation CRUD endpoints."""

    def test_list_conversations_empty(self, client, mock_storage):
        """Test listing conversations when empty."""
        mock_storage.list_conversations.return_value = []

        response = client.get("/api/conversations")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_conversations_with_data(self, client, mock_storage):
        """Test listing conversations with data."""
        mock_storage.list_conversations.return_value = [
            {
                "id": "conv-1",
                "created_at": "2025-01-01T00:00:00",
                "title": "First Conversation",
                "message_count": 2,
            },
            {
                "id": "conv-2",
                "created_at": "2025-01-02T00:00:00",
                "title": "Second Conversation",
                "message_count": 4,
            },
        ]

        response = client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "conv-1"

    def test_create_conversation(self, client, mock_storage):
        """Test creating a new conversation."""
        response = client.post("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "New Conversation"
        assert data["messages"] == []

    def test_get_conversation(self, client, mock_storage):
        """Test getting a specific conversation."""
        response = client.get("/api/conversations/test-conv-123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-conv-123"

    def test_get_conversation_not_found(self, client, mock_storage):
        """Test getting non-existent conversation."""
        mock_storage.get_conversation.return_value = None

        response = client.get("/api/conversations/nonexistent")
        assert response.status_code == 404

    def test_delete_conversation(self, client, mock_storage):
        """Test deleting a conversation."""
        response = client.delete("/api/conversations/test-conv-123")
        assert response.status_code == 200


class TestConfigEndpoints:
    """Tests for configuration endpoints."""

    def test_get_config(self, client):
        """Test getting current configuration."""
        with patch("backend.main.get_council_models", return_value=["model-a", "model-b"]):
            with patch("backend.main.get_chairman_model", return_value="model-c"):
                with patch("backend.main.get_all_models", return_value={"model-a": {}, "model-b": {}, "model-c": {}}):
                    response = client.get("/api/config")

        assert response.status_code == 200
        data = response.json()
        assert "council_models" in data
        assert "chairman_model" in data

    def test_update_config(self, client):
        """Test updating configuration."""
        with patch("backend.main.set_council_models") as mock_set_council:
            with patch("backend.main.set_chairman_model") as mock_set_chairman:
                with patch("backend.main.get_council_models", return_value=["new-model"]):
                    with patch("backend.main.get_chairman_model", return_value="new-chairman"):
                        with patch("backend.main.get_all_models", return_value={}):
                            response = client.post(
                                "/api/config",
                                json={
                                    "council_models": ["new-model"],
                                    "chairman_model": "new-chairman"
                                }
                            )

        assert response.status_code == 200


class TestPresetEndpoints:
    """Tests for preset configuration endpoints."""

    def test_list_presets(self, client):
        """Test listing available presets."""
        mock_presets = {
            "code_review": {
                "name": "Code Review",
                "description": "Expert code reviewers",
                "models": ["model-a"],
                "chairman": "model-b",
            }
        }

        with patch("backend.main.get_presets", return_value=mock_presets):
            response = client.get("/api/presets")

        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert len(data["presets"]) == 1
        assert data["presets"][0]["id"] == "code_review"

    def test_apply_preset(self, client):
        """Test applying a preset."""
        with patch("backend.main.apply_preset") as mock_apply:
            mock_apply.return_value = {
                "council_models": ["model-a"],
                "chairman_model": "model-b",
            }
            with patch("backend.main.get_presets", return_value={
                "code_review": {"name": "Code Review", "description": "Test"}
            }):
                response = client.post("/api/presets/code_review/apply")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_apply_nonexistent_preset(self, client):
        """Test applying non-existent preset."""
        with patch("backend.main.get_presets", return_value={}):
            response = client.post("/api/presets/nonexistent/apply")

        assert response.status_code == 404


class TestUsageEndpoints:
    """Tests for usage tracking endpoints."""

    def test_get_session_usage(self, client):
        """Test getting session usage statistics."""
        mock_usage = {
            "total_input_tokens": 1000,
            "total_output_tokens": 500,
            "total_cost": 0.05,
            "requests": [],
        }

        with patch("backend.main.get_session_usage", return_value=mock_usage):
            response = client.get("/api/usage")

        assert response.status_code == 200
        data = response.json()
        assert data["total_input_tokens"] == 1000
        assert data["total_cost"] == 0.05

    def test_reset_session_usage(self, client):
        """Test resetting session usage."""
        with patch("backend.main.reset_session_usage") as mock_reset:
            response = client.post("/api/usage/reset")

        assert response.status_code == 200
        mock_reset.assert_called_once()
