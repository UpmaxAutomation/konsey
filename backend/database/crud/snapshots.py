"""CRUD operations for board snapshots (version history)."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Board, Card, Edge, Section, BoardSnapshot


MAX_SNAPSHOTS_PER_BOARD = 50
AUTO_SNAPSHOT_COOLDOWN_MINUTES = 5


async def capture_snapshot(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    trigger: str = "auto",
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> BoardSnapshot:
    """Capture a point-in-time snapshot of a board's cards, edges, and sections."""
    # Load cards
    cards_result = await db.execute(
        select(Card).where(Card.board_id == board_id)
    )
    cards = list(cards_result.scalars().all())

    # Load edges
    edges_result = await db.execute(
        select(Edge).where(Edge.board_id == board_id)
    )
    edges = list(edges_result.scalars().all())

    # Load sections
    sections_result = await db.execute(
        select(Section).where(Section.board_id == board_id)
    )
    sections = list(sections_result.scalars().all())

    # Serialize to JSONB-compatible dict
    snapshot_data = {
        "cards": [
            {
                "id": str(c.id),
                "card_type": c.card_type,
                "title": c.title,
                "content": c.content,
                "position_x": c.position_x,
                "position_y": c.position_y,
                "width": c.width,
                "height": c.height,
                "color": c.color,
                "extra": c.extra,
                "is_inbox": getattr(c, "is_inbox", False) or False,
                "is_journal": getattr(c, "is_journal", False) or False,
                "journal_date": str(c.journal_date) if getattr(c, "journal_date", None) else None,
                "section_id": str(c.section_id) if getattr(c, "section_id", None) else None,
                "source_message_id": str(c.source_message_id) if c.source_message_id else None,
                "source_conversation_id": str(c.source_conversation_id) if c.source_conversation_id else None,
            }
            for c in cards
        ],
        "edges": [
            {
                "id": str(e.id),
                "from_card_id": str(e.from_card_id),
                "to_card_id": str(e.to_card_id),
                "edge_type": e.edge_type,
                "label": e.label,
                "style": getattr(e, "style", None) or {},
                "source_handle": getattr(e, "source_handle", None),
                "target_handle": getattr(e, "target_handle", None),
            }
            for e in edges
        ],
        "sections": [
            {
                "id": str(s.id),
                "title": s.title,
                "color": s.color,
                "x": s.x,
                "y": s.y,
                "width": s.width,
                "height": s.height,
            }
            for s in sections
        ],
    }

    snapshot = BoardSnapshot(
        id=uuid.uuid4(),
        board_id=board_id,
        user_id=user_id,
        name=name,
        description=description,
        trigger=trigger,
        snapshot_data=snapshot_data,
        card_count=len(cards),
        edge_count=len(edges),
        section_count=len(sections),
    )
    db.add(snapshot)
    await db.flush()

    # Enforce max snapshots per board: delete oldest auto snapshots if exceeded
    count_result = await db.execute(
        select(func.count(BoardSnapshot.id)).where(
            BoardSnapshot.board_id == board_id
        )
    )
    total = count_result.scalar() or 0

    if total > MAX_SNAPSHOTS_PER_BOARD:
        excess = total - MAX_SNAPSHOTS_PER_BOARD
        # Find the oldest auto snapshots to delete
        oldest_result = await db.execute(
            select(BoardSnapshot.id)
            .where(
                BoardSnapshot.board_id == board_id,
                BoardSnapshot.trigger == "auto",
            )
            .order_by(BoardSnapshot.created_at.asc())
            .limit(excess)
        )
        oldest_ids = [row[0] for row in oldest_result.all()]
        if oldest_ids:
            await db.execute(
                delete(BoardSnapshot).where(BoardSnapshot.id.in_(oldest_ids))
            )

    return snapshot


async def list_snapshots(
    db: AsyncSession,
    board_id: uuid.UUID,
    limit: int = 50,
) -> List[BoardSnapshot]:
    """List snapshots for a board (metadata only, no snapshot_data)."""
    result = await db.execute(
        select(
            BoardSnapshot.id,
            BoardSnapshot.board_id,
            BoardSnapshot.user_id,
            BoardSnapshot.name,
            BoardSnapshot.description,
            BoardSnapshot.trigger,
            BoardSnapshot.card_count,
            BoardSnapshot.edge_count,
            BoardSnapshot.section_count,
            BoardSnapshot.created_at,
        )
        .where(BoardSnapshot.board_id == board_id)
        .order_by(BoardSnapshot.created_at.desc())
        .limit(limit)
    )
    return result.all()


async def get_snapshot(
    db: AsyncSession,
    snapshot_id: uuid.UUID,
) -> Optional[BoardSnapshot]:
    """Get a single snapshot with full data."""
    result = await db.execute(
        select(BoardSnapshot).where(BoardSnapshot.id == snapshot_id)
    )
    return result.scalar_one_or_none()


async def restore_snapshot(
    db: AsyncSession,
    snapshot_id: uuid.UUID,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Optional[BoardSnapshot]:
    """Restore a board to a snapshot state.

    Creates a safety snapshot first, then deletes current content and recreates from snapshot data.
    Returns the safety snapshot for potential undo.
    """
    # Get the snapshot to restore
    snapshot = await get_snapshot(db, snapshot_id)
    if not snapshot or snapshot.board_id != board_id:
        return None

    # Capture a safety snapshot before restoring
    safety_snapshot = await capture_snapshot(
        db, board_id, user_id,
        trigger="restore",
        name="Auto-save before restore",
        description=f"Safety snapshot before restoring to: {snapshot.name or snapshot_id}",
    )

    # Delete current cards, edges, sections for this board
    await db.execute(delete(Edge).where(Edge.board_id == board_id))
    await db.execute(delete(Card).where(Card.board_id == board_id))
    await db.execute(delete(Section).where(Section.board_id == board_id))

    data = snapshot.snapshot_data

    # Recreate sections first (cards may reference them)
    section_id_map = {}
    for s in data.get("sections", []):
        new_section = Section(
            id=uuid.uuid4(),
            board_id=board_id,
            title=s.get("title", ""),
            color=s.get("color", "gray"),
            x=s.get("x", 0),
            y=s.get("y", 0),
            width=s.get("width", 400),
            height=s.get("height", 300),
        )
        section_id_map[s["id"]] = new_section.id
        db.add(new_section)

    await db.flush()

    # Recreate cards
    card_id_map = {}
    for c in data.get("cards", []):
        section_ref = c.get("section_id")
        new_section_id = section_id_map.get(section_ref) if section_ref else None

        new_card = Card(
            id=uuid.uuid4(),
            board_id=board_id,
            card_type=c.get("card_type", "note"),
            title=c.get("title"),
            content=c.get("content"),
            position_x=c.get("position_x", 0),
            position_y=c.get("position_y", 0),
            width=c.get("width", 280),
            height=c.get("height", 200),
            color=c.get("color"),
            extra=c.get("extra", {}),
            is_inbox=c.get("is_inbox", False),
            is_journal=c.get("is_journal", False),
            section_id=new_section_id,
        )
        # Map old card ID to new card ID for edge recreation
        card_id_map[c["id"]] = new_card.id

        # Restore journal_date if present
        if c.get("journal_date"):
            from datetime import date as date_type
            try:
                new_card.journal_date = date_type.fromisoformat(c["journal_date"])
            except (ValueError, TypeError):
                pass

        # Restore source references if present
        if c.get("source_message_id"):
            try:
                new_card.source_message_id = uuid.UUID(c["source_message_id"])
            except (ValueError, TypeError):
                pass
        if c.get("source_conversation_id"):
            try:
                new_card.source_conversation_id = uuid.UUID(c["source_conversation_id"])
            except (ValueError, TypeError):
                pass

        db.add(new_card)

    await db.flush()

    # Recreate edges
    for e in data.get("edges", []):
        from_id = card_id_map.get(e.get("from_card_id"))
        to_id = card_id_map.get(e.get("to_card_id"))
        if from_id and to_id:
            new_edge = Edge(
                id=uuid.uuid4(),
                board_id=board_id,
                from_card_id=from_id,
                to_card_id=to_id,
                edge_type=e.get("edge_type", "related"),
                label=e.get("label"),
                style=e.get("style", {}),
                source_handle=e.get("source_handle"),
                target_handle=e.get("target_handle"),
            )
            db.add(new_edge)

    return safety_snapshot


async def delete_snapshot(
    db: AsyncSession,
    snapshot_id: uuid.UUID,
) -> bool:
    """Delete a snapshot."""
    result = await db.execute(
        delete(BoardSnapshot).where(BoardSnapshot.id == snapshot_id)
    )
    return result.rowcount > 0


async def get_last_auto_snapshot_time(
    db: AsyncSession,
    board_id: uuid.UUID,
) -> Optional[datetime]:
    """Get the creation time of the most recent auto snapshot for cooldown checks."""
    result = await db.execute(
        select(BoardSnapshot.created_at)
        .where(
            BoardSnapshot.board_id == board_id,
            BoardSnapshot.trigger == "auto",
        )
        .order_by(BoardSnapshot.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
