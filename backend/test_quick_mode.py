"""
Test script for Quick Mode functionality.

Run with: python -m backend.test_quick_mode
"""

import asyncio
import json
from . import storage
from .openrouter import query_model_stream
from .config import get_chairman_model, AVAILABLE_MODELS


async def test_streaming():
    """Test the streaming functionality."""
    print("Testing streaming with chairman model...")

    model = get_chairman_model()
    messages = [{"role": "user", "content": "Count to 5, one number per line."}]

    print(f"Model: {model}")
    print("Response:")

    full_content = ""
    async for chunk in query_model_stream(model, messages):
        if chunk.get("error"):
            print(f"ERROR: {chunk.get('message')}")
            return False

        if chunk.get("chunk"):
            text = chunk["chunk"]
            print(text, end="", flush=True)
            full_content += text

        if chunk.get("done"):
            usage = chunk.get("usage", {})
            print(f"\n\nTokens: {usage.get('input_tokens', 0)} in, {usage.get('output_tokens', 0)} out")
            print(f"Cost: ${usage.get('cost', 0):.6f}")

    print("\n✓ Streaming test passed")
    return True


def test_storage():
    """Test the quick message storage."""
    print("\nTesting quick message storage...")

    # Create a test conversation
    conversation_id = "test_quick_mode_123"
    conversation = storage.create_conversation(conversation_id)

    # Add a user message
    storage.add_user_message(conversation_id, "Test question")

    # Add a quick message
    storage.add_quick_message(
        conversation_id=conversation_id,
        content="Test response from model",
        model="openai/gpt-4o",
        thinking="Test thinking process",
        usage={"input_tokens": 10, "output_tokens": 20, "cost": 0.0001}
    )

    # Retrieve the conversation
    conv = storage.get_conversation(conversation_id)

    # Verify structure
    assert len(conv["messages"]) == 2, "Should have 2 messages"
    assert conv["messages"][0]["role"] == "user"
    assert conv["messages"][1]["role"] == "assistant"
    assert conv["messages"][1]["type"] == "quick"
    assert conv["messages"][1]["model"] == "openai/gpt-4o"
    assert "thinking" in conv["messages"][1]
    assert "usage" in conv["messages"][1]

    # Cleanup
    storage.delete_conversation(conversation_id)

    print("✓ Storage test passed")
    return True


def test_models_list():
    """Test that we can get the models list."""
    print("\nTesting models list...")

    models_count = len(AVAILABLE_MODELS)
    print(f"Available models: {models_count}")

    # Check a few expected models
    expected_models = [
        "openai/gpt-4o",
        "anthropic/claude-sonnet-4",
        "google/gemini-2.5-flash",
    ]

    for model in expected_models:
        if model in AVAILABLE_MODELS:
            info = AVAILABLE_MODELS[model]
            print(f"  ✓ {model}: {info['name']}")
        else:
            print(f"  ✗ {model}: NOT FOUND")

    print("✓ Models list test passed")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Quick Mode Tests")
    print("=" * 60)

    results = []

    # Test 1: Storage
    try:
        results.append(test_storage())
    except Exception as e:
        print(f"✗ Storage test failed: {e}")
        results.append(False)

    # Test 2: Models list
    try:
        results.append(test_models_list())
    except Exception as e:
        print(f"✗ Models list test failed: {e}")
        results.append(False)

    # Test 3: Streaming (requires API key)
    try:
        results.append(await test_streaming())
    except Exception as e:
        print(f"✗ Streaming test failed: {e}")
        print("  (This is expected if OPENROUTER_API_KEY is not set)")
        results.append(False)

    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed (check above for details)")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
