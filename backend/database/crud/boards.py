"""CRUD operations for boards, cards, and edges."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Board, Card, Edge, Section, PropertyDefinition


# ──────────────────────────────────────────────
# Board operations
# ──────────────────────────────────────────────

async def get_board_by_id(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Board]:
    """Get board by ID with user ownership check."""
    result = await db.execute(
        select(Board).where(
            Board.id == board_id,
            Board.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def get_board_with_contents(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Board]:
    """Get board with cards and edges eager-loaded."""
    result = await db.execute(
        select(Board)
        .options(
            selectinload(Board.cards),
            selectinload(Board.edges),
            selectinload(Board.sections),
            selectinload(Board.property_definitions),
        )
        .where(
            Board.id == board_id,
            Board.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def list_boards(
    db: AsyncSession,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50
) -> List[Board]:
    """List boards for a user, optionally filtered by project."""
    query = select(Board).where(Board.user_id == user_id)
    if project_id is not None:
        query = query.where(Board.project_id == project_id)
    query = query.order_by(Board.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_board(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    project_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None
) -> Board:
    """Create a new board."""
    board = Board(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        project_id=project_id,
        description=description,
        viewport={"x": 0, "y": 0, "zoom": 1},
    )
    db.add(board)
    await db.flush()
    return board


async def update_board(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    **kwargs
) -> Optional[Board]:
    """Update board fields."""
    allowed_fields = {"name", "description", "project_id", "memory", "parent_board_id", "depth", "icon", "view_config"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        return await get_board_by_id(db, board_id, user_id)

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.execute(
        update(Board)
        .where(Board.id == board_id, Board.user_id == user_id)
        .values(**update_data)
    )
    return await get_board_by_id(db, board_id, user_id)


async def update_board_viewport(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    viewport: dict
) -> Optional[Board]:
    """Save viewport (pan/zoom) state."""
    await db.execute(
        update(Board)
        .where(Board.id == board_id, Board.user_id == user_id)
        .values(viewport=viewport, updated_at=datetime.now(timezone.utc))
    )
    return await get_board_by_id(db, board_id, user_id)


async def delete_board(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID
) -> bool:
    """Delete board (cascades to cards and edges)."""
    result = await db.execute(
        delete(Board).where(Board.id == board_id, Board.user_id == user_id)
    )
    return result.rowcount > 0


async def count_boards(
    db: AsyncSession,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None
) -> int:
    """Count boards for a user."""
    query = select(func.count(Board.id)).where(Board.user_id == user_id)
    if project_id is not None:
        query = query.where(Board.project_id == project_id)
    result = await db.execute(query)
    return result.scalar() or 0


# ──────────────────────────────────────────────
# Card operations
# ──────────────────────────────────────────────

async def get_card_by_id(
    db: AsyncSession,
    card_id: uuid.UUID,
    board_id: uuid.UUID
) -> Optional[Card]:
    """Get card by ID within a board."""
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.board_id == board_id)
    )
    return result.scalar_one_or_none()


async def list_cards(
    db: AsyncSession,
    board_id: uuid.UUID
) -> List[Card]:
    """List all cards on a board."""
    result = await db.execute(
        select(Card)
        .where(Card.board_id == board_id)
        .order_by(Card.created_at)
    )
    return list(result.scalars().all())


async def create_card(
    db: AsyncSession,
    board_id: uuid.UUID,
    card_type: str = "note",
    title: Optional[str] = None,
    content: Optional[str] = None,
    position_x: float = 0.0,
    position_y: float = 0.0,
    width: float = 280.0,
    height: float = 200.0,
    color: Optional[str] = None,
    source_message_id: Optional[uuid.UUID] = None,
    source_conversation_id: Optional[uuid.UUID] = None,
    extra: Optional[dict] = None
) -> Card:
    """Create a card on a board."""
    card = Card(
        id=uuid.uuid4(),
        board_id=board_id,
        card_type=card_type,
        title=title,
        content=content,
        position_x=position_x,
        position_y=position_y,
        width=width,
        height=height,
        color=color,
        source_message_id=source_message_id,
        source_conversation_id=source_conversation_id,
        extra=extra or {},
    )
    db.add(card)
    await db.flush()
    return card


async def update_card(
    db: AsyncSession,
    card_id: uuid.UUID,
    board_id: uuid.UUID,
    **kwargs
) -> Optional[Card]:
    """Update card fields."""
    allowed_fields = {
        "title", "content", "position_x", "position_y",
        "width", "height", "color", "extra", "card_type",
        "is_inbox", "is_journal", "journal_date", "section_id"
    }
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        return await get_card_by_id(db, card_id, board_id)

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.execute(
        update(Card)
        .where(Card.id == card_id, Card.board_id == board_id)
        .values(**update_data)
    )

    # Auto-sync linked cards if title or content changed
    if "title" in update_data or "content" in update_data:
        from .card_search import sync_linked_cards
        await sync_linked_cards(db, card_id)

    return await get_card_by_id(db, card_id, board_id)


async def batch_update_card_positions(
    db: AsyncSession,
    board_id: uuid.UUID,
    positions: List[Dict[str, Any]]
) -> int:
    """Batch update card positions. Each item: {card_id, x, y}."""
    updated = 0
    now = datetime.now(timezone.utc)
    for pos in positions:
        if not isinstance(pos, dict):
            continue
        card_id = pos.get("card_id") or pos.get("id")
        if not card_id:
            continue
        try:
            cid = uuid.UUID(str(card_id))
        except (ValueError, TypeError):
            continue
        values: Dict[str, Any] = {"updated_at": now}
        try:
            if "x" in pos and pos["x"] is not None:
                values["position_x"] = float(pos["x"])
            if "y" in pos and pos["y"] is not None:
                values["position_y"] = float(pos["y"])
            if "width" in pos and pos["width"] is not None:
                values["width"] = float(pos["width"])
            if "height" in pos and pos["height"] is not None:
                values["height"] = float(pos["height"])
        except (TypeError, ValueError):
            continue
        if len(values) <= 1:
            continue
        try:
            result = await db.execute(
                update(Card)
                .where(Card.id == cid, Card.board_id == board_id)
                .values(**values)
            )
            updated += result.rowcount
        except Exception:
            continue
    return updated


async def delete_card(
    db: AsyncSession,
    card_id: uuid.UUID,
    board_id: uuid.UUID
) -> bool:
    """Delete a card (cascades edges referencing it)."""
    result = await db.execute(
        delete(Card).where(Card.id == card_id, Card.board_id == board_id)
    )
    return result.rowcount > 0


async def merge_cards(
    db: AsyncSession,
    board_id: uuid.UUID,
    target_card_id: uuid.UUID,
    source_card_id: uuid.UUID,
) -> Optional[Card]:
    """Merge source card into target card.

    Appends source content to target, transfers edges from source to target,
    removes self-referential edges, merges extra dicts, takes the wider width,
    and deletes the source card.

    Returns the updated target card, or None if either card is missing.
    """
    target = await get_card_by_id(db, target_card_id, board_id)
    source = await get_card_by_id(db, source_card_id, board_id)
    if not target or not source:
        return None

    # ── Build merged content ──
    target_content = target.content or ""
    source_content = source.content or ""

    if source.title and source.title != target.title:
        appended = f"\n\n## {source.title}\n\n{source_content}"
    else:
        appended = source_content

    if target_content and appended:
        merged_content = f"{target_content}\n\n---\n\n{appended.lstrip()}"
    else:
        merged_content = target_content or appended

    # ── Transfer edges: re-point from_card_id ──
    await db.execute(
        update(Edge)
        .where(Edge.from_card_id == source_card_id, Edge.board_id == board_id)
        .values(from_card_id=target_card_id)
    )

    # ── Transfer edges: re-point to_card_id ──
    await db.execute(
        update(Edge)
        .where(Edge.to_card_id == source_card_id, Edge.board_id == board_id)
        .values(to_card_id=target_card_id)
    )

    # ── Delete self-referential edges that resulted from the transfer ──
    await db.execute(
        delete(Edge)
        .where(
            Edge.board_id == board_id,
            Edge.from_card_id == target_card_id,
            Edge.to_card_id == target_card_id,
        )
    )

    # ── Merge extra dicts (target takes priority for conflicts) ──
    source_extra = dict(source.extra) if source.extra else {}
    target_extra = dict(target.extra) if target.extra else {}
    merged_extra = {**source_extra, **target_extra}

    # ── Store merge provenance for unmerge/split ──
    existing_provenance = merged_extra.get("merged_from", [])
    existing_provenance.append({
        "card_id": str(source.id),
        "title": source.title,
        "content": source_content,
        "card_type": source.card_type or "note",
        "width": source.width,
        "color": source.color,
        "position_x": source.position_x,
        "position_y": source.position_y,
        "extra": source_extra,
    })
    merged_extra["merged_from"] = existing_provenance

    # ── Take the wider width ──
    merged_width = max(target.width, source.width)

    # ── Apply updates to target card ──
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Card)
        .where(Card.id == target_card_id, Card.board_id == board_id)
        .values(
            content=merged_content,
            extra=merged_extra,
            width=merged_width,
            updated_at=now,
        )
    )

    # ── Delete source card (cascade removes any remaining edges) ──
    await db.execute(
        delete(Card).where(Card.id == source_card_id, Card.board_id == board_id)
    )

    return await get_card_by_id(db, target_card_id, board_id)


async def split_card(
    db: AsyncSession,
    board_id: uuid.UUID,
    card_id: uuid.UUID,
) -> Optional[dict]:
    """Split a previously merged card back into its original components.

    Reads `extra.merged_from` provenance, recreates original source cards
    at nearby positions, restores the target card to its pre-merge content,
    and clears the provenance.

    Returns {"target": Card, "restored": [Card, ...]} or None if not splittable.
    """
    card = await get_card_by_id(db, card_id, board_id)
    if not card:
        return None

    card_extra = dict(card.extra) if card.extra else {}
    provenance = card_extra.get("merged_from")
    if not provenance or not isinstance(provenance, list) or len(provenance) == 0:
        return None

    now = datetime.now(timezone.utc)
    restored_cards = []

    # Recreate each source card from provenance
    for i, src in enumerate(provenance):
        src_extra = dict(src.get("extra", {}))
        # Clean provenance from restored cards
        src_extra.pop("merged_from", None)
        new_card = Card(
            id=uuid.uuid4(),
            board_id=board_id,
            card_type=src.get("card_type", "note"),
            title=src.get("title"),
            content=src.get("content", ""),
            position_x=card.position_x + (i + 1) * 60,
            position_y=card.position_y + (i + 1) * 60,
            width=src.get("width", 280.0),
            height=200.0,
            color=src.get("color"),
            extra=src_extra,
        )
        db.add(new_card)
        restored_cards.append(new_card)

    # Restore the target card: strip appended content and clear provenance
    # The merged content has "---" separators — restore to original by
    # taking everything before the first merge separator
    original_content = card.content or ""
    first_separator = original_content.find("\n\n---\n\n")
    if first_separator >= 0:
        original_content = original_content[:first_separator]

    cleaned_extra = {k: v for k, v in card_extra.items() if k != "merged_from"}
    await db.execute(
        update(Card)
        .where(Card.id == card_id, Card.board_id == board_id)
        .values(
            content=original_content,
            extra=cleaned_extra,
            updated_at=now,
        )
    )

    await db.flush()
    updated_target = await get_card_by_id(db, card_id, board_id)
    return {"target": updated_target, "restored": restored_cards}


# ──────────────────────────────────────────────
# Edge operations
# ──────────────────────────────────────────────

async def list_edges(
    db: AsyncSession,
    board_id: uuid.UUID
) -> List[Edge]:
    """List all edges on a board."""
    result = await db.execute(
        select(Edge)
        .where(Edge.board_id == board_id)
        .order_by(Edge.created_at)
    )
    return list(result.scalars().all())


async def create_edge(
    db: AsyncSession,
    board_id: uuid.UUID,
    from_card_id: uuid.UUID,
    to_card_id: uuid.UUID,
    edge_type: str = "related",
    label: Optional[str] = None,
    style: Optional[dict] = None,
    source_handle: Optional[str] = None,
    target_handle: Optional[str] = None
) -> Edge:
    """Create an edge between two cards."""
    edge = Edge(
        id=uuid.uuid4(),
        board_id=board_id,
        from_card_id=from_card_id,
        to_card_id=to_card_id,
        edge_type=edge_type,
        label=label,
        style=style or {},
        source_handle=source_handle,
        target_handle=target_handle,
    )
    db.add(edge)
    await db.flush()
    return edge


async def update_edge(
    db: AsyncSession,
    edge_id: uuid.UUID,
    board_id: uuid.UUID,
    **kwargs
) -> Optional[Edge]:
    """Update edge fields."""
    allowed_fields = {"label", "edge_type", "style", "source_handle", "target_handle"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        result = await db.execute(
            select(Edge).where(Edge.id == edge_id, Edge.board_id == board_id)
        )
        return result.scalar_one_or_none()

    await db.execute(
        update(Edge)
        .where(Edge.id == edge_id, Edge.board_id == board_id)
        .values(**update_data)
    )
    result = await db.execute(
        select(Edge).where(Edge.id == edge_id, Edge.board_id == board_id)
    )
    return result.scalar_one_or_none()


async def delete_edge(
    db: AsyncSession,
    edge_id: uuid.UUID,
    board_id: uuid.UUID
) -> bool:
    """Delete an edge."""
    result = await db.execute(
        delete(Edge).where(Edge.id == edge_id, Edge.board_id == board_id)
    )
    return result.rowcount > 0


# ──────────────────────────────────────────────
# Board Memory operations
# ──────────────────────────────────────────────

async def get_board_memory(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[dict]:
    """Get board memory."""
    board = await get_board_by_id(db, board_id, user_id)
    if not board:
        return None
    return board.memory or {"facts": [], "decisions": [], "preferences": {}}


async def add_board_fact(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    fact: str,
    max_facts: int = 100
) -> Optional[Board]:
    """Add a fact to board memory."""
    board = await get_board_by_id(db, board_id, user_id)
    if not board:
        return None

    memory = dict(board.memory) if board.memory else {"facts": [], "decisions": [], "preferences": {}}
    facts = list(memory.get("facts", []))
    facts.append({
        "content": fact,
        "added_at": datetime.now(timezone.utc).isoformat()
    })
    if len(facts) > max_facts:
        facts = facts[-max_facts:]
    memory["facts"] = facts
    return await update_board(db, board_id, user_id, memory=memory)


async def add_board_decision(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    decision: str,
    context: Optional[str] = None
) -> Optional[Board]:
    """Add a decision to board memory."""
    board = await get_board_by_id(db, board_id, user_id)
    if not board:
        return None

    memory = dict(board.memory) if board.memory else {"facts": [], "decisions": [], "preferences": {}}
    decisions = list(memory.get("decisions", []))
    decisions.append({
        "content": decision,
        "context": context,
        "added_at": datetime.now(timezone.utc).isoformat()
    })
    if len(decisions) > 50:
        decisions = decisions[-50:]
    memory["decisions"] = decisions
    return await update_board(db, board_id, user_id, memory=memory)


async def clear_board_memory(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Board]:
    """Clear all board memory."""
    return await update_board(
        db, board_id, user_id,
        memory={"facts": [], "decisions": [], "preferences": {}}
    )


# ──────────────────────────────────────────────
# Nested board operations
# ──────────────────────────────────────────────

async def get_board_children(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID
) -> List[Board]:
    """Get child boards of a board."""
    result = await db.execute(
        select(Board)
        .where(Board.parent_board_id == board_id, Board.user_id == user_id)
        .order_by(Board.created_at)
    )
    return list(result.scalars().all())


async def get_board_breadcrumbs(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID
) -> List[Dict[str, Any]]:
    """Get breadcrumb trail from root to this board."""
    breadcrumbs: List[Dict[str, Any]] = []
    current_id = board_id
    seen: set = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        board = await get_board_by_id(db, current_id, user_id)
        if not board:
            break
        breadcrumbs.insert(0, {
            "id": str(board.id),
            "name": board.name,
            "icon": getattr(board, "icon", None),
        })
        current_id = getattr(board, "parent_board_id", None)
    return breadcrumbs


async def create_child_board(
    db: AsyncSession,
    parent_board_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    project_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None
) -> Optional[Board]:
    """Create a child board under a parent."""
    parent = await get_board_by_id(db, parent_board_id, user_id)
    if not parent:
        return None
    parent_depth = getattr(parent, "depth", 0) or 0
    board = Board(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        project_id=project_id or parent.project_id,
        description=description,
        parent_board_id=parent_board_id,
        depth=parent_depth + 1,
        viewport={"x": 0, "y": 0, "zoom": 1},
    )
    db.add(board)
    await db.flush()
    return board


async def move_board(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    new_parent_id: Optional[uuid.UUID] = None
) -> Optional[Board]:
    """Move a board to a new parent (or root if new_parent_id is None)."""
    new_depth = 0
    if new_parent_id:
        parent = await get_board_by_id(db, new_parent_id, user_id)
        if not parent:
            return None
        new_depth = (getattr(parent, "depth", 0) or 0) + 1
    await db.execute(
        update(Board)
        .where(Board.id == board_id, Board.user_id == user_id)
        .values(
            parent_board_id=new_parent_id,
            depth=new_depth,
            updated_at=datetime.now(timezone.utc),
        )
    )
    return await get_board_by_id(db, board_id, user_id)


# ──────────────────────────────────────────────
# Journal operations
# ──────────────────────────────────────────────

async def create_journal_entry(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    journal_date=None,
    title: Optional[str] = None,
    content: Optional[str] = None
) -> Optional[Card]:
    """Create a journal entry card on a board."""
    from datetime import date as date_type

    board = await get_board_by_id(db, board_id, user_id)
    if not board:
        return None

    jdate = journal_date or date_type.today()

    # Check if entry already exists for this date
    existing = await db.execute(
        select(Card).where(
            Card.board_id == board_id,
            Card.is_journal == True,
            Card.journal_date == jdate
        )
    )
    existing_card = existing.scalar_one_or_none()
    if existing_card:
        return existing_card

    card = Card(
        id=uuid.uuid4(),
        board_id=board_id,
        card_type="note",
        title=title or f"Journal - {jdate.isoformat()}",
        content=content or "",
        position_x=0.0,
        position_y=0.0,
        is_journal=True,
        journal_date=jdate,
        extra={"journal": True},
    )
    db.add(card)
    await db.flush()
    return card


async def list_journal_entries(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 30
) -> List[Card]:
    """List journal entries for a board, most recent first."""
    board = await get_board_by_id(db, board_id, user_id)
    if not board:
        return []
    result = await db.execute(
        select(Card)
        .where(Card.board_id == board_id, Card.is_journal == True)
        .order_by(Card.journal_date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ──────────────────────────────────────────────
# Inbox operations
# ──────────────────────────────────────────────

async def create_inbox_item(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
    title: Optional[str] = None
) -> Optional[Card]:
    """Quick capture an item to the inbox."""
    board = await get_board_by_id(db, board_id, user_id)
    if not board:
        return None

    card = Card(
        id=uuid.uuid4(),
        board_id=board_id,
        card_type="note",
        title=title or content[:80],
        content=content,
        position_x=0.0,
        position_y=0.0,
        is_inbox=True,
        extra={"inbox": True},
    )
    db.add(card)
    await db.flush()
    return card


async def list_inbox_items(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID
) -> List[Card]:
    """List inbox items for a board."""
    board = await get_board_by_id(db, board_id, user_id)
    if not board:
        return []
    result = await db.execute(
        select(Card)
        .where(Card.board_id == board_id, Card.is_inbox == True)
        .order_by(Card.created_at.desc())
    )
    return list(result.scalars().all())


async def process_inbox_item(
    db: AsyncSession,
    card_id: uuid.UUID,
    board_id: uuid.UUID
) -> Optional[Card]:
    """Process an inbox item (clear inbox flag, keep card)."""
    await db.execute(
        update(Card)
        .where(Card.id == card_id, Card.board_id == board_id)
        .values(is_inbox=False, updated_at=datetime.now(timezone.utc))
    )
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.board_id == board_id)
    )
    return result.scalar_one_or_none()
