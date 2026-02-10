"""Shared utility functions for council operations."""

import logging
import uuid
from typing import Optional, Any

logger = logging.getLogger(__name__)


async def generate_conversation_title(
    user_query: str,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Returns:
        A short title (3-5 words)
    """
    from ..openrouter import query_model

    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Try multiple models for title generation (fast and cheap options)
    title_models = [
        "google/gemini-2.0-flash-001",
        "google/gemini-2.5-flash",
        "openai/gpt-4o-mini",
        "anthropic/claude-3-5-haiku-20241022"
    ]

    response = None
    for model in title_models:
        try:
            response = await query_model(model, messages, timeout=30.0, user_id=user_id, db=db)
            if response and response.get('content'):
                break
        except Exception as e:
            print(f"Title generation with {model} failed: {e}")
            continue

    if response is None or not response.get('content'):
        # Local fallback: extract first few words from query
        words = user_query.split()[:6]
        fallback_title = ' '.join(words)
        if len(fallback_title) > 40:
            fallback_title = fallback_title[:37] + "..."
        return fallback_title if fallback_title else "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title
