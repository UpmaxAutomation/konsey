"""Mock OpenRouter API responses for testing."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


# Mock model identifiers used in tests
MOCK_MODELS = [
    "openai/gpt-4o",
    "anthropic/claude-3-sonnet",
    "google/gemini-pro",
]

MOCK_CHAIRMAN = "google/gemini-2.5-flash"


@dataclass
class MockOpenRouterResponse:
    """Mock response structure from OpenRouter API."""

    content: str
    model: str
    input_tokens: int = 100
    output_tokens: int = 200
    thinking: Optional[str] = None

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to OpenRouter API response format."""
        message = {"content": self.content, "role": "assistant"}
        if self.thinking:
            message["reasoning_content"] = self.thinking

        return {
            "id": f"gen-{hash(self.content) % 10000}",
            "model": self.model,
            "choices": [{"message": message, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": self.input_tokens,
                "completion_tokens": self.output_tokens,
                "total_tokens": self.input_tokens + self.output_tokens,
            },
        }

    def to_internal_response(self) -> Dict[str, Any]:
        """Convert to internal response format used by openrouter.py."""
        result = {
            "content": self.content,
            "usage": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cost": 0.001,  # Mock cost
            },
        }
        if self.thinking:
            result["thinking"] = self.thinking
        return result


def create_mock_response(
    content: str,
    model: str = "openai/gpt-4o",
    input_tokens: int = 100,
    output_tokens: int = 200,
    thinking: Optional[str] = None,
) -> MockOpenRouterResponse:
    """Create a mock OpenRouter response."""
    return MockOpenRouterResponse(
        content=content,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking=thinking,
    )


def create_mock_stage1_responses(
    models: List[str] = None,
    query: str = "What is the meaning of life?",
) -> Dict[str, Dict[str, Any]]:
    """
    Create mock Stage 1 responses for multiple models.

    Returns dict mapping model -> internal response format.
    """
    if models is None:
        models = MOCK_MODELS

    responses = {}
    for i, model in enumerate(models):
        provider = model.split("/")[0].upper()
        responses[model] = {
            "content": f"Response from {provider}: The meaning of life is perspective {i + 1}. "
                      f"This is a thoughtful answer that considers multiple angles.",
            "usage": {
                "input_tokens": 100 + i * 10,
                "output_tokens": 200 + i * 20,
                "cost": 0.001 + i * 0.0001,
            },
        }

    return responses


def create_mock_stage2_responses(
    models: List[str] = None,
    num_responses: int = 3,
) -> Dict[str, Dict[str, Any]]:
    """
    Create mock Stage 2 ranking responses.

    Returns dict mapping model -> internal response format with ranking text.
    """
    if models is None:
        models = MOCK_MODELS

    labels = [chr(65 + i) for i in range(num_responses)]  # A, B, C, ...

    responses = {}
    for i, model in enumerate(models):
        # Create different ranking orderings for variety
        ranking_order = labels.copy()
        # Rotate the ranking for each model to simulate disagreement
        ranking_order = ranking_order[i:] + ranking_order[:i]

        ranking_text = f"""
Evaluating the responses:

Response A provides a philosophical perspective on the meaning of life.
It offers good depth but could be more practical.

Response B takes a scientific approach, discussing evolution and purpose.
Very well-researched but somewhat dry.

Response C focuses on personal fulfillment and relationships.
Engaging and relatable.

FINAL RANKING:
1. Response {ranking_order[0]}
2. Response {ranking_order[1]}
3. Response {ranking_order[2]}
"""

        responses[model] = {
            "content": ranking_text.strip(),
            "usage": {
                "input_tokens": 500 + i * 20,
                "output_tokens": 300 + i * 15,
                "cost": 0.002 + i * 0.0002,
            },
        }

    return responses


def create_mock_stage3_response(
    chairman: str = MOCK_CHAIRMAN,
) -> Dict[str, Any]:
    """Create mock Stage 3 chairman synthesis response."""
    return {
        "content": """Based on the council's deliberation, the meaning of life encompasses
several interconnected aspects:

1. **Personal Growth**: Continuous self-improvement and learning
2. **Relationships**: Deep connections with others
3. **Purpose**: Contributing to something larger than oneself
4. **Experience**: Embracing both joy and challenges

The council reached consensus that meaning is not a single answer but
a personal journey of discovery.""",
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 400,
            "cost": 0.003,
        },
    }


# Pre-built mock responses for common test scenarios
MOCK_SIMPLE_RESPONSE = create_mock_response(
    content="This is a simple test response.",
    model="openai/gpt-4o",
)

MOCK_REASONING_RESPONSE = create_mock_response(
    content="After careful analysis, the answer is 42.",
    model="deepseek/deepseek-r1",
    thinking="Let me think step by step... First, consider the question... "
             "The key insight is... Therefore, the answer must be 42.",
)

MOCK_ERROR_RESPONSE = None  # Represents a failed API call
