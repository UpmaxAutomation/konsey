"""Unit tests for voting.py - Voting system."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.voting import (
    run_vote,
    _parse_vote,
    _calculate_results,
    _determine_winner,
)


class TestParseVote:
    """Tests for the vote parsing function."""

    def test_parse_standard_format(self):
        """Test parsing standard VOTE/CONFIDENCE/REASON format."""
        text = """After careful consideration...

VOTE: Python
CONFIDENCE: 85%
REASON: Python is great for beginners because of its readable syntax."""

        options = ["Python", "JavaScript", "Java"]
        result = _parse_vote(text, options)

        assert result is not None
        assert result["choice"] == "Python"
        assert result["confidence"] == 85
        assert "readable syntax" in result["reasoning"]

    def test_parse_by_number(self):
        """Test parsing vote by number reference."""
        text = """VOTE: 2
CONFIDENCE: 75%
REASON: Option 2 is the most balanced choice."""

        options = ["Python", "JavaScript", "Java"]
        result = _parse_vote(text, options)

        assert result is not None
        assert result["choice"] == "JavaScript"  # Index 1 (second option)
        assert result["confidence"] == 75

    def test_parse_option_number_format(self):
        """Test parsing 'Option X' format."""
        text = """VOTE: Option 3
CONFIDENCE: 90%
REASON: Best option overall."""

        options = ["Python", "JavaScript", "Java"]
        result = _parse_vote(text, options)

        assert result is not None
        assert result["choice"] == "Java"  # Index 2 (third option)

    def test_parse_case_insensitive(self):
        """Test case-insensitive option matching."""
        text = """VOTE: PYTHON
CONFIDENCE: 80%
REASON: Clear winner."""

        options = ["Python", "JavaScript", "Java"]
        result = _parse_vote(text, options)

        assert result is not None
        assert result["choice"] == "Python"

    def test_parse_partial_match(self):
        """Test partial option matching."""
        text = """VOTE: I believe JavaScript is best
CONFIDENCE: 70%
REASON: Most versatile."""

        options = ["Python", "JavaScript", "Java"]
        result = _parse_vote(text, options)

        assert result is not None
        assert result["choice"] == "JavaScript"

    def test_parse_missing_confidence(self):
        """Test default confidence when missing."""
        text = """VOTE: Python
REASON: Good for beginners."""

        options = ["Python", "JavaScript"]
        result = _parse_vote(text, options)

        assert result is not None
        assert result["confidence"] == 50  # Default

    def test_parse_confidence_clamped(self):
        """Test confidence is clamped to 0-100."""
        text = """VOTE: Python
CONFIDENCE: 150%
REASON: Very confident."""

        options = ["Python", "JavaScript"]
        result = _parse_vote(text, options)

        assert result is not None
        assert result["confidence"] == 100  # Clamped

    def test_parse_missing_reason(self):
        """Test default reason when missing."""
        text = """VOTE: Python
CONFIDENCE: 80%"""

        options = ["Python", "JavaScript"]
        result = _parse_vote(text, options)

        assert result is not None
        assert result["reasoning"] == "No reasoning provided"

    def test_parse_no_vote(self):
        """Test handling when no VOTE found."""
        text = "I think Python is the best choice."
        options = ["Python", "JavaScript"]
        result = _parse_vote(text, options)

        assert result is None

    def test_parse_invalid_option(self):
        """Test handling when vote doesn't match any option."""
        text = """VOTE: Ruby
CONFIDENCE: 80%
REASON: Ruby is great."""

        options = ["Python", "JavaScript", "Java"]
        result = _parse_vote(text, options)

        assert result is None

    def test_parse_multiline_reason(self):
        """Test parsing multi-line reasoning."""
        text = """VOTE: Python
CONFIDENCE: 85%
REASON: Python is excellent because:
1. Clean syntax
2. Large ecosystem
3. Great community"""

        options = ["Python", "JavaScript"]
        result = _parse_vote(text, options)

        assert result is not None
        assert "Clean syntax" in result["reasoning"]
        assert "Large ecosystem" in result["reasoning"]


class TestCalculateResults:
    """Tests for result calculation."""

    def test_single_unanimous_vote(self):
        """Test when all voters choose the same option."""
        votes = [
            {"choice": "Python", "confidence": 80, "model": "model-a"},
            {"choice": "Python", "confidence": 90, "model": "model-b"},
            {"choice": "Python", "confidence": 85, "model": "model-c"},
        ]
        options = ["Python", "JavaScript", "Java"]

        results = _calculate_results(votes, options)

        assert results["Python"]["count"] == 3
        assert results["Python"]["avg_confidence"] == 85.0
        assert len(results["Python"]["voters"]) == 3
        assert results["JavaScript"]["count"] == 0
        assert results["Java"]["count"] == 0

    def test_split_votes(self):
        """Test when votes are split across options."""
        votes = [
            {"choice": "Python", "confidence": 80, "model": "model-a"},
            {"choice": "JavaScript", "confidence": 90, "model": "model-b"},
            {"choice": "JavaScript", "confidence": 70, "model": "model-c"},
        ]
        options = ["Python", "JavaScript", "Java"]

        results = _calculate_results(votes, options)

        assert results["Python"]["count"] == 1
        assert results["Python"]["avg_confidence"] == 80.0
        assert results["JavaScript"]["count"] == 2
        assert results["JavaScript"]["avg_confidence"] == 80.0

    def test_empty_votes(self):
        """Test with no votes."""
        votes = []
        options = ["Python", "JavaScript"]

        results = _calculate_results(votes, options)

        assert results["Python"]["count"] == 0
        assert results["Python"]["avg_confidence"] == 0
        assert results["JavaScript"]["count"] == 0

    def test_total_score_calculation(self):
        """Test total score calculation (count * avg_confidence)."""
        votes = [
            {"choice": "Python", "confidence": 100, "model": "model-a"},
            {"choice": "Python", "confidence": 100, "model": "model-b"},
            {"choice": "JavaScript", "confidence": 50, "model": "model-c"},
        ]
        options = ["Python", "JavaScript"]

        results = _calculate_results(votes, options)

        # Python: 2 votes * 100 avg = 200
        assert results["Python"]["total_score"] == 200.0
        # JavaScript: 1 vote * 50 avg = 50
        assert results["JavaScript"]["total_score"] == 50.0


class TestDetermineWinner:
    """Tests for winner determination."""

    def test_clear_winner(self):
        """Test determining winner with clear lead."""
        results = {
            "Python": {"count": 3, "avg_confidence": 85.0, "total_score": 255.0, "voters": []},
            "JavaScript": {"count": 1, "avg_confidence": 70.0, "total_score": 70.0, "voters": []},
        }

        winner = _determine_winner(results)

        assert winner["option"] == "Python"
        assert winner["total_votes"] == 3
        assert winner["avg_confidence"] == 85.0
        assert winner["total_score"] == 255.0

    def test_confidence_breaks_tie(self):
        """Test that confidence breaks vote count ties."""
        results = {
            "Python": {"count": 2, "avg_confidence": 90.0, "total_score": 180.0, "voters": []},
            "JavaScript": {"count": 2, "avg_confidence": 70.0, "total_score": 140.0, "voters": []},
        }

        winner = _determine_winner(results)

        # Python wins due to higher total_score (180 vs 140)
        assert winner["option"] == "Python"

    def test_empty_results(self):
        """Test with empty results."""
        winner = _determine_winner({})

        assert winner["option"] is None
        assert winner["total_votes"] == 0

    def test_single_option(self):
        """Test with single option."""
        results = {
            "Python": {"count": 5, "avg_confidence": 80.0, "total_score": 400.0, "voters": []},
        }

        winner = _determine_winner(results)

        assert winner["option"] == "Python"
        assert winner["total_votes"] == 5


@pytest.mark.asyncio
class TestRunVote:
    """Tests for the main run_vote function."""

    async def test_run_vote_success(self):
        """Test successful voting process."""
        mock_responses = {
            "model-a": {
                "content": "VOTE: Python\nCONFIDENCE: 85%\nREASON: Best for beginners."
            },
            "model-b": {
                "content": "VOTE: Python\nCONFIDENCE: 90%\nREASON: Clean syntax."
            },
            "model-c": {
                "content": "VOTE: JavaScript\nCONFIDENCE: 75%\nREASON: More versatile."
            },
        }

        with patch("backend.voting.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.voting.get_council_models", return_value=list(mock_responses.keys())):
                result = await run_vote(
                    "What's the best programming language for beginners?",
                    ["Python", "JavaScript", "Java"]
                )

        assert len(result["votes"]) == 3
        assert result["winner"]["option"] == "Python"
        assert result["winner"]["total_votes"] == 2

    async def test_run_vote_partial_failures(self):
        """Test voting handles some model failures."""
        mock_responses = {
            "model-a": {
                "content": "VOTE: Python\nCONFIDENCE: 85%\nREASON: Great choice."
            },
            "model-b": None,  # Failed
            "model-c": {
                "content": "Invalid response without VOTE"  # Parse fails
            },
        }

        with patch("backend.voting.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.voting.get_council_models", return_value=list(mock_responses.keys())):
                result = await run_vote("Question?", ["Python", "JavaScript"])

        # Only one valid vote parsed
        assert len(result["votes"]) == 1
        assert result["votes"][0]["model"] == "model-a"

    async def test_run_vote_all_fail(self):
        """Test voting when all models fail."""
        mock_responses = {
            "model-a": None,
            "model-b": None,
        }

        with patch("backend.voting.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.voting.get_council_models", return_value=list(mock_responses.keys())):
                result = await run_vote("Question?", ["Python", "JavaScript"])

        assert len(result["votes"]) == 0
        assert result["winner"]["option"] is None

    async def test_run_vote_includes_reasoning(self):
        """Test that reasoning is preserved in votes."""
        mock_responses = {
            "model-a": {
                "content": "VOTE: Python\nCONFIDENCE: 85%\nREASON: Readable syntax makes learning easier."
            },
        }

        with patch("backend.voting.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.voting.get_council_models", return_value=["model-a"]):
                result = await run_vote("Question?", ["Python", "JavaScript"])

        assert "Readable syntax" in result["votes"][0]["reasoning"]
