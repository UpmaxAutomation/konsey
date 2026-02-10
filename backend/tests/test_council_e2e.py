"""End-to-end tests for the council deliberation flow."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.council import (
    run_full_council,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
)


class TestFullCouncilFlow:
    """End-to-end tests for the complete council deliberation."""

    @pytest.fixture
    def mock_models(self):
        """Mock council models."""
        return ["openai/gpt-4o", "anthropic/claude-sonnet-4", "google/gemini-2.5-flash"]

    @pytest.fixture
    def mock_stage1_responses(self, mock_models):
        """Mock responses from Stage 1."""
        return {
            "openai/gpt-4o": {
                "content": "Python is a high-level programming language known for its readability and versatility.",
                "usage": {"input_tokens": 50, "output_tokens": 100}
            },
            "anthropic/claude-sonnet-4": {
                "content": "Python is an interpreted, object-oriented language with dynamic typing and garbage collection.",
                "usage": {"input_tokens": 45, "output_tokens": 90}
            },
            "google/gemini-2.5-flash": {
                "content": "Python is a popular general-purpose language used in web development, data science, and AI.",
                "usage": {"input_tokens": 55, "output_tokens": 85}
            },
        }

    @pytest.fixture
    def mock_stage2_responses(self, mock_models):
        """Mock ranking responses from Stage 2."""
        return {
            "openai/gpt-4o": {
                "content": """
                Response A provides a good overview but is brief.
                Response B gives technical details about the language.
                Response C highlights practical applications.

                FINAL RANKING:
                1. Response B
                2. Response C
                3. Response A
                """,
                "usage": {"input_tokens": 200, "output_tokens": 150}
            },
            "anthropic/claude-sonnet-4": {
                "content": """
                All responses are accurate.
                Response A is accessible for beginners.
                Response B is more technical.
                Response C is application-focused.

                FINAL RANKING:
                1. Response C
                2. Response A
                3. Response B
                """,
                "usage": {"input_tokens": 210, "output_tokens": 140}
            },
            "google/gemini-2.5-flash": {
                "content": """
                Each response has merits.

                FINAL RANKING:
                1. Response B
                2. Response A
                3. Response C
                """,
                "usage": {"input_tokens": 190, "output_tokens": 130}
            },
        }

    @pytest.fixture
    def mock_stage3_response(self):
        """Mock synthesis from chairman."""
        return {
            "content": """
            Based on the council's responses and peer evaluations:

            Python is an interpreted, object-oriented programming language known for:
            - High readability and clean syntax
            - Dynamic typing and garbage collection
            - Versatility across domains including web development, data science, and AI

            The council consensus highlights Python's accessibility for beginners while
            maintaining power for advanced applications.
            """,
            "usage": {"input_tokens": 500, "output_tokens": 200}
        }

    @pytest.mark.asyncio
    async def test_full_council_flow_success(
        self, mock_models, mock_stage1_responses, mock_stage2_responses, mock_stage3_response
    ):
        """Test complete council flow from query to synthesis."""
        query = "What is Python?"

        # Track call order
        call_order = []

        async def mock_parallel_stage1(models, messages_by_model, **kwargs):
            call_order.append("stage1")
            return mock_stage1_responses

        async def mock_parallel_stage2(models, messages_by_model, **kwargs):
            call_order.append("stage2")
            return mock_stage2_responses

        async def mock_query_model(model, messages, **kwargs):
            call_order.append("stage3")
            return mock_stage3_response

        with patch("backend.council.get_council_models", return_value=mock_models), \
             patch("backend.council.get_chairman_model", return_value="google/gemini-2.5-flash"), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel, \
             patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:

            # Set up different responses for Stage 1 and Stage 2
            mock_parallel.side_effect = [mock_stage1_responses, mock_stage2_responses]
            mock_query.return_value = mock_stage3_response

            result = await run_full_council(query)

            # Verify all stages executed
            assert "stage1" in result
            assert "stage2" in result
            assert "stage3" in result

            # Verify Stage 1 results
            assert len(result["stage1"]) == 3
            assert all("model" in r and "response" in r for r in result["stage1"])

            # Verify Stage 2 results
            assert len(result["stage2"]) == 3
            assert all("parsed_ranking" in r for r in result["stage2"])

            # Verify Stage 3 result
            assert "model" in result["stage3"]
            assert "response" in result["stage3"]
            assert "Python" in result["stage3"]["response"]

    @pytest.mark.asyncio
    async def test_anonymization_in_stage2(self, mock_models, mock_stage1_responses, mock_stage2_responses):
        """Test that Stage 2 receives anonymized responses."""
        captured_messages = {}

        async def capture_stage2_messages(models, messages_by_model, **kwargs):
            captured_messages.update(messages_by_model)
            return mock_stage2_responses

        with patch("backend.council.get_council_models", return_value=mock_models), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:

            # First call returns Stage 1 responses
            mock_parallel.side_effect = [mock_stage1_responses, mock_stage2_responses]

            # Collect Stage 1 first
            stage1_results = await stage1_collect_responses("What is Python?")

            # Now collect Stage 2
            mock_parallel.side_effect = [capture_stage2_messages]
            rankings, label_to_model = await stage2_collect_rankings("What is Python?", stage1_results)

            # Verify anonymization - messages should contain "Response A", "Response B", etc.
            # not model names
            for model, messages in captured_messages.items():
                user_message = messages[0]["content"]
                assert "Response A" in user_message
                assert "Response B" in user_message
                assert "Response C" in user_message
                # Model names should NOT be in the anonymized prompts
                assert "openai/gpt-4o" not in user_message
                assert "anthropic/claude-sonnet-4" not in user_message

    @pytest.mark.asyncio
    async def test_label_to_model_mapping(self, mock_models, mock_stage1_responses, mock_stage2_responses):
        """Test that label_to_model mapping is correct."""
        with patch("backend.council.get_council_models", return_value=mock_models), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:

            mock_parallel.side_effect = [mock_stage1_responses, mock_stage2_responses]

            # Collect Stage 1
            stage1_results = await stage1_collect_responses("What is Python?")

            # Collect Stage 2
            rankings, label_to_model = await stage2_collect_rankings("What is Python?", stage1_results)

            # Verify mapping
            assert len(label_to_model) == 3
            assert "Response A" in label_to_model
            assert "Response B" in label_to_model
            assert "Response C" in label_to_model

            # Labels should map to actual model names
            model_values = list(label_to_model.values())
            for model in mock_models:
                assert model in model_values

    @pytest.mark.asyncio
    async def test_aggregate_rankings_calculation(self, mock_models):
        """Test that aggregate rankings are calculated correctly."""
        stage2_results = [
            {
                "model": "openai/gpt-4o",
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response C\n3. Response A",
                "parsed_ranking": ["Response B", "Response C", "Response A"]
            },
            {
                "model": "anthropic/claude-sonnet-4",
                "ranking": "FINAL RANKING:\n1. Response C\n2. Response A\n3. Response B",
                "parsed_ranking": ["Response C", "Response A", "Response B"]
            },
            {
                "model": "google/gemini-2.5-flash",
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C",
                "parsed_ranking": ["Response B", "Response A", "Response C"]
            },
        ]

        label_to_model = {
            "Response A": "openai/gpt-4o",
            "Response B": "anthropic/claude-sonnet-4",
            "Response C": "google/gemini-2.5-flash",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Verify all models are ranked
        assert len(result) == 3

        # Check structure
        for r in result:
            assert "model" in r
            assert "average_rank" in r
            assert "rankings_count" in r

        # Response B got 1st twice and 3rd once = avg (1+3+1)/3 = 1.67
        # Response C got 2nd, 1st, 3rd = avg (2+1+3)/3 = 2.0
        # Response A got 3rd, 2nd, 2nd = avg (3+2+2)/3 = 2.33
        # So order should be: claude-sonnet-4 (B), gemini (C), gpt-4o (A)
        assert result[0]["model"] == "anthropic/claude-sonnet-4"  # Response B, avg 1.67
        assert result[1]["model"] == "google/gemini-2.5-flash"    # Response C, avg 2.0
        assert result[2]["model"] == "openai/gpt-4o"              # Response A, avg 2.33


class TestGracefulDegradation:
    """Tests for graceful handling of failures."""

    @pytest.fixture
    def mock_models(self):
        return ["model-a", "model-b", "model-c", "model-d", "model-e"]

    @pytest.mark.asyncio
    async def test_one_model_fails_in_stage1(self, mock_models):
        """Test that Stage 1 continues when 1 of 5 models fails."""
        mock_responses = {
            "model-a": {"content": "Response A"},
            "model-b": None,  # Failed
            "model-c": {"content": "Response C"},
            "model-d": {"content": "Response D"},
            "model-e": {"content": "Response E"},
        }

        with patch("backend.council.get_council_models", return_value=mock_models), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:

            mock_parallel.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            # Should have 4 responses (model-b failed)
            assert len(result) == 4
            models = [r["model"] for r in result]
            assert "model-b" not in models

    @pytest.mark.asyncio
    async def test_majority_models_fail_in_stage1(self, mock_models):
        """Test that Stage 1 continues with minimum viable responses."""
        mock_responses = {
            "model-a": None,
            "model-b": None,
            "model-c": None,
            "model-d": {"content": "Response D"},
            "model-e": {"content": "Response E"},
        }

        with patch("backend.council.get_council_models", return_value=mock_models), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:

            mock_parallel.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            # Should have 2 responses
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_all_models_fail_in_stage1(self, mock_models):
        """Test that Stage 1 returns empty list when all fail."""
        mock_responses = {model: None for model in mock_models}

        with patch("backend.council.get_council_models", return_value=mock_models), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:

            mock_parallel.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            assert result == []

    @pytest.mark.asyncio
    async def test_stage2_ranking_parse_failure(self):
        """Test fallback when Stage 2 rankings don't parse cleanly."""
        stage2_responses = {
            "model-a": {"content": "I think Response B is best, then A, then C."},  # No FINAL RANKING header
            "model-b": {"content": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C"},
        }

        stage1_results = [
            {"model": "resp-a", "response": "Response A content"},
            {"model": "resp-b", "response": "Response B content"},
            {"model": "resp-c", "response": "Response C content"},
        ]

        with patch("backend.council.get_council_models", return_value=["model-a", "model-b"]), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:

            mock_parallel.return_value = stage2_responses

            rankings, label_to_model = await stage2_collect_rankings("Query", stage1_results)

            # Both should produce rankings (fallback pattern matching for model-a)
            assert len(rankings) == 2

            # model-b should have clean parse
            model_b_ranking = next(r for r in rankings if r["model"] == "model-b")
            assert model_b_ranking["parsed_ranking"] == ["Response A", "Response B", "Response C"]

            # model-a should use fallback parsing (finding Response mentions)
            model_a_ranking = next(r for r in rankings if r["model"] == "model-a")
            assert "Response B" in model_a_ranking["parsed_ranking"]

    @pytest.mark.asyncio
    async def test_chairman_failure_returns_error(self):
        """Test that chairman failure produces error response."""
        stage1_results = [{"model": "m1", "response": "R1"}]
        stage2_results = [{"model": "m1", "ranking": "...", "parsed_ranking": ["Response A"]}]

        with patch("backend.council.get_chairman_model", return_value="chairman-model"), \
             patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:

            mock_query.return_value = None  # Chairman failed

            result = await stage3_synthesize_final("Query", stage1_results, stage2_results)

            assert "Error" in result["response"]


class TestReasoningModelSupport:
    """Tests for reasoning model thinking token extraction."""

    @pytest.mark.asyncio
    async def test_thinking_tokens_included_in_stage1(self):
        """Test that thinking tokens from reasoning models are included."""
        mock_responses = {
            "openai/o1": {
                "content": "The answer is 42.",
                "thinking": "Let me think step by step... First I consider... Then I realize...",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            },
            "google/gemini-pro": {
                "content": "The answer is also 42.",
                "usage": {"input_tokens": 80, "output_tokens": 40}
            },
        }

        with patch("backend.council.get_council_models", return_value=["openai/o1", "google/gemini-pro"]), \
             patch("backend.council.get_model_persona", return_value=None), \
             patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:

            mock_parallel.return_value = mock_responses

            result = await stage1_collect_responses("What is the meaning of life?")

            # Find the o1 response
            o1_result = next((r for r in result if r["model"] == "openai/o1"), None)
            assert o1_result is not None
            assert o1_result["thinking"] == "Let me think step by step... First I consider... Then I realize..."

            # gemini should not have thinking
            gemini_result = next((r for r in result if r["model"] == "google/gemini-pro"), None)
            assert gemini_result is not None
            assert gemini_result.get("thinking") is None
