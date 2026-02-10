#!/usr/bin/env python3
"""
Council Vote Execution Script
Runs a voting session through the LLM Council.

Usage:
    python execution/run_council_vote.py --question "Which is best?" --options "A,B,C"
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


async def run_vote(conversation_id: str, question: str, options: list) -> dict:
    """Run a vote through the council."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/conversations/{conversation_id}/vote",
            json={"question": question, "options": options}
        )
        response.raise_for_status()
        return response.json()


async def council_vote(
    question: str,
    options: list,
    conversation_id: str = None,
) -> dict:
    """
    Run a council vote.

    Args:
        question: The question to vote on
        options: List of options to choose from
        conversation_id: Optional existing conversation ID

    Returns:
        Vote results with winner
    """
    # Create conversation if not provided
    if not conversation_id:
        conversation_id = await create_conversation()

    # Run vote
    result = await run_vote(conversation_id, question, options)

    return {
        "conversation_id": conversation_id,
        "question": question,
        "options": options,
        **result
    }


def format_output(result: dict) -> str:
    """Format the result for display."""
    output = []

    output.append("=" * 60)
    output.append("LLM COUNCIL VOTE RESULTS")
    output.append("=" * 60)

    output.append(f"\n📋 Question: {result['question']}")
    output.append(f"📝 Options: {', '.join(result['options'])}")

    # Individual votes
    if "votes" in result:
        output.append("\n🗳️ Individual Votes:")
        output.append("-" * 40)
        for vote in result["votes"]:
            confidence = vote.get("confidence", 0)
            emoji = "🟢" if confidence >= 70 else "🟡" if confidence >= 40 else "🔴"
            output.append(f"  {emoji} {vote['model']}: {vote['vote']} ({confidence}%)")
            if vote.get("reason"):
                output.append(f"     └─ {vote['reason'][:80]}...")

    # Aggregated results
    if "results" in result:
        output.append("\n📊 Aggregated Results:")
        output.append("-" * 40)
        sorted_results = sorted(
            result["results"].items(),
            key=lambda x: x[1].get("total_score", 0),
            reverse=True
        )
        for option, stats in sorted_results:
            count = stats.get("count", 0)
            avg_conf = stats.get("avg_confidence", 0)
            total = stats.get("total_score", 0)
            output.append(f"  {option}: {count} votes, {avg_conf:.1f}% avg confidence, {total:.1f} total score")

    # Winner
    if "winner" in result and result["winner"]:
        output.append("\n🏆 Winner:")
        output.append("-" * 40)
        winner = result["winner"]
        output.append(f"  {winner['option']}")
        output.append(f"  └─ {winner['votes']} votes × {winner['avg_confidence']:.1f}% = {winner['total_score']:.1f}")

    output.append("\n" + "=" * 60)

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Run LLM Council vote")
    parser.add_argument("--question", "-q", required=True, help="Question to vote on")
    parser.add_argument("--options", "-o", required=True, help="Comma-separated options")
    parser.add_argument("--conversation", "-c", help="Existing conversation ID")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    options = [opt.strip() for opt in args.options.split(",")]

    if len(options) < 2:
        print("ERROR: At least 2 options required")
        sys.exit(1)

    if len(options) > 26:
        print("ERROR: Maximum 26 options supported")
        sys.exit(1)

    try:
        result = asyncio.run(council_vote(
            question=args.question,
            options=options,
            conversation_id=args.conversation,
        ))

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_output(result))

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
