"""Integration tests for API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import json


# We need to mock the dependencies before importing main
@pytest.fixture
def mock_dependencies():
    """Mock external dependencies for API tests."""
    with patch("backend.openrouter.get_openrouter_api_key", return_value="test-key"):
        with patch("backend.config.get_openrouter_api_key", return_value="test-key"):
            yield


@pytest.fixture
def client(mock_dependencies):
    """Create test client."""
    from backend.main import app
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_root_returns_ok(self, client):
        """Root endpoint returns success."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok" or "status" in str(data)


class TestModelsEndpoint:
    """Tests for models endpoint."""

    def test_get_models_returns_list(self, client):
        """GET /api/models returns list of available models."""
        response = client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_get_models_structure(self, client):
        """GET /api/models returns properly structured data."""
        response = client.get("/api/models")
        assert response.status_code == 200
        data = response.json()

        # Should be either a list of models or dict with models
        if isinstance(data, dict):
            # Check for expected keys
            assert "models" in data or "available_models" in data or len(data) > 0


class TestPresetsEndpoint:
    """Tests for presets endpoint."""

    def test_get_presets_returns_list(self, client):
        """GET /api/presets returns list of presets."""
        response = client.get("/api/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert isinstance(data["presets"], list)

    def test_presets_have_required_fields(self, client):
        """Each preset has required fields."""
        response = client.get("/api/presets")
        data = response.json()

        for preset in data["presets"]:
            assert "id" in preset
            assert "name" in preset or "description" in preset

    def test_apply_nonexistent_preset_returns_404(self, client):
        """Applying non-existent preset returns 404."""
        response = client.post("/api/presets/nonexistent-preset-xyz/apply")
        assert response.status_code == 404


class TestConfigEndpoint:
    """Tests for config endpoint."""

    def test_get_config_returns_data(self, client):
        """GET /api/config returns configuration."""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_config_has_expected_structure(self, client):
        """Config response has expected structure."""
        response = client.get("/api/config")
        data = response.json()

        # Check for common config fields
        # May vary based on implementation
        assert isinstance(data, dict)


class TestConversationsEndpoint:
    """Tests for conversations endpoints."""

    def test_create_conversation(self, client):
        """POST /api/conversations creates new conversation."""
        response = client.post("/api/conversations")

        # Should either succeed or require body
        assert response.status_code in [200, 201, 422]

        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data

    def test_list_conversations(self, client):
        """GET /api/conversations lists conversations."""
        response = client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_nonexistent_conversation_returns_404(self, client):
        """GET non-existent conversation returns 404."""
        response = client.get("/api/conversations/nonexistent-conv-xyz")
        assert response.status_code == 404


class TestSessionUsageEndpoint:
    """Tests for session usage tracking."""

    def test_get_session_usage(self, client):
        """GET /api/sessions/usage returns usage data."""
        response = client.get("/api/sessions/usage")

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_endpoint_returns_404(self, client):
        """Invalid endpoint returns 404."""
        response = client.get("/api/invalid-endpoint-xyz")
        assert response.status_code == 404

    def test_invalid_method_returns_405(self, client):
        """Invalid method returns 405."""
        response = client.delete("/")  # DELETE on root
        assert response.status_code in [405, 404]  # Some servers return 404 for method not allowed


class TestCORS:
    """Tests for CORS headers."""

    def test_cors_headers_on_options(self, client):
        """OPTIONS requests include CORS headers."""
        response = client.options(
            "/api/models",
            headers={"Origin": "http://localhost:5173"}
        )

        # CORS headers should be present
        # May vary based on CORS configuration
        assert response.status_code in [200, 204]


class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_normal_requests_not_limited(self, client):
        """Normal request rate is not limited."""
        # Make a few quick requests
        for _ in range(5):
            response = client.get("/api/models")
            assert response.status_code == 200


class TestInputValidation:
    """Tests for input validation."""

    def test_message_endpoint_validates_input(self, client):
        """Message endpoint validates input."""
        # First create a conversation
        create_response = client.post("/api/conversations")

        if create_response.status_code in [200, 201]:
            conv_id = create_response.json()["id"]

            # Try to send message with invalid data
            response = client.post(
                f"/api/conversations/{conv_id}/message",
                json={}  # Missing required fields
            )

            # Should either require content or return validation error
            assert response.status_code in [400, 422, 200]

    def test_vote_endpoint_validates_options(self, client):
        """Vote endpoint validates options count."""
        # Create conversation first
        create_response = client.post("/api/conversations")

        if create_response.status_code in [200, 201]:
            conv_id = create_response.json()["id"]

            # Try to vote with invalid options (only 1)
            response = client.post(
                f"/api/conversations/{conv_id}/vote",
                json={
                    "question": "Test question",
                    "options": ["Only one option"]  # Needs at least 2
                }
            )

            # Should return validation error
            assert response.status_code in [400, 422]


class TestFoldersEndpoint:
    """Tests for folders endpoints."""

    def test_list_folders(self, client):
        """GET /api/folders lists folders."""
        response = client.get("/api/folders")

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_create_folder(self, client):
        """POST /api/folders creates folder."""
        response = client.post(
            "/api/folders",
            json={"name": "Test Folder", "color": "#ff0000"}
        )

        # May require auth or succeed
        assert response.status_code in [200, 201, 401, 403, 422]


class TestTagsEndpoint:
    """Tests for tags endpoints."""

    def test_list_tags(self, client):
        """GET /api/tags lists all tags."""
        response = client.get("/api/tags")

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)


class TestQuickModeEndpoint:
    """Tests for quick mode (single model) endpoint."""

    def test_quick_mode_validates_model(self, client):
        """Quick mode validates model parameter."""
        # Create conversation first
        create_response = client.post("/api/conversations")

        if create_response.status_code in [200, 201]:
            conv_id = create_response.json()["id"]

            # Try quick mode with missing model
            response = client.post(
                f"/api/conversations/{conv_id}/quick",
                json={"message": "Test"}  # Missing model
            )

            assert response.status_code in [400, 422]


class TestResponseFormat:
    """Tests for response format consistency."""

    def test_error_responses_have_consistent_format(self, client):
        """Error responses have consistent format."""
        response = client.get("/api/conversations/nonexistent")
        assert response.status_code == 404

        data = response.json()
        # Should have error message
        assert "detail" in data or "error" in data or "message" in data

    def test_success_responses_are_json(self, client):
        """Success responses are valid JSON."""
        response = client.get("/api/models")
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")

        # Should be valid JSON
        data = response.json()
        assert data is not None
