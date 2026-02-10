"""CRUD operations for tags and card-tag associations."""

import uuid
from typing import Optional, List

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Tag, CardTag


# ──────────────────────────────────────────────
# Tag operations
# ──────────────────────────────────────────────

async def list_user_tags(
    db: AsyncSession,
    user_id: uuid.UUID
) -> List[Tag]:
    """Get all tags for a user, ordered by name."""
    result = await db.execute(
        select(Tag)
        .where(Tag.user_id == user_id)
        .order_by(Tag.name)
    )
    return list(result.scalars().all())


async def create_tag(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    color: str = "#4a90e2",
    collection: Optional[str] = None
) -> Tag:
    """Create a new tag for a user."""
    tag = Tag(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        color=color,
        collection=collection,
    )
    db.add(tag)
    await db.flush()
    return tag


async def get_tag_by_id(
    db: AsyncSession,
    tag_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Tag]:
    """Get a single tag by ID with user ownership check."""
    result = await db.execute(
        select(Tag)
        .where(Tag.id == tag_id, Tag.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_tag(
    db: AsyncSession,
    tag_id: uuid.UUID,
    user_id: uuid.UUID,
    **kwargs
) -> Optional[Tag]:
    """Update tag fields."""
    allowed_fields = {"name", "color", "collection"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        return await get_tag_by_id(db, tag_id, user_id)

    await db.execute(
        update(Tag)
        .where(Tag.id == tag_id, Tag.user_id == user_id)
        .values(**update_data)
    )
    return await get_tag_by_id(db, tag_id, user_id)


async def delete_tag(
    db: AsyncSession,
    tag_id: uuid.UUID,
    user_id: uuid.UUID
) -> bool:
    """Delete a tag and all its card associations."""
    result = await db.execute(
        delete(Tag)
        .where(Tag.id == tag_id, Tag.user_id == user_id)
    )
    return result.rowcount > 0


# ──────────────────────────────────────────────
# Card-Tag association operations
# ──────────────────────────────────────────────

async def add_card_tag(
    db: AsyncSession,
    card_id: uuid.UUID,
    tag_id: uuid.UUID
) -> CardTag:
    """Add a tag to a card. Idempotent (ignores if already exists)."""
    result = await db.execute(
        select(CardTag)
        .where(CardTag.card_id == card_id, CardTag.tag_id == tag_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    card_tag = CardTag(card_id=card_id, tag_id=tag_id)
    db.add(card_tag)
    await db.flush()
    return card_tag


async def remove_card_tag(
    db: AsyncSession,
    card_id: uuid.UUID,
    tag_id: uuid.UUID
) -> bool:
    """Remove a tag from a card."""
    result = await db.execute(
        delete(CardTag)
        .where(CardTag.card_id == card_id, CardTag.tag_id == tag_id)
    )
    return result.rowcount > 0


async def get_card_tags(
    db: AsyncSession,
    card_id: uuid.UUID
) -> List[Tag]:
    """Get all tags for a card."""
    result = await db.execute(
        select(Tag)
        .join(CardTag, CardTag.tag_id == Tag.id)
        .where(CardTag.card_id == card_id)
        .order_by(Tag.name)
    )
    return list(result.scalars().all())
