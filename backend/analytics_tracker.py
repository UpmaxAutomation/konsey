"""Helper to track analytics after council queries."""

from typing import List, Dict, Any, Optional
from . import analytics
from .config import get_council_models, get_chairman_model


def track_council_query(
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    stage3_result: Dict[str, Any],
    aggregate_rankings: List[Dict[str, Any]]
):
    """
    Track analytics for a completed council query.

    Extracts usage data from the results and records to analytics system.
    """
    try:
        tokens_used = {}
        response_times = {}
        total_cost = 0.0

        # Helper to extract usage from a result
        def extract_usage(result: Dict[str, Any], model_key: str = 'model'):
            model = result.get(model_key)
            if not model:
                return

            # Check for usage in response or response_data
            usage = None
            if 'usage' in result:
                usage = result['usage']
            elif 'response_data' in result and 'usage' in result['response_data']:
                usage = result['response_data']['usage']
            elif 'response' in result and isinstance(result['response'], dict) and 'usage' in result['response']:
                usage = result['response']['usage']

            if usage:
                input_tok = usage.get('input_tokens', 0)
                output_tok = usage.get('output_tokens', 0)
                cost = usage.get('cost', 0.0)

                if model in tokens_used:
                    tokens_used[model] += input_tok + output_tok
                else:
                    tokens_used[model] = input_tok + output_tok

                nonlocal total_cost
                total_cost += cost

        # Extract from stage1
        for result in stage1_results:
            extract_usage(result)

        # Extract from stage2
        for result in stage2_results:
            extract_usage(result)

        # Extract from stage3
        chairman = get_chairman_model()
        extract_usage(stage3_result)

        # Record to analytics
        analytics.record_query(
            models=get_council_models(),
            chairman=chairman,
            tokens_used=tokens_used,
            cost=total_cost,
            response_times=response_times,  # We'll populate this later if needed
            aggregate_rankings=aggregate_rankings
        )
    except Exception as e:
        # Don't fail the request if analytics fails
        print(f"Analytics tracking error: {e}")
