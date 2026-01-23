"""Tests for backend/council.py module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.council import (
    parse_ranking_from_text,
    calculate_aggregate_rankings,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
)


class TestParseRankingFromText:
    """Tests for parse_ranking_from_text function."""

    def test_standard_format_numbered_list(self):
        """Test parsing standard numbered list format."""
        text = """
        Response A is good but lacks detail.
        Response B provides comprehensive coverage.
        Response C is accurate but brief.

        FINAL RANKING:
        1. Response B
        2. Response A
        3. Response C
        """
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A", "Response C"]

    def test_no_spaces_after_number(self):
        """Test parsing when there's no space after the period."""
        text = """FINAL RANKING:
        1.Response A
        2.Response B
        3.Response C"""
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_extra_whitespace(self):
        """Test parsing with extra whitespace."""
        text = """
        FINAL RANKING:
        1.   Response C
        2.   Response A
        3.   Response B
        """
        result = parse_ranking_from_text(text)
        assert result == ["Response C", "Response A", "Response B"]

    def test_without_final_ranking_header(self):
        """Test fallback when FINAL RANKING header is missing."""
        text = """
        After careful analysis:
        Response B is the best.
        Response A comes second.
        Response C is third.
        """
        result = parse_ranking_from_text(text)
        # Should find Response patterns in order
        assert result == ["Response B", "Response A", "Response C"]

    def test_empty_text(self):
        """Test with empty text."""
        result = parse_ranking_from_text("")
        assert result == []

    def test_no_responses_mentioned(self):
        """Test with text that has no Response mentions."""
        text = "This is a general evaluation without specific response labels."
        result = parse_ranking_from_text(text)
        assert result == []

    def test_mixed_case_final_ranking(self):
        """Test that FINAL RANKING must be uppercase (per current implementation)."""
        text = """
        Final Ranking:
        1. Response A
        2. Response B
        """
        result = parse_ranking_from_text(text)
        # Since the header check is exact, this falls back to pattern matching
        assert "Response A" in result
        assert "Response B" in result

    def test_multiple_response_mentions_before_ranking(self):
        """Test that responses mentioned before FINAL RANKING don't affect result."""
        text = """
        Response A has some issues.
        Response B is better than Response A.
        Response C is solid.

        FINAL RANKING:
        1. Response B
        2. Response C
        3. Response A
        """
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response C", "Response A"]

    def test_single_response(self):
        """Test with only one response."""
        text = """FINAL RANKING:
        1. Response A"""
        result = parse_ranking_from_text(text)
        assert result == ["Response A"]

    def test_many_responses(self):
        """Test with many responses (A through F)."""
        text = """FINAL RANKING:
        1. Response D
        2. Response A
        3. Response F
        4. Response B
        5. Response E
        6. Response C"""
        result = parse_ranking_from_text(text)
        assert result == ["Response D", "Response A", "Response F", "Response B", "Response E", "Response C"]


class TestCalculateAggregateRankings:
    """Tests for calculate_aggregate_rankings function."""

    def test_unanimous_ranking(self, sample_label_to_model):
        """Test when all models agree on ranking."""
        stage2_results = [
            {"model": "model1", "ranking": "FINAL RANKING:\n1. Response C\n2. Response B\n3. Response A"},
            {"model": "model2", "ranking": "FINAL RANKING:\n1. Response C\n2. Response B\n3. Response A"},
            {"model": "model3", "ranking": "FINAL RANKING:\n1. Response C\n2. Response B\n3. Response A"},
        ]
        result = calculate_aggregate_rankings(stage2_results, sample_label_to_model)

        # Response C should be ranked first (avg position 1.0)
        assert result[0]["model"] == "google/gemini-pro"
        assert result[0]["average_rank"] == 1.0
        # Response B second (avg position 2.0)
        assert result[1]["model"] == "anthropic/claude-3"
        assert result[1]["average_rank"] == 2.0
        # Response A third (avg position 3.0)
        assert result[2]["model"] == "openai/gpt-4"
        assert result[2]["average_rank"] == 3.0

    def test_mixed_rankings(self, sample_stage2_results, sample_label_to_model):
        """Test with different rankings from each model."""
        result = calculate_aggregate_rankings(sample_stage2_results, sample_label_to_model)

        # All models should be present
        model_names = [r["model"] for r in result]
        assert "openai/gpt-4" in model_names
        assert "anthropic/claude-3" in model_names
        assert "google/gemini-pro" in model_names

        # Check that rankings_count is correct (3 models voted)
        for r in result:
            assert r["rankings_count"] == 3

    def test_empty_stage2_results(self, sample_label_to_model):
        """Test with no rankings."""
        result = calculate_aggregate_rankings([], sample_label_to_model)
        assert result == []

    def test_partial_rankings(self, sample_label_to_model):
        """Test when some models don't rank all responses."""
        stage2_results = [
            {"model": "model1", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B"},
            {"model": "model2", "ranking": "FINAL RANKING:\n1. Response C\n2. Response A\n3. Response B"},
        ]
        result = calculate_aggregate_rankings(stage2_results, sample_label_to_model)

        # Response A should appear in both rankings
        response_a = next((r for r in result if r["model"] == "openai/gpt-4"), None)
        assert response_a is not None
        assert response_a["rankings_count"] == 2  # Ranked by both models

        # Response C only in one ranking
        response_c = next((r for r in result if r["model"] == "google/gemini-pro"), None)
        assert response_c is not None
        assert response_c["rankings_count"] == 1

    def test_unknown_response_labels_ignored(self, sample_label_to_model):
        """Test that unknown response labels are ignored."""
        stage2_results = [
            {"model": "model1", "ranking": "FINAL RANKING:\n1. Response Z\n2. Response A"},
        ]
        result = calculate_aggregate_rankings(stage2_results, sample_label_to_model)

        # Only Response A should be in results
        assert len(result) == 1
        assert result[0]["model"] == "openai/gpt-4"

    def test_sorting_by_average_rank(self):
        """Test that results are sorted by average rank (lower is better)."""
        label_to_model = {
            "Response A": "model-a",
            "Response B": "model-b",
        }
        stage2_results = [
            {"model": "ranker1", "ranking": "FINAL RANKING:\n1. Response B\n2. Response A"},
            {"model": "ranker2", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B"},
            {"model": "ranker3", "ranking": "FINAL RANKING:\n1. Response B\n2. Response A"},
        ]
        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # model-b should be first (avg rank 1.33) vs model-a (avg rank 1.67)
        assert result[0]["model"] == "model-b"
        assert result[1]["model"] == "model-a"


class TestStage1CollectResponses:
    """Tests for stage1_collect_responses async function."""

    @pytest.mark.asyncio
    async def test_successful_responses(self, mock_council_models):
        """Test collecting responses from all models successfully."""
        mock_responses = {
            "openai/gpt-4": {"content": "GPT-4 answer"},
            "anthropic/claude-3": {"content": "Claude answer"},
            "google/gemini-pro": {"content": "Gemini answer"},
        }

        with patch("backend.council.get_council_models", return_value=mock_council_models), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await stage1_collect_responses("What is Python?")

            assert len(result) == 3
            assert all("model" in r and "response" in r for r in result)
            models = [r["model"] for r in result]
            assert "openai/gpt-4" in models

    @pytest.mark.asyncio
    async def test_partial_failures(self, mock_council_models):
        """Test when some models fail (return None)."""
        mock_responses = {
            "openai/gpt-4": {"content": "GPT-4 answer"},
            "anthropic/claude-3": None,  # Failed
            "google/gemini-pro": {"content": "Gemini answer"},
        }

        with patch("backend.council.get_council_models", return_value=mock_council_models), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await stage1_collect_responses("What is Python?")

            # Should only have 2 results (Claude failed)
            assert len(result) == 2
            models = [r["model"] for r in result]
            assert "anthropic/claude-3" not in models

    @pytest.mark.asyncio
    async def test_all_failures(self, mock_council_models):
        """Test when all models fail."""
        mock_responses = {
            "openai/gpt-4": None,
            "anthropic/claude-3": None,
            "google/gemini-pro": None,
        }

        with patch("backend.council.get_council_models", return_value=mock_council_models), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await stage1_collect_responses("What is Python?")
            assert result == []

    @pytest.mark.asyncio
    async def test_with_context(self, mock_council_models):
        """Test that context is included in query."""
        mock_responses = {
            "openai/gpt-4": {"content": "Answer with context"},
        }

        with patch("backend.council.get_council_models", return_value=["openai/gpt-4"]), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await stage1_collect_responses("Follow-up question", context="Previous conversation...")

            # Verify query_models_parallel was called
            mock_parallel.assert_called_once()
            # The messages should contain the context
            call_args = mock_parallel.call_args
            messages_by_model = call_args[0][1]
            user_message = messages_by_model["openai/gpt-4"][0]["content"]
            assert "Previous conversation..." in user_message

    @pytest.mark.asyncio
    async def test_thinking_tokens_included(self, mock_council_models):
        """Test that thinking tokens from reasoning models are included."""
        mock_responses = {
            "openai/gpt-4": {"content": "Answer", "thinking": "My reasoning process..."},
        }

        with patch("backend.council.get_council_models", return_value=["openai/gpt-4"]), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            result = await stage1_collect_responses("Complex question")

            assert len(result) == 1
            assert result[0]["thinking"] == "My reasoning process..."


class TestStage2CollectRankings:
    """Tests for stage2_collect_rankings async function."""

    @pytest.mark.asyncio
    async def test_successful_rankings(self, mock_council_models, sample_stage1_results):
        """Test collecting rankings from all models."""
        mock_responses = {
            "openai/gpt-4": {"content": "FINAL RANKING:\n1. Response C\n2. Response B\n3. Response A"},
            "anthropic/claude-3": {"content": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C"},
            "google/gemini-pro": {"content": "FINAL RANKING:\n1. Response A\n2. Response C\n3. Response B"},
        }

        with patch("backend.council.get_council_models", return_value=mock_council_models), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            rankings, label_to_model = await stage2_collect_rankings("What is Python?", sample_stage1_results)

            # Check rankings
            assert len(rankings) == 3
            assert all("parsed_ranking" in r for r in rankings)

            # Check label_to_model mapping
            assert "Response A" in label_to_model
            assert "Response B" in label_to_model
            assert "Response C" in label_to_model
            assert label_to_model["Response A"] == "openai/gpt-4"

    @pytest.mark.asyncio
    async def test_label_generation(self, mock_council_models):
        """Test that labels are generated correctly for varying numbers of responses."""
        stage1_results = [
            {"model": f"model-{i}", "response": f"Response {i}"}
            for i in range(5)
        ]

        mock_responses = {model: {"content": "FINAL RANKING:\n1. Response A"} for model in mock_council_models}

        with patch("backend.council.get_council_models", return_value=mock_council_models), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            rankings, label_to_model = await stage2_collect_rankings("Query", stage1_results)

            # Should have labels A through E
            assert "Response A" in label_to_model
            assert "Response B" in label_to_model
            assert "Response C" in label_to_model
            assert "Response D" in label_to_model
            assert "Response E" in label_to_model

    @pytest.mark.asyncio
    async def test_failed_rankings_excluded(self, mock_council_models, sample_stage1_results):
        """Test that failed ranking attempts are excluded."""
        mock_responses = {
            "openai/gpt-4": {"content": "FINAL RANKING:\n1. Response A"},
            "anthropic/claude-3": None,  # Failed
            "google/gemini-pro": {"content": "FINAL RANKING:\n1. Response B"},
        }

        with patch("backend.council.get_council_models", return_value=mock_council_models), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
            mock_parallel.return_value = mock_responses

            rankings, label_to_model = await stage2_collect_rankings("Query", sample_stage1_results)

            # Only 2 rankings should be present
            assert len(rankings) == 2


class TestStage3SynthesizeFinal:
    """Tests for stage3_synthesize_final async function."""

    @pytest.mark.asyncio
    async def test_successful_synthesis(self, sample_stage1_results, sample_stage2_results):
        """Test successful synthesis by chairman."""
        mock_response = {"content": "This is the synthesized final answer."}

        with patch("backend.council.get_chairman_model", return_value="google/gemini-2.0-flash"), \
             patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_response

            result = await stage3_synthesize_final("What is Python?", sample_stage1_results, sample_stage2_results)

            assert result["model"] == "google/gemini-2.0-flash"
            assert result["response"] == "This is the synthesized final answer."

    @pytest.mark.asyncio
    async def test_chairman_failure(self, sample_stage1_results, sample_stage2_results):
        """Test fallback when chairman fails."""
        with patch("backend.council.get_chairman_model", return_value="google/gemini-2.0-flash"), \
             patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = None  # Chairman failed

            result = await stage3_synthesize_final("What is Python?", sample_stage1_results, sample_stage2_results)

            assert result["model"] == "google/gemini-2.0-flash"
            assert "Error" in result["response"]

    @pytest.mark.asyncio
    async def test_empty_inputs(self):
        """Test with empty stage1 and stage2 results."""
        mock_response = {"content": "No responses to synthesize."}

        with patch("backend.council.get_chairman_model", return_value="google/gemini-2.0-flash"), \
             patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_response

            result = await stage3_synthesize_final("Query", [], [])

            assert result["response"] == "No responses to synthesize."
