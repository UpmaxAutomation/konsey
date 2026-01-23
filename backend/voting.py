"""Voting system for LLM Council."""

from typing import List, Dict, Any, Optional
import uuid
from .openrouter import query_models_parallel
from .config import get_council_models
import re


async def run_vote(question: str, options: List[str], user_id: Optional[uuid.UUID] = None, db: Optional[Any] = None) -> Dict[str, Any]:
    """
    Run a vote where each council model votes on the provided options.

    Args:
        question: The question or context for the vote
        options: List of options to vote on

    Returns:
        Dict containing:
            - votes: List of individual votes with model, choice, confidence, reasoning
            - results: Dict of vote counts and statistics per option
            - winner: The option with highest total score (votes * avg confidence)
    """
    # Build the voting prompt
    options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])

    voting_prompt = f"""You are participating in a council vote. Please carefully evaluate the options and vote for ONE option.

Question/Context: {question}

Options:
{options_text}

Your task:
1. Pick ONE option from the list above that you believe is the best answer
2. Provide your confidence level (0-100%)
3. Give brief reasoning for your choice

IMPORTANT: Format your response EXACTLY as follows:
VOTE: [exact option text or number]
CONFIDENCE: [number]%
REASON: [your reasoning]

Example:
VOTE: Option 2
CONFIDENCE: 85%
REASON: This option provides the most comprehensive solution because...

Now provide your vote:"""

    messages = [{"role": "user", "content": voting_prompt}]

    # Query all council models in parallel (using user-specific API keys)
    responses = await query_models_parallel(get_council_models(), messages, user_id=user_id, db=db)

    # Parse votes from each model
    votes = []
    for model, response in responses.items():
        if response is not None:
            content = response.get('content', '')
            parsed_vote = _parse_vote(content, options)
            if parsed_vote:
                votes.append({
                    "model": model,
                    "choice": parsed_vote["choice"],
                    "confidence": parsed_vote["confidence"],
                    "reasoning": parsed_vote["reasoning"]
                })

    # Calculate results
    results = _calculate_results(votes, options)

    # Determine winner
    winner = _determine_winner(results)

    return {
        "votes": votes,
        "results": results,
        "winner": winner
    }


def _parse_vote(vote_text: str, options: List[str]) -> Dict[str, Any]:
    """
    Parse a vote from model response text.

    Args:
        vote_text: The model's response text
        options: List of valid options

    Returns:
        Dict with choice, confidence, reasoning or None if parse failed
    """
    # Extract VOTE
    vote_match = re.search(r'VOTE:\s*(.+?)(?:\n|$)', vote_text, re.IGNORECASE)
    if not vote_match:
        return None

    raw_choice = vote_match.group(1).strip()

    # Try to match to an option
    # First, try exact match (case-insensitive)
    choice = None
    for option in options:
        if option.lower() == raw_choice.lower():
            choice = option
            break

    # If no exact match, check if it's a number
    if not choice:
        # Try to extract number (e.g., "Option 2" -> "2" or just "2")
        number_match = re.search(r'\d+', raw_choice)
        if number_match:
            option_num = int(number_match.group()) - 1  # Convert to 0-indexed
            if 0 <= option_num < len(options):
                choice = options[option_num]

    # If still no match, try partial match
    if not choice:
        for option in options:
            if raw_choice.lower() in option.lower() or option.lower() in raw_choice.lower():
                choice = option
                break

    if not choice:
        return None

    # Extract CONFIDENCE
    confidence_match = re.search(r'CONFIDENCE:\s*(\d+)%?', vote_text, re.IGNORECASE)
    confidence = int(confidence_match.group(1)) if confidence_match else 50  # Default to 50% if not found

    # Clamp confidence to 0-100
    confidence = max(0, min(100, confidence))

    # Extract REASON
    reason_match = re.search(r'REASON:\s*(.+?)(?:\n\n|\Z)', vote_text, re.IGNORECASE | re.DOTALL)
    reasoning = reason_match.group(1).strip() if reason_match else "No reasoning provided"

    return {
        "choice": choice,
        "confidence": confidence,
        "reasoning": reasoning
    }


def _calculate_results(votes: List[Dict[str, Any]], options: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate voting results by option.

    Args:
        votes: List of parsed votes
        options: List of all options

    Returns:
        Dict mapping option to statistics (count, avg_confidence, voters)
    """
    from collections import defaultdict

    # Initialize results for all options
    results = {}
    for option in options:
        results[option] = {
            "count": 0,
            "total_confidence": 0,
            "avg_confidence": 0,
            "voters": [],
            "total_score": 0  # count * avg_confidence
        }

    # Aggregate votes
    for vote in votes:
        choice = vote["choice"]
        if choice in results:
            results[choice]["count"] += 1
            results[choice]["total_confidence"] += vote["confidence"]
            results[choice]["voters"].append({
                "model": vote["model"],
                "confidence": vote["confidence"]
            })

    # Calculate averages and scores
    for option, data in results.items():
        if data["count"] > 0:
            data["avg_confidence"] = round(data["total_confidence"] / data["count"], 1)
            data["total_score"] = round(data["count"] * data["avg_confidence"], 1)
        # Remove total_confidence as it's not needed in output
        del data["total_confidence"]

    return results


def _determine_winner(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Determine the winning option based on total score (votes * avg confidence).

    Args:
        results: Results dict from _calculate_results

    Returns:
        Dict with option, total_votes, avg_confidence, total_score
    """
    if not results:
        return {
            "option": None,
            "total_votes": 0,
            "avg_confidence": 0,
            "total_score": 0
        }

    # Find option with highest total_score
    winner_option = max(results.items(), key=lambda x: x[1]["total_score"])

    # If no votes were cast (all options have 0 votes), return None as winner
    if winner_option[1]["count"] == 0:
        return {
            "option": None,
            "total_votes": 0,
            "avg_confidence": 0,
            "total_score": 0
        }

    return {
        "option": winner_option[0],
        "total_votes": winner_option[1]["count"],
        "avg_confidence": winner_option[1]["avg_confidence"],
        "total_score": winner_option[1]["total_score"]
    }
