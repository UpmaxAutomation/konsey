"""CRUD operations for cross-board linked cards and global card search."""

import uuid
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Board, Card, CardTag


# ──────────────────────────────────────────────
# Linked card operations
# ──────────────────────────────────────────────

async def create_linked_card(
    db: AsyncSession,
    source_card_id: uuid.UUID,
    target_board_id: uuid.UUID,
    position_x: float = 0.0,
    position_y: float = 0.0,
) -> Card:
    """Create a linked_card on target_board that mirrors the source card.

    The linked card copies the source's title, content, and color at creation
    time, and maintains a reference back via source_card_id so that future
    syncs propagate changes from the source.

    Raises:
        ValueError: If the source card does not exist.
    """
    source = await db.execute(
        select(Card).where(Card.id == source_card_id)
    )
    source_card = source.scalar_one_or_none()
    if source_card is None:
        raise ValueError(f"Source card {source_card_id} not found")

    linked = Card(
        id=uuid.uuid4(),
        board_id=target_board_id,
        card_type="linked_card",
        title=source_card.title,
        content=source_card.content,
        color=source_card.color,
        position_x=position_x,
        position_y=position_y,
        width=source_card.width,
        height=source_card.height,
        source_card_id=source_card.id,
        extra={"linked_from_board": str(source_card.board_id)},
    )
    db.add(linked)
    await db.flush()
    return linked


async def clone_card(
    db: AsyncSession,
    source_card_id: uuid.UUID,
    target_board_id: uuid.UUID,
    position_x: float = 0.0,
    position_y: float = 0.0,
) -> Card:
    """Deep copy a card (no link) to the target board.

    Copies title, content, color, extra, and dimensions. The clone has
    card_type 'note' and no source_card_id, so it is fully independent.

    Raises:
        ValueError: If the source card does not exist.
    """
    source = await db.execute(
        select(Card).where(Card.id == source_card_id)
    )
    source_card = source.scalar_one_or_none()
    if source_card is None:
        raise ValueError(f"Source card {source_card_id} not found")

    clone = Card(
        id=uuid.uuid4(),
        board_id=target_board_id,
        card_type="note",
        title=source_card.title,
        content=source_card.content,
        color=source_card.color,
        position_x=position_x,
        position_y=position_y,
        width=source_card.width,
        height=source_card.height,
        extra=dict(source_card.extra) if source_card.extra else {},
    )
    db.add(clone)
    await db.flush()
    return clone


async def unlink_card(
    db: AsyncSession,
    card_id: uuid.UUID,
) -> Optional[Card]:
    """Break the link on a linked card: null out source_card_id, change type to 'note'.

    Returns the updated card, or None if the card was not found.
    """
    await db.execute(
        update(Card)
        .where(Card.id == card_id)
        .values(source_card_id=None, card_type="note")
    )
    result = await db.execute(select(Card).where(Card.id == card_id))
    return result.scalar_one_or_none()


async def sync_linked_cards(
    db: AsyncSession,
    source_card_id: uuid.UUID,
) -> int:
    """Sync all linked instances from the source card (title + content).

    Finds every card whose source_card_id matches and updates their
    title and content to match the current source card values.

    Returns the number of linked cards that were updated.
    """
    source = await db.execute(
        select(Card).where(Card.id == source_card_id)
    )
    source_card = source.scalar_one_or_none()
    if source_card is None:
        return 0

    result = await db.execute(
        update(Card)
        .where(Card.source_card_id == source_card_id)
        .values(title=source_card.title, content=source_card.content)
    )
    return result.rowcount


async def get_linked_instances(
    db: AsyncSession,
    card_id: uuid.UUID,
) -> List[Card]:
    """Get all cards that are linked to the given source card."""
    result = await db.execute(
        select(Card)
        .where(Card.source_card_id == card_id)
        .order_by(Card.created_at)
    )
    return list(result.scalars().all())


# ──────────────────────────────────────────────
# Cross-board search
# ──────────────────────────────────────────────

async def search_cards(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: Optional[str] = None,
    card_type: Optional[str] = None,
    tag_ids: Optional[List[uuid.UUID]] = None,
    is_library: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """Cross-board card search with filtering and pagination.

    Joins Board to enforce user ownership and include the board name in
    results. Optionally filters by:
      - q: ILIKE search on title and content
      - card_type: exact match on card_type
      - tag_ids: cards that have ALL specified tags (via CardTag join)
      - is_library: filter by is_library flag

    Returns a tuple of (list-of-card-dicts-with-board_name, total_count).
    """
    # Clamp pagination bounds
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    # Base query: cards joined with their board for ownership and board name
    base_conditions = [Board.user_id == user_id]

    if q:
        search_term = f"%{q}%"
        base_conditions.append(
            or_(
                Card.title.ilike(search_term),
                Card.content.ilike(search_term),
            )
        )

    if card_type:
        base_conditions.append(Card.card_type == card_type)

    if is_library is not None:
        base_conditions.append(Card.is_library == is_library)

    # If tag_ids are provided, filter to cards that have ALL specified tags
    if tag_ids:
        for tid in tag_ids:
            tag_subq = (
                select(CardTag.card_id)
                .where(CardTag.tag_id == tid)
                .correlate(Card)
                .scalar_subquery()
            )
            base_conditions.append(Card.id.in_(
                select(CardTag.card_id).where(CardTag.tag_id == tid)
            ))

    # Count query
    count_query = (
        select(func.count(Card.id))
        .join(Board, Card.board_id == Board.id)
        .where(*base_conditions)
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Data query -- select card columns plus board name
    data_query = (
        select(Card, Board.name.label("board_name"))
        .join(Board, Card.board_id == Board.id)
        .where(*base_conditions)
        .order_by(Card.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = await db.execute(data_query)
    results = []
    for card, board_name in rows:
        results.append({
            "id": str(card.id),
            "board_id": str(card.board_id),
            "board_name": board_name,
            "card_type": card.card_type,
            "title": card.title,
            "content": card.content[:300] if card.content else None,
            "color": card.color,
            "is_library": card.is_library,
            "source_card_id": str(card.source_card_id) if card.source_card_id else None,
            "position_x": card.position_x,
            "position_y": card.position_y,
            "created_at": card.created_at.isoformat() if card.created_at else None,
            "updated_at": card.updated_at.isoformat() if card.updated_at else None,
        })

    return results, total


# ──────────────────────────────────────────────
# Library toggle
# ──────────────────────────────────────────────

async def toggle_library(
    db: AsyncSession,
    card_id: uuid.UUID,
) -> Optional[Dict[str, Any]]:
    """Toggle the is_library flag on a card.

    Returns a dict with the card id and the new is_library value,
    or None if the card was not found.
    """
    result = await db.execute(
        select(Card).where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    if card is None:
        return None

    new_value = not card.is_library
    await db.execute(
        update(Card)
        .where(Card.id == card_id)
        .values(is_library=new_value)
    )
    return {"id": str(card.id), "is_library": new_value}
