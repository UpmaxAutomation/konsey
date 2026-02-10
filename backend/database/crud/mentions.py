"""CRUD operations for card mentions (backlinks)."""

import uuid
from typing import List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CardMention, Card


async def sync_mentions(
    db: AsyncSession,
    card_id: uuid.UUID,
    board_id: uuid.UUID,
    mentioned_card_ids: List[uuid.UUID],
) -> None:
    """Replace all outgoing mentions from a card with a new set."""
    # Delete existing mentions from this source card
    await db.execute(
        delete(CardMention).where(CardMention.source_card_id == card_id)
    )

    # Insert new mentions
    for target_id in mentioned_card_ids:
        if target_id == card_id:
            continue  # skip self-mentions
        mention = CardMention(
            source_card_id=card_id,
            target_card_id=target_id,
            board_id=board_id,
        )
        db.add(mention)

    await db.flush()


async def get_backlinks(
    db: AsyncSession,
    card_id: uuid.UUID,
) -> List[dict]:
    """Get all cards that mention the given card (backlinks)."""
    result = await db.execute(
        select(
            CardMention.source_card_id,
            Card.title,
            Card.card_type,
        )
        .join(Card, Card.id == CardMention.source_card_id)
        .where(CardMention.target_card_id == card_id)
    )
    return [
        {"id": str(row.source_card_id), "title": row.title, "card_type": row.card_type}
        for row in result.all()
    ]


async def get_mentions(
    db: AsyncSession,
    card_id: uuid.UUID,
) -> List[dict]:
    """Get all cards mentioned by the given card (forward links)."""
    result = await db.execute(
        select(
            CardMention.target_card_id,
            Card.title,
            Card.card_type,
        )
        .join(Card, Card.id == CardMention.target_card_id)
        .where(CardMention.source_card_id == card_id)
    )
    return [
        {"id": str(row.target_card_id), "title": row.title, "card_type": row.card_type}
        for row in result.all()
    ]


async def get_board_mention_graph(
    db: AsyncSession,
    board_id: uuid.UUID,
) -> List[dict]:
    """Get all mention edges for a board."""
    result = await db.execute(
        select(CardMention).where(CardMention.board_id == board_id)
    )
    return [
        {
            "source_card_id": str(m.source_card_id),
            "target_card_id": str(m.target_card_id),
            "board_id": str(m.board_id),
        }
        for m in result.scalars().all()
    ]
