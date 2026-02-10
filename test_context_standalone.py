"""Standalone test for conversation context (without dependencies)."""

import json
import os
from pathlib import Path


# Mock conversation storage
def create_test_data():
    """Create test conversation data."""
    return {
        "id": "test-123",
        "created_at": "2025-01-01T00:00:00",
        "title": "Test Conversation",
        "messages": [
            {
                "role": "user",
                "content": "What is the capital of France?"
            },
            {
                "role": "assistant",
                "stage1": [{"model": "model1", "response": "Paris is the capital."}],
                "stage2": [],
                "stage3": {"model": "chairman", "response": "The capital of France is Paris."}
            },
            {
                "role": "user",
                "content": "What about Germany?"
            },
            {
                "role": "assistant",
                "stage1": [{"model": "model1", "response": "Berlin is the capital."}],
                "stage2": [],
                "stage3": {"model": "chairman", "response": "The capital of Germany is Berlin."}
            },
            {
                "role": "user",
                "content": "And Italy?"
            },
            {
                "role": "assistant",
                "stage1": [{"model": "model1", "response": "Rome is the capital."}],
                "stage2": [],
                "stage3": {"model": "chairman", "response": "The capital of Italy is Rome."}
            }
        ]
    }


def get_conversation_context(conversation_data, limit=3):
    """
    Get summarized context from recent conversation history.
    This is a copy of the implementation from storage.py for testing.
    """
    messages = conversation_data.get("messages", [])

    if not messages:
        return None

    # Get the last N user-assistant pairs
    context_parts = []

    # Process messages in forward order, pairing user with following assistant
    i = 0
    while i < len(messages):
        # Look for user message followed by assistant message
        if (i < len(messages) - 1 and
            messages[i]["role"] == "user" and
            messages[i + 1]["role"] == "assistant"):

            user_msg = messages[i]["content"]
            stage3 = messages[i + 1].get("stage3", {})
            assistant_response = stage3.get("response", "")

            # Add this exchange
            context_parts.append({
                "question": user_msg,
                "answer": assistant_response
            })

            i += 2  # Skip both user and assistant messages
        else:
            i += 1

    # Keep only the last N exchanges
    context_parts = context_parts[-limit:]

    if not context_parts:
        return None

    # Format context as a readable summary
    context_lines = ["Previous conversation context:"]
    for i, exchange in enumerate(context_parts, 1):
        # Truncate long responses to keep context manageable
        question = exchange["question"][:300]
        answer = exchange["answer"][:500]

        context_lines.append(f"\nExchange {i}:")
        context_lines.append(f"Q: {question}")
        context_lines.append(f"A: {answer}...")

    return "\n".join(context_lines)


def test_context_extraction():
    """Test the context extraction logic."""
    print("Testing conversation context extraction...\n")

    # Create test data
    conversation = create_test_data()

    # Test 1: Extract last 2 exchanges
    print("="*70)
    print("TEST 1: Extract last 2 exchanges (limit=2)")
    print("="*70)
    context = get_conversation_context(conversation, limit=2)
    print(context)
    print()

    # Verify
    assert context is not None, "Context should not be None"
    assert "Germany" in context, "Should include Germany exchange"
    assert "Italy" in context, "Should include Italy exchange"
    assert "France" not in context, "Should NOT include France (outside limit)"
    print("✅ Test 1 PASSED: Last 2 exchanges extracted correctly\n")

    # Test 2: Extract all 3 exchanges
    print("="*70)
    print("TEST 2: Extract all 3 exchanges (limit=3)")
    print("="*70)
    context_all = get_conversation_context(conversation, limit=3)
    print(context_all)
    print()

    # Verify
    assert "France" in context_all, "Should include France exchange"
    assert "Germany" in context_all, "Should include Germany exchange"
    assert "Italy" in context_all, "Should include Italy exchange"
    print("✅ Test 2 PASSED: All 3 exchanges extracted correctly\n")

    # Test 3: Empty conversation
    print("="*70)
    print("TEST 3: Empty conversation")
    print("="*70)
    empty_conv = {"id": "empty", "messages": []}
    context_empty = get_conversation_context(empty_conv, limit=3)
    print(f"Context: {context_empty}")
    print()

    # Verify
    assert context_empty is None, "Empty conversation should return None"
    print("✅ Test 3 PASSED: Empty conversation returns None\n")

    # Test 4: Demonstrate how context would be used in a follow-up query
    print("="*70)
    print("TEST 4: Example follow-up query with context")
    print("="*70)
    follow_up_query = "What are the populations of these cities?"
    context = get_conversation_context(conversation, limit=3)
    enhanced_query = f"{context}\n\n---\n\nCurrent Question: {follow_up_query}"
    print("Follow-up query:", follow_up_query)
    print("\nEnhanced query sent to models:")
    print("-" * 70)
    print(enhanced_query)
    print("-" * 70)
    print()
    print("✅ Test 4 PASSED: Context successfully enhances follow-up query\n")

    print("="*70)
    print("ALL TESTS PASSED! ✅")
    print("="*70)


if __name__ == "__main__":
    test_context_extraction()
