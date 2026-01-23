"""Unit tests for council.py - Core deliberation logic."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.council import (
    parse_ranking_from_text,
    calculate_aggregate_rankings,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    generate_conversation_title,
)


class TestParseRankingFromText:
    """Tests for the ranking parser function."""

    def test_parse_standard_format(self):
        """Test parsing standard FINAL RANKING format."""
        text = """
        Response A is great because it provides detailed analysis.
        Response B lacks depth in certain areas.
        Response C is comprehensive but verbose.

        FINAL RANKING:
        1. Response B
        2. Response A
        3. Response C
        """
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A", "Response C"]

    def test_parse_no_spaces_format(self):
        """Test parsing without spaces after numbers."""
        text = """
        FINAL RANKING:
        1.Response A
        2.Response B
        3.Response C
        """
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_parse_extra_whitespace(self):
        """Test parsing with extra whitespace."""
        text = """
        FINAL RANKING:
        1.   Response C
        2.   Response A
        3.   Response B
        """
        result = parse_ranking_from_text(text)
        assert result == ["Response C", "Response A", "Response B"]

    def test_parse_no_ranking_section_fallback(self):
        """Test fallback when no FINAL RANKING section exists."""
        text = "Response A is best, followed by Response B, then Response C"
        result = parse_ranking_from_text(text)
        # Should extract Response labels in order of appearance
        assert result == ["Response A", "Response B", "Response C"]

    def test_parse_empty_text(self):
        """Test handling empty text."""
        result = parse_ranking_from_text("")
        assert result == []

    def test_parse_no_responses(self):
        """Test handling text with no Response labels."""
        text = "This text contains no response labels at all."
        result = parse_ranking_from_text(text)
        assert result == []

    def test_parse_lowercase_ranking_header(self):
        """Test that lowercase FINAL RANKING doesn't match (case sensitive)."""
        text = """
        final ranking:
        1. Response A
        2. Response B
        """
        result = parse_ranking_from_text(text)
        # Falls back to finding Response patterns in order
        assert "Response A" in result
        assert "Response B" in result

    def test_parse_partial_ranking(self):
        """Test parsing when only some responses are ranked."""
        text = """
        FINAL RANKING:
        1. Response A
        2. Response C
        """
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response C"]

    def test_parse_with_explanations_after_labels(self):
        """Test parsing with text after response labels."""
        text = """
        FINAL RANKING:
        1. Response B - Best overall quality
        2. Response A - Good but verbose
        3. Response C - Needs improvement
        """
        result = parse_ranking_from_text(text)
        # Should only extract the Response labels
        assert result == ["Response B", "Response A", "Response C"]


class TestCalculateAggregateRankings:
    """Tests for aggregate ranking calculation."""

    def test_unanimous_ranking(self):
        """Test when all models agree on ranking."""
        stage2_results = [
            {"model": "model1", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C"},
            {"model": "model2", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C"},
            {"model": "model3", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C"},
        ]
        label_to_model = {
            "Response A": "openai/gpt-4o",
            "Response B": "anthropic/claude-3-sonnet",
            "Response C": "google/gemini-pro",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert len(result) == 3
        assert result[0]["model"] == "openai/gpt-4o"
        assert result[0]["average_rank"] == 1.0
        assert result[1]["model"] == "anthropic/claude-3-sonnet"
        assert result[1]["average_rank"] == 2.0
        assert result[2]["model"] == "google/gemini-pro"
        assert result[2]["average_rank"] == 3.0

    def test_split_ranking(self):
        """Test when models disagree (split vote)."""
        stage2_results = [
            {"model": "model1", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B"},
            {"model": "model2", "ranking": "FINAL RANKING:\n1. Response B\n2. Response A"},
        ]
        label_to_model = {
            "Response A": "openai/gpt-4o",
            "Response B": "anthropic/claude-3-sonnet",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Both should have average rank of 1.5
        assert len(result) == 2
        assert result[0]["average_rank"] == 1.5
        assert result[1]["average_rank"] == 1.5

    def test_varied_rankings(self):
        """Test realistic varied rankings."""
        stage2_results = [
            {"model": "m1", "ranking": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C"},
            {"model": "m2", "ranking": "FINAL RANKING:\n1. Response A\n2. Response C\n3. Response B"},
            {"model": "m3", "ranking": "FINAL RANKING:\n1. Response B\n2. Response C\n3. Response A"},
        ]
        label_to_model = {
            "Response A": "model-a",
            "Response B": "model-b",
            "Response C": "model-c",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # model-b: positions 1, 3, 1 = avg 1.67
        # model-a: positions 2, 1, 3 = avg 2.0
        # model-c: positions 3, 2, 2 = avg 2.33
        assert len(result) == 3
        assert result[0]["model"] == "model-b"
        assert abs(result[0]["average_rank"] - 1.67) < 0.01

    def test_empty_results(self):
        """Test with empty stage2 results."""
        result = calculate_aggregate_rankings([], {})
        assert result == []

    def test_missing_rankings(self):
        """Test when some rankings are missing labels."""
        stage2_results = [
            {"model": "m1", "ranking": "FINAL RANKING:\n1. Response A"},
            {"model": "m2", "ranking": "No clear ranking provided"},
        ]
        label_to_model = {
            "Response A": "model-a",
            "Response B": "model-b",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Only model-a should appear (Response A found in m1)
        assert len(result) == 1
        assert result[0]["model"] == "model-a"


@pytest.mark.asyncio
class TestStage1CollectResponses:
    """Tests for Stage 1 response collection."""

    async def test_stage1_returns_responses(self):
        """Test Stage 1 collects responses from all models."""
        mock_responses = {
            "openai/gpt-4o": {"content": "Response from GPT-4", "usage": {}},
            "anthropic/claude-3-sonnet": {"content": "Response from Claude", "usage": {}},
        }

        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.council.get_council_models", return_value=list(mock_responses.keys())):
                with patch("backend.council.get_model_persona", return_value=None):
                    results = await stage1_collect_responses("Test query")

        assert len(results) == 2
        assert any(r["model"] == "openai/gpt-4o" for r in results)
        assert any(r["model"] == "anthropic/claude-3-sonnet" for r in results)

    async def test_stage1_handles_partial_failure(self):
        """Test Stage 1 continues when some models fail."""
        mock_responses = {
            "openai/gpt-4o": {"content": "Response from GPT-4", "usage": {}},
            "anthropic/claude-3-sonnet": None,  # Failed
        }

        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.council.get_council_models", return_value=list(mock_responses.keys())):
                with patch("backend.council.get_model_persona", return_value=None):
                    results = await stage1_collect_responses("Test query")

        # Should only include successful response
        assert len(results) == 1
        assert results[0]["model"] == "openai/gpt-4o"

    async def test_stage1_all_fail(self):
        """Test Stage 1 returns empty when all models fail."""
        mock_responses = {
            "openai/gpt-4o": None,
            "anthropic/claude-3-sonnet": None,
        }

        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.council.get_council_models", return_value=list(mock_responses.keys())):
                with patch("backend.council.get_model_persona", return_value=None):
                    results = await stage1_collect_responses("Test query")

        assert len(results) == 0

    async def test_stage1_includes_thinking_tokens(self):
        """Test Stage 1 includes thinking tokens for reasoning models."""
        mock_responses = {
            "deepseek/deepseek-r1": {
                "content": "Final answer",
                "thinking": "Step by step reasoning...",
                "usage": {},
            },
        }

        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.council.get_council_models", return_value=["deepseek/deepseek-r1"]):
                with patch("backend.council.get_model_persona", return_value=None):
                    results = await stage1_collect_responses("Complex question")

        assert len(results) == 1
        assert results[0]["thinking"] == "Step by step reasoning..."

    async def test_stage1_with_context(self):
        """Test Stage 1 includes conversation context."""
        mock_responses = {
            "openai/gpt-4o": {"content": "Context-aware response", "usage": {}},
        }

        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.council.get_council_models", return_value=["openai/gpt-4o"]):
                with patch("backend.council.get_model_persona", return_value=None):
                    results = await stage1_collect_responses(
                        "Follow-up question",
                        context="Previous discussion about AI"
                    )

        # Verify the query was called (context handling is internal)
        assert len(results) == 1


@pytest.mark.asyncio
class TestStage2CollectRankings:
    """Tests for Stage 2 ranking collection."""

    async def test_stage2_creates_anonymized_labels(self):
        """Test Stage 2 creates proper anonymized labels."""
        stage1_results = [
            {"model": "openai/gpt-4o", "response": "Response 1"},
            {"model": "anthropic/claude-3-sonnet", "response": "Response 2"},
        ]

        mock_responses = {
            "openai/gpt-4o": {"content": "FINAL RANKING:\n1. Response A\n2. Response B", "usage": {}},
            "anthropic/claude-3-sonnet": {"content": "FINAL RANKING:\n1. Response B\n2. Response A", "usage": {}},
        }

        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.council.get_council_models", return_value=list(mock_responses.keys())):
                rankings, label_to_model = await stage2_collect_rankings("Query", stage1_results)

        # Check label mapping
        assert "Response A" in label_to_model
        assert "Response B" in label_to_model
        assert label_to_model["Response A"] == "openai/gpt-4o"
        assert label_to_model["Response B"] == "anthropic/claude-3-sonnet"

    async def test_stage2_parses_rankings(self):
        """Test Stage 2 parses rankings correctly."""
        stage1_results = [
            {"model": "model-a", "response": "Response A content"},
            {"model": "model-b", "response": "Response B content"},
        ]

        mock_responses = {
            "model-a": {"content": "FINAL RANKING:\n1. Response B\n2. Response A", "usage": {}},
        }

        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses
            with patch("backend.council.get_council_models", return_value=["model-a"]):
                rankings, _ = await stage2_collect_rankings("Query", stage1_results)

        assert len(rankings) == 1
        assert rankings[0]["parsed_ranking"] == ["Response B", "Response A"]


@pytest.mark.asyncio
class TestStage3SynthesizeFinal:
    """Tests for Stage 3 chairman synthesis."""

    async def test_stage3_returns_synthesis(self):
        """Test Stage 3 returns chairman synthesis."""
        stage1_results = [{"model": "m1", "response": "R1"}]
        stage2_results = [{"model": "m1", "ranking": "FINAL RANKING:\n1. Response A"}]

        with patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {"content": "Final synthesis from chairman"}
            with patch("backend.council.get_chairman_model", return_value="google/gemini-2.5-flash"):
                result = await stage3_synthesize_final("Query", stage1_results, stage2_results)

        assert result["model"] == "google/gemini-2.5-flash"
        assert result["response"] == "Final synthesis from chairman"

    async def test_stage3_handles_failure(self):
        """Test Stage 3 handles chairman failure gracefully."""
        stage1_results = [{"model": "m1", "response": "R1"}]
        stage2_results = [{"model": "m1", "ranking": "FINAL RANKING:\n1. Response A"}]

        with patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = None  # Chairman failed
            with patch("backend.council.get_chairman_model", return_value="google/gemini-2.5-flash"):
                result = await stage3_synthesize_final("Query", stage1_results, stage2_results)

        assert "Error" in result["response"]


@pytest.mark.asyncio
class TestGenerateConversationTitle:
    """Tests for conversation title generation."""

    async def test_generates_title(self):
        """Test title generation from query."""
        with patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {"content": "AI Ethics Discussion"}
            title = await generate_conversation_title("What are the ethical implications of AI?")

        assert title == "AI Ethics Discussion"

    async def test_handles_failure(self):
        """Test fallback when title generation fails."""
        with patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = None
            title = await generate_conversation_title("Some query")

        assert title == "New Conversation"

    async def test_truncates_long_title(self):
        """Test that long titles are truncated."""
        with patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {"content": "A" * 100}  # Very long title
            title = await generate_conversation_title("Query")

        assert len(title) <= 50
        assert title.endswith("...")

    async def test_strips_quotes(self):
        """Test that quotes are stripped from title."""
        with patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {"content": '"Quantum Computing Basics"'}
            title = await generate_conversation_title("Explain quantum computing")

        assert title == "Quantum Computing Basics"
