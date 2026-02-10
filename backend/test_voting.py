"""Test script for the voting system."""

import asyncio
from voting import run_vote, _parse_vote, _calculate_results, _determine_winner


async def test_voting():
    """Test the voting system with a sample question."""
    question = "What is the best programming language for web development?"
    options = [
        "JavaScript/TypeScript",
        "Python",
        "Go",
        "Rust"
    ]

    print("=" * 80)
    print("TESTING LLM COUNCIL VOTING SYSTEM")
    print("=" * 80)
    print(f"\nQuestion: {question}")
    print(f"\nOptions:")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    print("\n" + "=" * 80)
    print("Running vote with all council models...")
    print("=" * 80 + "\n")

    # Run the vote
    results = await run_vote(question, options)

    # Display individual votes
    print("INDIVIDUAL VOTES:")
    print("-" * 80)
    for vote in results["votes"]:
        print(f"\nModel: {vote['model']}")
        print(f"Choice: {vote['choice']}")
        print(f"Confidence: {vote['confidence']}%")
        print(f"Reasoning: {vote['reasoning'][:200]}...")  # First 200 chars
        print("-" * 80)

    # Display aggregate results
    print("\n\nAGGREGATE RESULTS:")
    print("=" * 80)
    for option, data in results["results"].items():
        print(f"\n{option}:")
        print(f"  Total Votes: {data['count']}")
        print(f"  Average Confidence: {data['avg_confidence']}%")
        print(f"  Total Score: {data['total_score']}")
        if data['voters']:
            print(f"  Voters: {', '.join([v['model'].split('/')[-1] for v in data['voters']])}")

    # Display winner
    print("\n\n" + "=" * 80)
    print("WINNER:")
    print("=" * 80)
    winner = results["winner"]
    if winner["option"]:
        print(f"Option: {winner['option']}")
        print(f"Total Votes: {winner['total_votes']}")
        print(f"Average Confidence: {winner['avg_confidence']}%")
        print(f"Total Score: {winner['total_score']}")
    else:
        print("No winner (no votes received)")
    print("=" * 80)


def test_parse_vote():
    """Test the vote parsing function."""
    print("\n\nTESTING VOTE PARSER:")
    print("=" * 80)

    test_cases = [
        {
            "text": "VOTE: JavaScript/TypeScript\nCONFIDENCE: 85%\nREASON: Most popular for web dev",
            "options": ["JavaScript/TypeScript", "Python", "Go", "Rust"],
            "expected_choice": "JavaScript/TypeScript"
        },
        {
            "text": "VOTE: 2\nCONFIDENCE: 70\nREASON: Python is versatile",
            "options": ["JavaScript/TypeScript", "Python", "Go", "Rust"],
            "expected_choice": "Python"
        },
        {
            "text": "VOTE: Option 3\nCONFIDENCE: 60%\nREASON: Go is fast",
            "options": ["JavaScript/TypeScript", "Python", "Go", "Rust"],
            "expected_choice": "Go"
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Input: {case['text'][:50]}...")
        result = _parse_vote(case["text"], case["options"])
        if result:
            print(f"Parsed Choice: {result['choice']}")
            print(f"Confidence: {result['confidence']}%")
            print(f"Match: {'✓' if result['choice'] == case['expected_choice'] else '✗'}")
        else:
            print("Failed to parse")
        print("-" * 80)


if __name__ == "__main__":
    # Test parser first
    test_parse_vote()

    # Test full voting system
    print("\n\n")
    asyncio.run(test_voting())
