"""Tests for backend/voting.py module."""

import pytest
from unittest.mock import AsyncMock, patch
from backend.voting import (
    run_vote,
    _parse_vote,
    _calculate_results,
    _determine_winner,
)


class TestParseVote:
    """Tests for _parse_vote function."""

    def test_standard_format(self, sample_options):
        """Test parsing standard vote format."""
        vote_text = """VOTE: Option A
CONFIDENCE: 85%
REASON: This is the best option because it provides comprehensive coverage."""

        result = _parse_vote(vote_text, sample_options)

        assert result["choice"] == "Option A"
        assert result["confidence"] == 85
        assert "comprehensive coverage" in result["reasoning"]

    def test_numeric_vote(self, sample_options):
        """Test parsing vote by option number."""
        vote_text = """VOTE: 2
CONFIDENCE: 90%
REASON: Second option is more practical."""

        result = _parse_vote(vote_text, sample_options)

        assert result["choice"] == "Option B"  # 2nd option (0-indexed)
        assert result["confidence"] == 90

    def test_option_with_number_prefix(self, sample_options):
        """Test parsing 'Option 1' style vote."""
        vote_text = """VOTE: Option 1
CONFIDENCE: 75%
REASON: First is usually best."""

        result = _parse_vote(vote_text, sample_options)

        assert result["choice"] == "Option A"

    def test_partial_match(self):
        """Test partial option matching."""
        options = ["Implement feature now", "Wait until next sprint", "Cancel feature"]
        vote_text = """VOTE: Implement
CONFIDENCE: 60%
REASON: We should do it."""

        result = _parse_vote(vote_text, options)

        assert result["choice"] == "Implement feature now"

    def test_case_insensitive_match(self, sample_options):
        """Test case insensitive option matching."""
        vote_text = """VOTE: option a
CONFIDENCE: 80%
REASON: Lowercase works too."""

        result = _parse_vote(vote_text, sample_options)

        assert result["choice"] == "Option A"

    def test_missing_vote_returns_none(self, sample_options):
        """Test that missing VOTE returns None."""
        vote_text = """CONFIDENCE: 80%
REASON: No vote provided."""

        result = _parse_vote(vote_text, sample_options)

        assert result is None

    def test_invalid_vote_returns_none(self, sample_options):
        """Test that unmatched vote returns None."""
        vote_text = """VOTE: Option Z
CONFIDENCE: 80%
REASON: Invalid option."""

        result = _parse_vote(vote_text, sample_options)

        assert result is None

    def test_missing_confidence_defaults_to_50(self, sample_options):
        """Test default confidence when not provided."""
        vote_text = """VOTE: Option A
REASON: No confidence specified."""

        result = _parse_vote(vote_text, sample_options)

        assert result["choice"] == "Option A"
        assert result["confidence"] == 50

    def test_confidence_clamped_to_100(self, sample_options):
        """Test that confidence over 100 is clamped."""
        vote_text = """VOTE: Option A
CONFIDENCE: 150%
REASON: Over confident."""

        result = _parse_vote(vote_text, sample_options)

        assert result["confidence"] == 100

    def test_confidence_clamped_to_0(self, sample_options):
        """Test that negative confidence is clamped to 0."""
        vote_text = """VOTE: Option A
CONFIDENCE: -50%
REASON: Negative confidence."""

        result = _parse_vote(vote_text, sample_options)

        assert result["confidence"] == 0

    def test_missing_reason_default(self, sample_options):
        """Test default reason when not provided."""
        vote_text = """VOTE: Option A
CONFIDENCE: 80%"""

        result = _parse_vote(vote_text, sample_options)

        assert result["reasoning"] == "No reasoning provided"

    def test_multiline_reason(self, sample_options):
        """Test parsing multi-line reasoning."""
        vote_text = """VOTE: Option B
CONFIDENCE: 95%
REASON: This is a multi-line reason.
It spans multiple lines to provide
detailed justification."""

        result = _parse_vote(vote_text, sample_options)

        assert result["choice"] == "Option B"
        assert "multi-line" in result["reasoning"]

    def test_confidence_without_percent_sign(self, sample_options):
        """Test parsing confidence without % sign."""
        vote_text = """VOTE: Option A
CONFIDENCE: 75
REASON: No percent sign."""

        result = _parse_vote(vote_text, sample_options)

        assert result["confidence"] == 75


class TestCalculateResults:
    """Tests for _calculate_results function."""

    def test_unanimous_vote(self, sample_options):
        """Test when all models vote for same option."""
        votes = [
            {"model": "model1", "choice": "Option A", "confidence": 90, "reasoning": "Best"},
            {"model": "model2", "choice": "Option A", "confidence": 85, "reasoning": "Agreed"},
            {"model": "model3", "choice": "Option A", "confidence": 95, "reasoning": "Obviously"},
        ]

        result = _calculate_results(votes, sample_options)

        assert result["Option A"]["count"] == 3
        assert result["Option A"]["avg_confidence"] == 90.0  # (90+85+95)/3
        assert result["Option B"]["count"] == 0
        assert result["Option C"]["count"] == 0

    def test_split_vote(self, sample_options, sample_votes):
        """Test with votes split between options."""
        result = _calculate_results(sample_votes, sample_options)

        # Option A has 2 votes (85, 90), Option B has 1 vote (75)
        assert result["Option A"]["count"] == 2
        assert result["Option A"]["avg_confidence"] == 87.5  # (85+90)/2
        assert result["Option B"]["count"] == 1
        assert result["Option B"]["avg_confidence"] == 75.0
        assert result["Option C"]["count"] == 0

    def test_total_score_calculation(self, sample_options, sample_votes):
        """Test that total_score is calculated correctly."""
        result = _calculate_results(sample_votes, sample_options)

        # Option A: 2 * 87.5 = 175.0
        assert result["Option A"]["total_score"] == 175.0
        # Option B: 1 * 75 = 75.0
        assert result["Option B"]["total_score"] == 75.0

    def test_empty_votes(self, sample_options):
        """Test with no votes."""
        result = _calculate_results([], sample_options)

        for option in sample_options:
            assert result[option]["count"] == 0
            assert result[option]["avg_confidence"] == 0
            assert result[option]["total_score"] == 0

    def test_voters_list_populated(self, sample_options, sample_votes):
        """Test that voters list is correctly populated."""
        result = _calculate_results(sample_votes, sample_options)

        # Option A should have 2 voters
        voters_a = result["Option A"]["voters"]
        assert len(voters_a) == 2
        assert any(v["model"] == "openai/gpt-4" for v in voters_a)
        assert any(v["model"] == "anthropic/claude-3" for v in voters_a)

    def test_all_options_present_in_results(self):
        """Test that all options appear in results even with 0 votes."""
        options = ["A", "B", "C", "D", "E"]
        votes = [
            {"model": "m1", "choice": "A", "confidence": 80, "reasoning": ""},
        ]

        result = _calculate_results(votes, options)

        assert len(result) == 5
        for opt in options:
            assert opt in result

    def test_unknown_choice_ignored(self, sample_options):
        """Test that votes for unknown options are handled gracefully."""
        votes = [
            {"model": "m1", "choice": "Option X", "confidence": 80, "reasoning": ""},
            {"model": "m2", "choice": "Option A", "confidence": 90, "reasoning": ""},
        ]

        result = _calculate_results(votes, sample_options)

        # Only Option A should have a vote
        assert result["Option A"]["count"] == 1
        assert result["Option B"]["count"] == 0
        assert result["Option C"]["count"] == 0


class TestDetermineWinner:
    """Tests for _determine_winner function."""

    def test_clear_winner(self, sample_options):
        """Test determining winner with clear leader."""
        results = {
            "Option A": {"count": 3, "avg_confidence": 90.0, "total_score": 270.0, "voters": []},
            "Option B": {"count": 1, "avg_confidence": 60.0, "total_score": 60.0, "voters": []},
            "Option C": {"count": 0, "avg_confidence": 0, "total_score": 0, "voters": []},
        }

        winner = _determine_winner(results)

        assert winner["option"] == "Option A"
        assert winner["total_votes"] == 3
        assert winner["avg_confidence"] == 90.0
        assert winner["total_score"] == 270.0

    def test_high_confidence_beats_more_votes(self):
        """Test that higher total score wins even with fewer votes."""
        results = {
            "Option A": {"count": 2, "avg_confidence": 95.0, "total_score": 190.0, "voters": []},
            "Option B": {"count": 3, "avg_confidence": 50.0, "total_score": 150.0, "voters": []},
        }

        winner = _determine_winner(results)

        # Option A wins because 2*95=190 > 3*50=150
        assert winner["option"] == "Option A"

    def test_empty_results(self):
        """Test with empty results dict."""
        winner = _determine_winner({})

        assert winner["option"] is None
        assert winner["total_votes"] == 0
        assert winner["total_score"] == 0

    def test_no_votes_cast(self, sample_options):
        """Test when no votes were cast for any option."""
        results = {
            "Option A": {"count": 0, "avg_confidence": 0, "total_score": 0, "voters": []},
            "Option B": {"count": 0, "avg_confidence": 0, "total_score": 0, "voters": []},
        }

        winner = _determine_winner(results)

        assert winner["option"] is None
        assert winner["total_votes"] == 0

    def test_tie_resolved_by_max(self):
        """Test that ties are resolved (max returns one)."""
        results = {
            "Option A": {"count": 2, "avg_confidence": 75.0, "total_score": 150.0, "voters": []},
            "Option B": {"count": 2, "avg_confidence": 75.0, "total_score": 150.0, "voters": []},
        }

        winner = _determine_winner(results)

        # One of them should win (max picks one deterministically)
        assert winner["option"] in ["Option A", "Option B"]
        assert winner["total_score"] == 150.0


class TestRunVote:
    """Integration tests for run_vote async function."""

    @pytest.mark.asyncio
    async def test_full_vote_flow(self, mock_council_models, sample_options):
        """Test complete voting flow."""
        mock_responses = {
            "openai/gpt-4": {"content": "VOTE: Option A\nCONFIDENCE: 90%\nREASON: Best choice"},
            "anthropic/claude-3": {"content": "VOTE: Option A\nCONFIDENCE: 85%\nREASON: Agreed"},
            "google/gemini-pro": {"content": "VOTE: Option B\nCONFIDENCE: 70%\nREASON: Alternative"},
        }

        with patch("backend.voting.get_council_models", return_value=mock_council_models), \
             patch("backend.voting.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await run_vote("Which option is best?", sample_options)

            # Check structure
            assert "votes" in result
            assert "results" in result
            assert "winner" in result

            # Check votes
            assert len(result["votes"]) == 3

            # Check winner (Option A should win: 2 votes with high confidence)
            assert result["winner"]["option"] == "Option A"
            assert result["winner"]["total_votes"] == 2

    @pytest.mark.asyncio
    async def test_partial_failures(self, mock_council_models, sample_options):
        """Test when some models fail to respond."""
        mock_responses = {
            "openai/gpt-4": {"content": "VOTE: Option A\nCONFIDENCE: 90%\nREASON: Only good response"},
            "anthropic/claude-3": None,  # Failed
            "google/gemini-pro": {"content": "Invalid response format"},  # Parse will fail
        }

        with patch("backend.voting.get_council_models", return_value=mock_council_models), \
             patch("backend.voting.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await run_vote("Question?", sample_options)

            # Only 1 valid vote
            assert len(result["votes"]) == 1
            assert result["votes"][0]["model"] == "openai/gpt-4"

    @pytest.mark.asyncio
    async def test_all_failures(self, mock_council_models, sample_options):
        """Test when all models fail."""
        mock_responses = {
            "openai/gpt-4": None,
            "anthropic/claude-3": None,
            "google/gemini-pro": None,
        }

        with patch("backend.voting.get_council_models", return_value=mock_council_models), \
             patch("backend.voting.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await run_vote("Question?", sample_options)

            assert len(result["votes"]) == 0
            assert result["winner"]["option"] is None

    @pytest.mark.asyncio
    async def test_many_options(self, mock_council_models):
        """Test voting with many options."""
        options = [f"Option {i}" for i in range(10)]
        mock_responses = {
            "openai/gpt-4": {"content": "VOTE: Option 5\nCONFIDENCE: 80%\nREASON: Middle ground"},
            "anthropic/claude-3": {"content": "VOTE: 5\nCONFIDENCE: 75%\nREASON: Same"},
            "google/gemini-pro": {"content": "VOTE: Option 5\nCONFIDENCE: 85%\nREASON: Agreed"},
        }

        with patch("backend.voting.get_council_models", return_value=mock_council_models), \
             patch("backend.voting.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await run_vote("Pick an option", options)

            assert result["winner"]["option"] == "Option 5"
            assert result["winner"]["total_votes"] == 3

    @pytest.mark.asyncio
    async def test_results_contain_all_options(self, mock_council_models, sample_options):
        """Test that results dict contains all options even with no votes."""
        mock_responses = {
            "openai/gpt-4": {"content": "VOTE: Option A\nCONFIDENCE: 100%\nREASON: Only A"},
            "anthropic/claude-3": {"content": "VOTE: Option A\nCONFIDENCE: 100%\nREASON: Agreed"},
            "google/gemini-pro": {"content": "VOTE: Option A\nCONFIDENCE: 100%\nREASON: Unanimous"},
        }

        with patch("backend.voting.get_council_models", return_value=mock_council_models), \
             patch("backend.voting.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await run_vote("All vote A", sample_options)

            # All options should be in results
            assert "Option A" in result["results"]
            assert "Option B" in result["results"]
            assert "Option C" in result["results"]

            # B and C should have 0 votes
            assert result["results"]["Option B"]["count"] == 0
            assert result["results"]["Option C"]["count"] == 0
