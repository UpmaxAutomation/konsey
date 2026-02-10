"""CRUD operations for template ratings."""

import uuid
from typing import Optional, List
from sqlalchemy import select, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import TemplateRating, BoardTemplate, UserFlowTemplate


async def rate_template(
    db: AsyncSession,
    user_id: uuid.UUID,
    template_type: str,
    template_id: uuid.UUID,
    rating: int,
    review: Optional[str] = None,
) -> TemplateRating:
    """Upsert a rating for a template."""
    # Check for existing rating
    existing = await get_user_rating(db, user_id, template_type, template_id)
    if existing:
        existing.rating = rating
        existing.review = review
        await db.flush()
        await db.refresh(existing)
        result_rating = existing
    else:
        new_rating = TemplateRating(
            user_id=user_id,
            template_type=template_type,
            template_id=template_id,
            rating=rating,
            review=review,
        )
        db.add(new_rating)
        await db.flush()
        await db.refresh(new_rating)
        result_rating = new_rating

    # Update avg rating on the template
    await _update_template_avg_rating(db, template_type, template_id)
    return result_rating


async def get_ratings(
    db: AsyncSession,
    template_type: str,
    template_id: uuid.UUID,
    limit: int = 20,
) -> List[TemplateRating]:
    """List ratings/reviews for a template."""
    result = await db.execute(
        select(TemplateRating)
        .where(TemplateRating.template_type == template_type, TemplateRating.template_id == template_id)
        .order_by(desc(TemplateRating.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_user_rating(
    db: AsyncSession,
    user_id: uuid.UUID,
    template_type: str,
    template_id: uuid.UUID,
) -> Optional[TemplateRating]:
    """Check if a user has rated a template."""
    result = await db.execute(
        select(TemplateRating).where(
            TemplateRating.user_id == user_id,
            TemplateRating.template_type == template_type,
            TemplateRating.template_id == template_id,
        )
    )
    return result.scalar_one_or_none()


async def _update_template_avg_rating(db: AsyncSession, template_type: str, template_id: uuid.UUID):
    """Recalculate and update avg_rating on the template."""
    result = await db.execute(
        select(func.avg(TemplateRating.rating), func.count(TemplateRating.id))
        .where(TemplateRating.template_type == template_type, TemplateRating.template_id == template_id)
    )
    row = result.one()
    avg_val = float(row[0]) if row[0] else 0.0
    count_val = int(row[1]) if row[1] else 0

    if template_type == "board":
        await db.execute(
            update(BoardTemplate)
            .where(BoardTemplate.id == template_id)
            .values(avg_rating=avg_val, rating_count=count_val)
        )
    elif template_type == "workflow":
        await db.execute(
            update(UserFlowTemplate)
            .where(UserFlowTemplate.id == template_id)
            .values(avg_rating=avg_val, rating_count=count_val)
        )
    await db.flush()
