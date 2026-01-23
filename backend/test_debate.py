#!/usr/bin/env python3
"""Test script for debate mode."""

import asyncio
from debate import run_debate
from config import set_council_models

# Use a small set of models for testing
test_models = [
    "google/gemini-2.5-flash",
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o-mini",
    "meta-llama/llama-3.3-70b-instruct"
]

async def test_debate():
    """Test the debate function."""
    set_council_models(test_models)

    topic = "Should artificial intelligence be regulated by governments?"
    rounds = 2

    print(f"\n{'='*60}")
    print(f"Testing Debate Mode")
    print(f"{'='*60}")
    print(f"Topic: {topic}")
    print(f"Rounds: {rounds}")
    print(f"Models: {len(test_models)} total ({len(test_models)//2} pro, {len(test_models)//2} con)")
    print(f"{'='*60}\n")

    result = await run_debate(topic, rounds)

    print(f"\n{'='*60}")
    print("DEBATE RESULTS")
    print(f"{'='*60}\n")

    # Show metadata
    print(f"Pro Team: {', '.join(result['metadata']['pro_models'])}")
    print(f"Con Team: {', '.join(result['metadata']['con_models'])}")
    print(f"\nTotal Rounds: {result['metadata']['total_rounds']}\n")

    # Show each round
    for round_data in result['rounds']:
        round_num = round_data['round_number']
        print(f"\n{'='*60}")
        print(f"ROUND {round_num}")
        print(f"{'='*60}\n")

        print(f"--- PRO Arguments ({len(round_data['pro'])} models) ---\n")
        for i, arg in enumerate(round_data['pro'], 1):
            print(f"{i}. {arg['model']}:")
            print(f"   {arg['argument'][:200]}...\n")

        print(f"--- CON Arguments ({len(round_data['con'])} models) ---\n")
        for i, arg in enumerate(round_data['con'], 1):
            print(f"{i}. {arg['model']}:")
            print(f"   {arg['argument'][:200]}...\n")

    # Show synthesis
    print(f"\n{'='*60}")
    print("CHAIRMAN SYNTHESIS")
    print(f"{'='*60}\n")
    print(f"Model: {result['synthesis']['model']}\n")
    print(result['synthesis']['response'])
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(test_debate())
