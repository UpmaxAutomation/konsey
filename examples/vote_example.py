"""
Example: Using the LLM Council Voting System

This script demonstrates how to use the voting endpoint to get
the council's collective decision on a multiple-choice question.
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8001"


def create_conversation():
    """Create a new conversation."""
    response = requests.post(f"{BASE_URL}/api/conversations")
    response.raise_for_status()
    conversation = response.json()
    print(f"Created conversation: {conversation['id']}\n")
    return conversation['id']


def run_vote(conversation_id, question, options):
    """Run a vote on a question with multiple options."""
    print("=" * 80)
    print("RUNNING VOTE")
    print("=" * 80)
    print(f"Question: {question}\n")
    print("Options:")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    print("\n" + "=" * 80)
    print("Collecting votes from council models...")
    print("=" * 80 + "\n")

    response = requests.post(
        f"{BASE_URL}/api/conversations/{conversation_id}/vote",
        json={"question": question, "options": options}
    )
    response.raise_for_status()
    results = response.json()

    # Display individual votes
    print("INDIVIDUAL VOTES:")
    print("-" * 80)
    for vote in results["votes"]:
        model_name = vote['model'].split('/')[-1]  # Just the model name
        print(f"\n{model_name}:")
        print(f"  Choice: {vote['choice']}")
        print(f"  Confidence: {vote['confidence']}%")
        print(f"  Reasoning: {vote['reasoning'][:150]}...")
        print("-" * 80)

    # Display aggregate results
    print("\n\nAGGREGATE RESULTS:")
    print("=" * 80)

    # Sort by total score
    sorted_results = sorted(
        results["results"].items(),
        key=lambda x: x[1]["total_score"],
        reverse=True
    )

    for option, data in sorted_results:
        print(f"\n{option}:")
        print(f"  Votes: {data['count']}")
        print(f"  Avg Confidence: {data['avg_confidence']}%")
        print(f"  Total Score: {data['total_score']}")

    # Display winner
    print("\n\n" + "=" * 80)
    print("WINNER")
    print("=" * 80)
    winner = results["winner"]
    if winner["option"]:
        print(f"\n  {winner['option']}")
        print(f"\n  {winner['total_votes']} votes @ {winner['avg_confidence']}% avg confidence")
        print(f"  Total Score: {winner['total_score']}")
    else:
        print("\n  No winner (no valid votes)")
    print("\n" + "=" * 80)

    return results


def main():
    """Run example votes."""

    # Create a conversation
    conversation_id = create_conversation()

    # Example 1: Best programming language for web development
    print("\n\nEXAMPLE 1: Programming Language for Web Development\n")
    run_vote(
        conversation_id,
        question="What is the best programming language for modern web development?",
        options=[
            "JavaScript/TypeScript",
            "Python",
            "Go",
            "Rust"
        ]
    )

    print("\n\n" + "=" * 80)
    print("Press Enter to continue to next example...")
    input()

    # Example 2: State management in React
    print("\n\nEXAMPLE 2: React State Management\n")
    run_vote(
        conversation_id,
        question="What is the best approach for state management in a large React application?",
        options=[
            "Redux Toolkit",
            "Context API with useReducer",
            "Zustand",
            "Jotai",
            "MobX"
        ]
    )

    print("\n\n" + "=" * 80)
    print("Press Enter to continue to next example...")
    input()

    # Example 3: Database choice
    print("\n\nEXAMPLE 3: Database Selection\n")
    run_vote(
        conversation_id,
        question="What database should we use for a real-time collaborative application with complex queries?",
        options=[
            "PostgreSQL",
            "MongoDB",
            "CockroachDB",
            "Firebase Firestore",
            "Supabase (PostgreSQL)",
            "DynamoDB"
        ]
    )

    print("\n\n✅ Examples completed!\n")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the backend.")
        print("   Make sure the backend is running on http://localhost:8001")
        print("\n   Start it with:")
        print("   cd /Users/sezars/llm-council")
        print("   python3 -m backend.main")
    except Exception as e:
        print(f"❌ Error: {e}")
