"""Sample data for testing LLM Council."""

from typing import Dict, List, Any
from datetime import datetime
import uuid


# Sample user queries for testing
SAMPLE_USER_QUERIES = [
    "What is the meaning of life?",
    "Explain quantum computing in simple terms.",
    "What are the best practices for Python development?",
    "How does machine learning work?",
    "Compare REST and GraphQL APIs.",
]


def create_sample_conversation(
    num_messages: int = 2,
    conversation_id: str = None,
    title: str = "Test Conversation",
) -> Dict[str, Any]:
    """
    Create a sample conversation for testing.

    Args:
        num_messages: Number of message pairs (user + assistant)
        conversation_id: Optional specific ID
        title: Conversation title

    Returns:
        Conversation dict in storage format
    """
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    messages = []
    for i in range(num_messages):
        # User message
        messages.append({
            "role": "user",
            "content": SAMPLE_USER_QUERIES[i % len(SAMPLE_USER_QUERIES)],
        })

        # Assistant message with all stages
        messages.append({
            "role": "assistant",
            "stage1": [
                {
                    "model": "openai/gpt-4o",
                    "response": f"GPT-4o response to query {i + 1}",
                },
                {
                    "model": "anthropic/claude-3-sonnet",
                    "response": f"Claude response to query {i + 1}",
                },
            ],
            "stage2": [
                {
                    "model": "openai/gpt-4o",
                    "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
                    "parsed_ranking": ["Response A", "Response B"],
                },
                {
                    "model": "anthropic/claude-3-sonnet",
                    "ranking": "FINAL RANKING:\n1. Response B\n2. Response A",
                    "parsed_ranking": ["Response B", "Response A"],
                },
            ],
            "stage3": {
                "model": "google/gemini-2.5-flash",
                "response": f"Chairman synthesis for query {i + 1}",
            },
        })

    return {
        "id": conversation_id,
        "created_at": datetime.now().isoformat(),
        "title": title,
        "messages": messages,
    }


# Pre-built sample conversations
SAMPLE_CONVERSATIONS = [
    create_sample_conversation(num_messages=1, title="Simple Question"),
    create_sample_conversation(num_messages=3, title="Multi-turn Discussion"),
]


def create_sample_stage1_results() -> List[Dict[str, Any]]:
    """Create sample Stage 1 results for testing."""
    return [
        {
            "model": "openai/gpt-4o",
            "response": "The meaning of life is a philosophical question that has been "
                       "debated for centuries. From a scientific perspective...",
        },
        {
            "model": "anthropic/claude-3-sonnet",
            "response": "This profound question touches on existentialism, purpose, "
                       "and human experience. Let me explore several perspectives...",
        },
        {
            "model": "google/gemini-pro",
            "response": "The meaning of life varies by individual and cultural context. "
                       "Key themes include happiness, relationships, and growth...",
        },
    ]


def create_sample_stage2_results() -> tuple:
    """
    Create sample Stage 2 results for testing.

    Returns:
        Tuple of (stage2_results, label_to_model mapping)
    """
    label_to_model = {
        "Response A": "openai/gpt-4o",
        "Response B": "anthropic/claude-3-sonnet",
        "Response C": "google/gemini-pro",
    }

    stage2_results = [
        {
            "model": "openai/gpt-4o",
            "ranking": """Response A provides good scientific grounding.
Response B offers philosophical depth.
Response C is well-balanced but less detailed.

FINAL RANKING:
1. Response B
2. Response A
3. Response C""",
            "parsed_ranking": ["Response B", "Response A", "Response C"],
        },
        {
            "model": "anthropic/claude-3-sonnet",
            "ranking": """Each response has merits.
Response A is analytical, B is thoughtful, C is accessible.

FINAL RANKING:
1. Response A
2. Response C
3. Response B""",
            "parsed_ranking": ["Response A", "Response C", "Response B"],
        },
        {
            "model": "google/gemini-pro",
            "ranking": """Comparing all three responses...

FINAL RANKING:
1. Response B
2. Response C
3. Response A""",
            "parsed_ranking": ["Response B", "Response C", "Response A"],
        },
    ]

    return stage2_results, label_to_model


def create_sample_aggregate_rankings() -> List[Dict[str, Any]]:
    """Create sample aggregate rankings for testing."""
    return [
        {"model": "anthropic/claude-3-sonnet", "average_rank": 1.67, "rankings_count": 3},
        {"model": "openai/gpt-4o", "average_rank": 2.0, "rankings_count": 3},
        {"model": "google/gemini-pro", "average_rank": 2.33, "rankings_count": 3},
    ]
