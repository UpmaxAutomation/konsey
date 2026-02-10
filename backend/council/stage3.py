"""Stage 3: Chairman synthesis of final response."""

import logging
import uuid
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    web_context: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        web_context: Optional web context for grounding
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Returns:
        Dict with 'model' and 'response' keys
    """
    from ..config import get_chairman_model
    from ..openrouter import query_model

    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    if web_context:
        chairman_prompt = f"{web_context}\n\n---\n\n{chairman_prompt}"

    messages = [{"role": "user", "content": chairman_prompt}]

    # Get user-specific chairman model if available
    if user_id and db:
        from ..database import crud as db_crud
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.chairman_model:
            chairman = settings.chairman_model
        else:
            chairman = get_chairman_model()
    else:
        chairman = get_chairman_model()

    # Query the chairman model (with user-specific API keys)
    response = await query_model(chairman, messages, user_id=user_id, db=db)

    if response is None:
        # Fallback if chairman fails
        logger.error(f"Chairman model failed: {chairman}. Check API key in Settings -> API Keys.")
        return {
            "model": chairman,
            "response": f"Error: Chairman model ({chairman}) failed to respond. Please check your API key in Settings -> API Keys."
        }

    return {
        "model": chairman,
        "response": response.get('content', '')
    }
