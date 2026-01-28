"""Unit tests for model routing heuristics."""

from unittest.mock import patch

from backend.router import route_query


def test_route_query_prefers_cost_when_requested():
    """Cost preference should favor cheaper models when quality isn't preferred."""
    mock_models = {
        "provider/high-cost": {"name": "High Cost"},
        "provider/low-cost": {"name": "Low Cost"},
    }
    mock_capabilities = {
        "provider/high-cost": {
            "strengths": ["code"],
            "tier": 1,
            "cost": "high",
            "context_window": 128000,
        },
        "provider/low-cost": {
            "strengths": ["code"],
            "tier": 2,
            "cost": "low",
            "context_window": 128000,
        },
    }

    with patch("backend.router.AVAILABLE_MODELS", mock_models):
        with patch("backend.router.MODEL_CAPABILITIES", mock_capabilities):
            result = route_query(
                query="Please review this code for bugs.",
                prefer_speed=False,
                prefer_cost=True,
                prefer_quality=False,
                num_recommendations=1,
            )

    assert result["recommended_models"][0]["model_id"] == "provider/low-cost"
    assert "cost" in result["recommended_models"][0]["reason"]


def test_route_query_includes_reason_details():
    """Routing should provide detailed reason text for the top model."""
    mock_models = {
        "provider/reasoning": {"name": "Reasoning Model"},
    }
    mock_capabilities = {
        "provider/reasoning": {
            "strengths": ["reasoning"],
            "tier": 1,
            "cost": "medium",
            "context_window": 128000,
        },
    }

    with patch("backend.router.AVAILABLE_MODELS", mock_models):
        with patch("backend.router.MODEL_CAPABILITIES", mock_capabilities):
            result = route_query(
                query="Prove this theorem step by step.",
                prefer_speed=False,
                prefer_cost=False,
                prefer_quality=True,
                num_recommendations=1,
            )

    reason = result["recommended_models"][0]["reason"]
    assert "reasoning" in reason
