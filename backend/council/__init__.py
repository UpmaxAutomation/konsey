"""
LLM Council 3-stage deliberation package.

This package provides the core council functionality:
- Stage 1: Collect individual responses from council models
- Stage 2: Anonymized peer ranking of responses
- Stage 3: Chairman synthesis of final response

Usage:
    from backend.council import run_full_council, run_full_council_stream

    # Non-streaming
    stage1, stage2, stage3, metadata = await run_full_council(query)

    # Streaming
    async for event in run_full_council_stream(query):
        print(event)
"""

# Stage functions
from .stage1 import stage1_collect_responses
from .stage2 import stage2_collect_rankings
from .stage3 import stage3_synthesize_final

# Parsing and aggregation
from .parsing import parse_ranking_from_text
from .aggregation import calculate_aggregate_rankings

# Context gathering
from .context import gather_context, format_web_context

# Utilities
from .utils import generate_conversation_title

# Main orchestration
from .orchestration import run_full_council, run_full_council_stream

__all__ = [
    # Stage functions
    "stage1_collect_responses",
    "stage2_collect_rankings",
    "stage3_synthesize_final",
    # Parsing and aggregation
    "parse_ranking_from_text",
    "calculate_aggregate_rankings",
    # Context
    "gather_context",
    "format_web_context",
    # Utilities
    "generate_conversation_title",
    # Main orchestration
    "run_full_council",
    "run_full_council_stream",
]
