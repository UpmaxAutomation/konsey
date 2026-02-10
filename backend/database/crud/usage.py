"""CRUD operations for usage tracking."""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UsageAnalytics


async def record_usage(
    db: AsyncSession,
    user_id: uuid.UUID,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    direct_api: bool = False
) -> UsageAnalytics:
    """Record a single API request's usage."""
    usage = UsageAnalytics(
        user_id=user_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost,
        request_date=datetime.utcnow()
    )
    db.add(usage)
    await db.flush()
    return usage


async def get_session_usage(
    db: AsyncSession,
    user_id: uuid.UUID,
    since: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get aggregated usage for a user's session.

    Args:
        db: Database session
        user_id: User ID
        since: Only count requests after this time (default: last 24 hours)

    Returns:
        Dict with total_input_tokens, total_output_tokens, total_cost, request_count
    """
    if since is None:
        since = datetime.utcnow() - timedelta(hours=24)

    result = await db.execute(
        select(
            func.coalesce(func.sum(UsageAnalytics.input_tokens), 0).label("total_input"),
            func.coalesce(func.sum(UsageAnalytics.output_tokens), 0).label("total_output"),
            func.coalesce(func.sum(UsageAnalytics.cost), 0.0).label("total_cost"),
            func.count(UsageAnalytics.id).label("request_count")
        )
        .where(UsageAnalytics.user_id == user_id)
        .where(UsageAnalytics.request_date >= since)
    )
    row = result.one()

    return {
        "total_input_tokens": int(row.total_input),
        "total_output_tokens": int(row.total_output),
        "total_cost": float(row.total_cost),
        "request_count": int(row.request_count)
    }


async def get_recent_requests(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    since: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Get recent requests for a user."""
    if since is None:
        since = datetime.utcnow() - timedelta(hours=24)

    result = await db.execute(
        select(UsageAnalytics)
        .where(UsageAnalytics.user_id == user_id)
        .where(UsageAnalytics.request_date >= since)
        .order_by(UsageAnalytics.created_at.desc())
        .limit(limit)
    )

    return [
        {
            "model": u.model,
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "cost": u.cost,
            "timestamp": u.request_date.isoformat()
        }
        for u in result.scalars().all()
    ]


async def reset_session_usage(
    db: AsyncSession,
    user_id: uuid.UUID,
    before: Optional[datetime] = None
) -> int:
    """
    Reset session usage by deleting old records.

    Args:
        db: Database session
        user_id: User ID
        before: Delete records before this time (default: delete all)

    Returns:
        Number of records deleted
    """
    if before:
        result = await db.execute(
            delete(UsageAnalytics)
            .where(UsageAnalytics.user_id == user_id)
            .where(UsageAnalytics.request_date < before)
        )
    else:
        result = await db.execute(
            delete(UsageAnalytics)
            .where(UsageAnalytics.user_id == user_id)
        )

    return result.rowcount


async def get_usage_by_model(
    db: AsyncSession,
    user_id: uuid.UUID,
    since: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Get usage breakdown by model for a user."""
    if since is None:
        since = datetime.utcnow() - timedelta(days=30)

    result = await db.execute(
        select(
            UsageAnalytics.model,
            func.sum(UsageAnalytics.input_tokens).label("total_input"),
            func.sum(UsageAnalytics.output_tokens).label("total_output"),
            func.sum(UsageAnalytics.cost).label("total_cost"),
            func.count(UsageAnalytics.id).label("request_count")
        )
        .where(UsageAnalytics.user_id == user_id)
        .where(UsageAnalytics.request_date >= since)
        .group_by(UsageAnalytics.model)
        .order_by(func.sum(UsageAnalytics.cost).desc())
    )

    return [
        {
            "model": row.model,
            "input_tokens": int(row.total_input or 0),
            "output_tokens": int(row.total_output or 0),
            "cost": float(row.total_cost or 0),
            "request_count": int(row.request_count)
        }
        for row in result.all()
    ]
