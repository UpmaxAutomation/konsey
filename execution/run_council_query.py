#!/usr/bin/env python3
"""
Council Query Execution Script
Runs a 3-stage deliberation query through the LLM Council.

Usage:
    python execution/run_council_query.py --query "Your question" --preset reasoning
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

BASE_URL = "http://localhost:8001"


async def create_conversation() -> str:
    """Create a new conversation."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/api/conversations")
        response.raise_for_status()
        return response.json()["id"]


async def apply_preset(preset_id: str) -> dict:
    """Apply a council preset."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/api/presets/{preset_id}/apply")
        response.raise_for_status()
        return response.json()


async def send_query(conversation_id: str, query: str) -> dict:
    """Send a query to the council."""
    async with httpx.AsyncClient(timeout=180.0) as client:  # Extended timeout for reasoning models
        response = await client.post(
            f"{BASE_URL}/api/conversations/{conversation_id}/message",
            json={"content": query}
        )
        response.raise_for_status()
        return response.json()


async def run_council_query(
    query: str,
    preset: str = None,
    conversation_id: str = None,
    verbose: bool = False,
) -> dict:
    """
    Run a council query with optional preset.

    Args:
        query: The question to ask
        preset: Optional preset ID (code_review, research, creative, reasoning, budget)
        conversation_id: Optional existing conversation ID
        verbose: Print detailed output

    Returns:
        Full response with stage1, stage2, stage3, and metadata
    """
    # Create conversation if not provided
    if not conversation_id:
        conversation_id = await create_conversation()
        if verbose:
            print(f"Created conversation: {conversation_id}")

    # Apply preset if specified
    if preset:
        preset_result = await apply_preset(preset)
        if verbose:
            print(f"Applied preset: {preset_result['preset_name']}")
            print(f"Council: {', '.join(preset_result['council_models'])}")
            print(f"Chairman: {preset_result['chairman_model']}")

    # Send query
    if verbose:
        print(f"\nSending query: {query[:100]}...")

    result = await send_query(conversation_id, query)

    return {
        "conversation_id": conversation_id,
        "query": query,
        "preset": preset,
        **result
    }


def format_output(result: dict, verbose: bool = False) -> str:
    """Format the result for display."""
    output = []

    output.append("=" * 60)
    output.append("LLM COUNCIL RESPONSE")
    output.append("=" * 60)

    # Stage 1: Individual responses
    if "stage1" in result:
        output.append("\n📋 STAGE 1: Individual Responses")
        output.append("-" * 40)
        for model, response in result["stage1"].items():
            output.append(f"\n🤖 {model}:")
            content = response.get("content", "No response")
            if verbose:
                output.append(content)
            else:
                output.append(content[:200] + "..." if len(content) > 200 else content)

    # Stage 2: Rankings (summary)
    if "stage2" in result:
        output.append("\n📊 STAGE 2: Peer Rankings")
        output.append("-" * 40)
        if "aggregate_rankings" in result.get("metadata", {}):
            output.append("Aggregate Rankings:")
            for ranking in result["metadata"]["aggregate_rankings"]:
                output.append(f"  {ranking['position']}. {ranking['model']} (avg: {ranking['avg_rank']:.2f})")

    # Stage 3: Final answer
    if "stage3" in result:
        output.append("\n✅ STAGE 3: Chairman's Synthesis")
        output.append("-" * 40)
        output.append(result["stage3"].get("content", "No synthesis"))

    output.append("\n" + "=" * 60)

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Run LLM Council query")
    parser.add_argument("--query", "-q", required=True, help="Question to ask the council")
    parser.add_argument("--preset", "-p", help="Preset to use (code_review, research, creative, reasoning, budget)")
    parser.add_argument("--conversation", "-c", help="Existing conversation ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full responses")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        result = asyncio.run(run_council_query(
            query=args.query,
            preset=args.preset,
            conversation_id=args.conversation,
            verbose=args.verbose,
        ))

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_output(result, args.verbose))

    except httpx.ConnectError:
        print("ERROR: Cannot connect to backend. Is the server running on port 8001?")
        print("Start it with: python -m backend.main")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"ERROR: HTTP {e.response.status_code}: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
