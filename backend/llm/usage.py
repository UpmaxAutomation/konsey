"""Usage and cost tracking for LLM queries."""

import logging
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global token tracking for current session (for anonymous users)
_session_usage = {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost": 0.0,
    "requests": []
}


def reset_session_usage():
    """Reset global session usage tracking (for anonymous users)."""
    global _session_usage
    _session_usage = {
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost": 0.0,
        "requests": []
    }


def get_session_usage():
    """Get global session usage (for anonymous users)."""
    return _session_usage.copy()


async def get_user_session_usage(user_id: uuid.UUID, db: Any) -> dict:
    """Get session usage for a specific user from database."""
    from ..database import crud as db_crud
    return await db_crud.usage.get_session_usage(db, user_id)


async def reset_user_session_usage(user_id: uuid.UUID, db: Any) -> int:
    """Reset session usage for a specific user."""
    from ..database import crud as db_crud
    return await db_crud.usage.reset_session_usage(db, user_id)


async def record_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None,
    direct_api: bool = False
) -> None:
    """
    Record usage - to database for authenticated users, global dict for anonymous.

    Args:
        model: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost: Calculated cost
        user_id: User ID (if authenticated)
        db: Database session (if available)
        direct_api: Whether this was a direct API call
    """
    global _session_usage

    # Always update global for backward compatibility (e.g., API endpoints that use it)
    _session_usage["total_input_tokens"] += input_tokens
    _session_usage["total_output_tokens"] += output_tokens
    _session_usage["total_cost"] += cost
    _session_usage["requests"].append({
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost,
        "direct_api": direct_api
    })

    # Also record to database for authenticated users
    if user_id and db:
        try:
            from ..database import crud as db_crud
            await db_crud.usage.record_usage(
                db,
                user_id,
                model,
                input_tokens,
                output_tokens,
                cost,
                direct_api
            )
        except Exception as e:
            logger.warning(f"Failed to record usage to database: {e}")


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for a model request."""
    from ..config import AVAILABLE_MODELS

    if model not in AVAILABLE_MODELS:
        return 0.0

    pricing = AVAILABLE_MODELS[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input_cost"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_cost"]
    return input_cost + output_cost
