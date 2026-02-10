"""Stage 1: Collect individual responses from council models."""

import logging
import uuid
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


async def stage1_collect_responses(
    user_query: str,
    context: Optional[str] = None,
    image_content: Optional[List[Dict]] = None,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        context: Optional conversation context from previous exchanges
        image_content: Optional list of image content dicts for vision models
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    from ..config import get_council_models, get_model_persona, supports_vision
    from ..openrouter import query_models_parallel

    # Build the query with context if available
    if context:
        enhanced_query = f"{context}\n\n---\n\nCurrent Question: {user_query}"
    else:
        enhanced_query = user_query

    # Enhance query for image analysis if images are attached
    has_images = bool(image_content and len(image_content) > 0)
    if has_images:
        # Add image analysis guidance if user hasn't explicitly asked about the image
        image_keywords = ['image', 'picture', 'photo', 'screenshot', 'diagram', 'chart', 'graph', 'see', 'look', 'show', 'visual']
        user_query_lower = user_query.lower()
        user_mentions_image = any(kw in user_query_lower for kw in image_keywords)

        if not user_mentions_image:
            # User didn't mention the image, so add context
            enhanced_query = f"""[Image Analysis Context]
The user has attached {len(image_content)} image(s). Please analyze the image(s) as part of your response:
- Describe what you see in the image
- Identify any text, numbers, data, or important elements
- Note any patterns, trends, or notable features
- Connect your observations to the user's question

User Question: {enhanced_query}"""

    # Build messages with persona if assigned
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

    messages_by_model = {}

    for model in council_models:
        persona = get_model_persona(model)

        # Build user content - multimodal for vision models with images
        if image_content and supports_vision(model):
            # Build multimodal content array for vision models
            user_content = [{"type": "text", "text": enhanced_query}]
            for img in image_content:
                if img.get("type") == "image":
                    # Convert to OpenAI-compatible format
                    source = img.get("source", {})
                    if source.get("type") == "base64":
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{source.get('media_type', 'image/png')};base64,{source.get('data', '')}"
                            }
                        })
        else:
            # Plain text content for non-vision models or no images
            user_content = enhanced_query

        if persona:
            # Prepend system message with persona
            messages_by_model[model] = [
                {"role": "system", "content": persona},
                {"role": "user", "content": user_content}
            ]
        else:
            # No persona, just user message
            messages_by_model[model] = [{"role": "user", "content": user_content}]

    # Query all models in parallel (with user-specific API keys)
    responses = await query_models_parallel(council_models, messages_by_model, user_id=user_id, db=db)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            result = {
                "model": model,
                "response": response.get('content', '')
            }
            # Include thinking tokens if available (for reasoning models)
            if 'thinking' in response:
                result['thinking'] = response.get('thinking')
            stage1_results.append(result)

    return stage1_results
