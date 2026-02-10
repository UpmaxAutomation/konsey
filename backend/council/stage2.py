"""Stage 2: Anonymized peer ranking of responses."""

import logging
import uuid
from typing import List, Dict, Any, Tuple, Optional

from .parsing import parse_ranking_from_text

logger = logging.getLogger(__name__)


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    web_context: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        web_context: Optional web context for grounding
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    from ..config import get_council_models
    from ..openrouter import query_models_parallel

    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    if web_context:
        ranking_prompt = f"{web_context}\n\n---\n\n{ranking_prompt}"

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get user-specific council models if available
    if user_id and db:
        from ..database import crud as db_crud
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.council_models:
            council_models = settings.council_models
        else:
            council_models = get_council_models()
    else:
        council_models = get_council_models()

    # Get rankings from all council models in parallel (with user-specific API keys)
    responses = await query_models_parallel(council_models, messages, user_id=user_id, db=db)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model
