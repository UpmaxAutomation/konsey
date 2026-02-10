"""Test script to verify follow-up conversation context works."""

import asyncio
from .storage import (
    create_conversation,
    add_user_message,
    add_assistant_message,
    get_conversation_context
)


def test_conversation_context():
    """Test that conversation context extraction works correctly."""
    # Create a test conversation
    conv_id = "test-conversation-123"
    conversation = create_conversation(conv_id)

    print(f"Created conversation: {conv_id}")

    # Add first exchange
    add_user_message(conv_id, "What is the capital of France?")
    add_assistant_message(
        conv_id,
        stage1=[{"model": "model1", "response": "Paris is the capital."}],
        stage2=[],
        stage3={"model": "chairman", "response": "The capital of France is Paris."}
    )
    print("Added first exchange")

    # Add second exchange
    add_user_message(conv_id, "What about Germany?")
    add_assistant_message(
        conv_id,
        stage1=[{"model": "model1", "response": "Berlin is the capital."}],
        stage2=[],
        stage3={"model": "chairman", "response": "The capital of Germany is Berlin."}
    )
    print("Added second exchange")

    # Add third exchange
    add_user_message(conv_id, "And Italy?")
    add_assistant_message(
        conv_id,
        stage1=[{"model": "model1", "response": "Rome is the capital."}],
        stage2=[],
        stage3={"model": "chairman", "response": "The capital of Italy is Rome."}
    )
    print("Added third exchange")

    # Test context extraction with limit=2
    context = get_conversation_context(conv_id, limit=2)

    print("\n" + "="*60)
    print("CONVERSATION CONTEXT (limit=2):")
    print("="*60)
    print(context)
    print("="*60)

    # Verify context contains expected elements
    assert context is not None, "Context should not be None"
    assert "Germany" in context, "Should include Germany exchange"
    assert "Italy" in context, "Should include Italy exchange"
    assert "France" not in context, "Should NOT include France (outside limit)"

    print("\n✅ All tests passed!")

    # Test with limit=3 (all exchanges)
    context_all = get_conversation_context(conv_id, limit=3)
    print("\n" + "="*60)
    print("CONVERSATION CONTEXT (limit=3):")
    print("="*60)
    print(context_all)
    print("="*60)

    assert "France" in context_all, "Should include all 3 exchanges"
    assert "Germany" in context_all
    assert "Italy" in context_all

    print("\n✅ Context with limit=3 works correctly!")

    # Test with no history
    new_conv_id = "new-conversation-456"
    create_conversation(new_conv_id)
    context_empty = get_conversation_context(new_conv_id, limit=3)

    assert context_empty is None, "Empty conversation should return None"
    print("\n✅ Empty conversation returns None as expected!")


if __name__ == "__main__":
    test_conversation_context()
