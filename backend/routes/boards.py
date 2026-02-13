"""Board/Canvas routes for LLM Council."""

import asyncio
import json
import logging
import re
import uuid
from typing import Optional, List, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from ..database.crud import boards as boards_crud
from ..database.crud import sections as sections_crud
from ..database.crud import tags as tags_crud
from ..database.crud import snapshots as snapshots_crud
from ..database.crud import mentions as mentions_crud
from ..auth.dependencies import get_current_user
from ..collaboration.manager import manager as collab_manager
from ..utils import parse_uuid

MENTION_PATTERN = re.compile(r'\[\[([^|\]]+)\|([a-f0-9-]+)\]\]')


def extract_mention_ids(content: str) -> List[str]:
    """Extract card IDs from [[title|uuid]] mention patterns."""
    return [match.group(2) for match in MENTION_PATTERN.finditer(content or '')]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/boards", tags=["boards"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class CreateBoardRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    project_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=2000)


class UpdateBoardRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    project_id: Optional[str] = None


class UpdateViewportRequest(BaseModel):
    x: float
    y: float
    zoom: float = Field(ge=0.1, le=5.0)


class CreateCardRequest(BaseModel):
    card_type: str = Field(default="note")
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    position_x: float = 0.0
    position_y: float = 0.0
    width: float = Field(default=280.0, ge=100, le=1200)
    height: float = Field(default=200.0, ge=80, le=800)
    color: Optional[str] = None
    extra: Optional[dict] = None


class UpdateCardRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    color: Optional[str] = None
    extra: Optional[dict] = None
    card_type: Optional[str] = None


class BatchUpdatePositionsRequest(BaseModel):
    positions: List[dict]


class CreateEdgeRequest(BaseModel):
    from_card_id: str
    to_card_id: str
    edge_type: str = Field(default="related")
    label: Optional[str] = None
    style: Optional[dict] = None
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None


class UpdateEdgeRequest(BaseModel):
    label: Optional[str] = None
    edge_type: Optional[str] = None
    style: Optional[dict] = None
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None


class CreateCardFromMessageRequest(BaseModel):
    message_id: str
    conversation_id: str
    card_type: str = "council_response"
    position_x: float = 0.0
    position_y: float = 0.0
    extra: Optional[dict] = None


class CreateCardsFromTurnRequest(BaseModel):
    conversation_id: str
    message_index: int
    include_query: bool = True
    include_responses: bool = True
    include_synthesis: bool = True
    base_position_x: float = 0.0
    base_position_y: float = 0.0


class CreateSectionRequest(BaseModel):
    title: str = Field(default="", max_length=255)
    color: str = Field(default="gray", max_length=20)
    x: float = 0.0
    y: float = 0.0
    width: float = Field(default=400.0, ge=100, le=2000)
    height: float = Field(default=300.0, ge=100, le=2000)

class UpdateSectionRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None, max_length=20)
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None

class GroupIntoSectionRequest(BaseModel):
    card_ids: List[str] = Field(..., min_length=2)
    title: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None, max_length=20)
    # Optional: frontend-computed bounds (uses actual rendered card dimensions)
    bounds_x: Optional[float] = None
    bounds_y: Optional[float] = None
    bounds_width: Optional[float] = None
    bounds_height: Optional[float] = None


class MoveBoardRequest(BaseModel):
    new_parent_id: Optional[str] = None

class CreateChildBoardRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class CreateJournalEntryRequest(BaseModel):
    date: Optional[str] = None  # ISO date string, defaults to today
    content: Optional[str] = ""
    title: Optional[str] = None

class CreateInboxItemRequest(BaseModel):
    content: str = Field(..., min_length=1)
    title: Optional[str] = None


class MergeCardsRequest(BaseModel):
    source_card_id: str


class CreateSnapshotRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


# ──────────────────────────────────────────────
# Serialization helpers
# ──────────────────────────────────────────────

def _serialize_board(board, include_contents: bool = False) -> dict:
    data = {
        "id": str(board.id),
        "user_id": str(board.user_id),
        "project_id": str(board.project_id) if board.project_id else None,
        "name": board.name,
        "description": board.description,
        "viewport": board.viewport,
        "memory": getattr(board, "memory", None) or {"facts": [], "decisions": [], "preferences": {}},
        "parent_board_id": str(board.parent_board_id) if getattr(board, 'parent_board_id', None) else None,
        "depth": getattr(board, 'depth', 0) or 0,
        "icon": getattr(board, 'icon', None),
        "view_config": getattr(board, 'view_config', None) or {"active_view": "canvas", "table": {}, "kanban": {}},
        "created_at": board.created_at.isoformat() if board.created_at else None,
        "updated_at": board.updated_at.isoformat() if board.updated_at else None,
    }
    if include_contents:
        data["cards"] = [_serialize_card(c) for c in (board.cards or [])]
        data["edges"] = [_serialize_edge(e) for e in (board.edges or [])]
        data["sections"] = [_serialize_section(s) for s in (getattr(board, 'sections', None) or [])]
        data["property_definitions"] = [_serialize_property_def(p) for p in (getattr(board, 'property_definitions', None) or [])]
    return data


def _serialize_card(card) -> dict:
    return {
        "id": str(card.id),
        "board_id": str(card.board_id),
        "card_type": card.card_type,
        "title": card.title,
        "content": card.content,
        "position_x": card.position_x,
        "position_y": card.position_y,
        "width": card.width,
        "height": card.height,
        "color": card.color,
        "source_message_id": str(card.source_message_id) if card.source_message_id else None,
        "source_conversation_id": str(card.source_conversation_id) if card.source_conversation_id else None,
        "extra": card.extra,
        "is_inbox": getattr(card, 'is_inbox', False) or False,
        "is_journal": getattr(card, 'is_journal', False) or False,
        "journal_date": str(card.journal_date) if getattr(card, 'journal_date', None) else None,
        "section_id": str(card.section_id) if getattr(card, 'section_id', None) else None,
        "created_at": card.created_at.isoformat() if card.created_at else None,
        "updated_at": card.updated_at.isoformat() if card.updated_at else None,
    }


def _serialize_edge(edge) -> dict:
    return {
        "id": str(edge.id),
        "board_id": str(edge.board_id),
        "from_card_id": str(edge.from_card_id),
        "to_card_id": str(edge.to_card_id),
        "edge_type": edge.edge_type,
        "label": edge.label,
        "style": getattr(edge, 'style', None) or {},
        "source_handle": getattr(edge, 'source_handle', None),
        "target_handle": getattr(edge, 'target_handle', None),
        "created_at": edge.created_at.isoformat() if edge.created_at else None,
    }


def _serialize_section(section) -> dict:
    return {
        "id": str(section.id),
        "board_id": str(section.board_id),
        "title": section.title,
        "color": section.color,
        "x": section.x,
        "y": section.y,
        "width": section.width,
        "height": section.height,
        "created_at": section.created_at.isoformat() if section.created_at else None,
    }


def _serialize_property_def(prop) -> dict:
    return {
        "id": str(prop.id),
        "board_id": str(prop.board_id),
        "name": prop.name,
        "property_type": prop.property_type,
        "options": prop.options,
        "sort_order": prop.sort_order,
        "created_at": prop.created_at.isoformat() if prop.created_at else None,
    }


def _serialize_tag(tag) -> dict:
    return {
        "id": str(tag.id),
        "user_id": str(tag.user_id),
        "name": tag.name,
        "color": tag.color,
        "collection": tag.collection,
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
    }


# ──────────────────────────────────────────────
# Board endpoints
# ──────────────────────────────────────────────

@router.get("")
async def list_boards(
    project_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List boards for current user, optionally filtered by project."""
    pid = parse_uuid(project_id, "project_id") if project_id else None
    boards = await boards_crud.list_boards(db, current_user.id, project_id=pid, skip=skip, limit=limit)
    count = await boards_crud.count_boards(db, current_user.id, project_id=pid)
    return {"boards": [_serialize_board(b) for b in boards], "total": count}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_board(
    request: CreateBoardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new board."""
    pid = parse_uuid(request.project_id, "project_id") if request.project_id else None
    board = await boards_crud.create_board(
        db, current_user.id, request.name, project_id=pid, description=request.description
    )
    await db.commit()
    return _serialize_board(board)


@router.get("/{board_id}")
async def get_board(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get board with all cards and edges."""
    board = await boards_crud.get_board_with_contents(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return _serialize_board(board, include_contents=True)


@router.put("/{board_id}")
async def update_board(
    board_id: str,
    request: UpdateBoardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update board name/description."""
    kwargs = {}
    if request.name is not None:
        kwargs["name"] = request.name
    if request.description is not None:
        kwargs["description"] = request.description
    if request.project_id is not None:
        kwargs["project_id"] = parse_uuid(request.project_id, "project_id") if request.project_id else None

    board = await boards_crud.update_board(db, parse_uuid(board_id, "board_id"), current_user.id, **kwargs)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    await db.commit()
    return _serialize_board(board)


@router.patch("/{board_id}/viewport")
async def update_viewport(
    board_id: str,
    request: UpdateViewportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save board viewport (pan/zoom)."""
    viewport = {"x": request.x, "y": request.y, "zoom": request.zoom}
    board = await boards_crud.update_board_viewport(db, parse_uuid(board_id, "board_id"), current_user.id, viewport)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    await db.commit()
    return {"status": "ok"}


@router.delete("/{board_id}")
async def delete_board(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete board and all its cards/edges."""
    deleted = await boards_crud.delete_board(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Board not found")
    await db.commit()
    return {"status": "deleted"}


# ──────────────────────────────────────────────
# Board Memory endpoints
# ──────────────────────────────────────────────

class BoardMemoryActionRequest(BaseModel):
    action: str = Field(..., pattern="^(add_fact|add_decision|clear)$")
    content: Optional[str] = None
    context: Optional[str] = None


@router.get("/{board_id}/memory")
async def get_board_memory_endpoint(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get board memory (facts, decisions, preferences)."""
    memory = await boards_crud.get_board_memory(db, parse_uuid(board_id, "board_id"), current_user.id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return {"memory": memory}


@router.post("/{board_id}/memory")
async def board_memory_action(
    board_id: str,
    request: BoardMemoryActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Perform a memory action on a board."""
    if request.action == "add_fact":
        if not request.content:
            raise HTTPException(status_code=400, detail="content is required for add_fact")
        bid = parse_uuid(board_id, "board_id")
        board = await boards_crud.add_board_fact(db, bid, current_user.id, request.content)
    elif request.action == "add_decision":
        if not request.content:
            raise HTTPException(status_code=400, detail="content is required for add_decision")
        bid = parse_uuid(board_id, "board_id")
        board = await boards_crud.add_board_decision(
            db, bid, current_user.id, request.content, request.context
        )
    elif request.action == "clear":
        board = await boards_crud.clear_board_memory(db, parse_uuid(board_id, "board_id"), current_user.id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    await db.commit()
    return {"memory": board.memory or {"facts": [], "decisions": [], "preferences": {}}}


@router.delete("/{board_id}/memory/facts/{fact_index}")
async def delete_board_fact(
    board_id: str,
    fact_index: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific fact from board memory by index."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    memory = dict(board.memory) if board.memory else {"facts": [], "decisions": [], "preferences": {}}
    facts = list(memory.get("facts", []))
    if fact_index < 0 or fact_index >= len(facts):
        raise HTTPException(status_code=404, detail="Fact not found")
    facts.pop(fact_index)
    memory["facts"] = facts
    await boards_crud.update_board(db, board.id, current_user.id, memory=memory)
    await db.commit()
    return {"memory": memory}


# ──────────────────────────────────────────────
# Card endpoints
# ──────────────────────────────────────────────

@router.get("/{board_id}/cards")
async def list_cards_endpoint(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all cards on a board."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    cards = await boards_crud.list_cards(db, board.id)
    return {"cards": [_serialize_card(c) for c in cards]}


@router.post("/{board_id}/cards", status_code=status.HTTP_201_CREATED)
async def create_card_endpoint(
    board_id: str,
    request: CreateCardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a card on a board."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    card = await boards_crud.create_card(
        db, board.id,
        card_type=request.card_type,
        title=request.title,
        content=request.content,
        position_x=request.position_x,
        position_y=request.position_y,
        width=request.width,
        height=request.height,
        color=request.color,
        extra=request.extra,
    )
    await db.commit()
    asyncio.create_task(collab_manager.broadcast_to_board(
        parse_uuid(board_id, "board_id"),
        {"type": "card_created", "card_id": str(card.id), "board_id": board_id},
        exclude_user=current_user.id,
    ))
    return _serialize_card(card)


@router.patch("/{board_id}/cards/batch-positions")
async def batch_update_positions(
    board_id: str,
    request: BatchUpdatePositionsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch update card positions (for drag operations)."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    try:
        updated = await boards_crud.batch_update_card_positions(
            db, board.id, request.positions or []
        )
        await db.commit()
        return {"updated": updated}
    except Exception as e:
        await db.rollback()
        logger.exception("batch_update_card_positions failed")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update positions: {str(e)}",
        ) from e


@router.patch("/{board_id}/cards/{card_id}")
async def update_card_endpoint(
    board_id: str,
    card_id: str,
    request: UpdateCardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a card's fields."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
    card = await boards_crud.update_card(db, parse_uuid(card_id, "card_id"), board.id, **kwargs)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Sync mentions when content changes
    if 'content' in kwargs:
        mention_ids = extract_mention_ids(kwargs.get('content', ''))
        mention_uuids = [parse_uuid(mid, "mention_id") for mid in mention_ids if mid]
        await mentions_crud.sync_mentions(db, parse_uuid(card_id, "card_id"), board.id, mention_uuids)

    await db.commit()
    asyncio.create_task(collab_manager.broadcast_to_board(
        parse_uuid(board_id, "board_id"),
        {"type": "card_updated", "card_id": str(card_id), "board_id": board_id},
        exclude_user=current_user.id,
    ))
    return _serialize_card(card)


@router.get("/{board_id}/cards/{card_id}/backlinks")
async def get_card_backlinks(
    board_id: str,
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all cards that mention this card (backlinks)."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    backlinks = await mentions_crud.get_backlinks(db, parse_uuid(card_id, "card_id"))
    return {"backlinks": backlinks}


@router.delete("/{board_id}/cards/{card_id}")
async def delete_card_endpoint(
    board_id: str,
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a card."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    deleted = await boards_crud.delete_card(db, parse_uuid(card_id, "card_id"), board.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Card not found")
    await db.commit()
    asyncio.create_task(collab_manager.broadcast_to_board(
        parse_uuid(board_id, "board_id"),
        {"type": "card_deleted", "card_id": card_id, "board_id": board_id},
        exclude_user=current_user.id,
    ))
    return {"status": "deleted"}


@router.post("/{board_id}/cards/{card_id}/merge")
async def merge_cards_endpoint(
    board_id: str,
    card_id: str,
    request: MergeCardsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Merge source card into target card (card_id).

    Appends source content, transfers edges, merges metadata, and deletes the source.
    """
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    merged = await boards_crud.merge_cards(
        db, board.id, parse_uuid(card_id, "card_id"), parse_uuid(request.source_card_id, "source_card_id")
    )
    if not merged:
        raise HTTPException(status_code=404, detail="One or both cards not found")

    await db.commit()

    asyncio.create_task(collab_manager.broadcast_to_board(
        parse_uuid(board_id, "board_id"),
        {
            "type": "cards_merged",
            "target_card_id": card_id,
            "source_card_id": request.source_card_id,
            "board_id": board_id,
        },
        exclude_user=current_user.id,
    ))

    return _serialize_card(merged)


@router.post("/{board_id}/cards/{card_id}/split")
async def split_card_endpoint(
    board_id: str,
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Split a previously merged card back into its original components.

    Reads extra.merged_from provenance and recreates original source cards.
    """
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    result = await boards_crud.split_card(db, board.id, parse_uuid(card_id, "card_id"))
    if not result:
        raise HTTPException(status_code=400, detail="Card has no merge provenance to split")

    await db.commit()

    asyncio.create_task(collab_manager.broadcast_to_board(
        parse_uuid(board_id, "board_id"),
        {
            "type": "card_split",
            "card_id": card_id,
            "board_id": board_id,
        },
        exclude_user=current_user.id,
    ))

    return {
        "target": _serialize_card(result["target"]),
        "restored": [_serialize_card(c) for c in result["restored"]],
    }


# ──────────────────────────────────────────────
# Card-Tag endpoints
# ──────────────────────────────────────────────

class AddCardTagRequest(BaseModel):
    tag_id: str


@router.get("/{board_id}/cards/{card_id}/tags")
async def get_card_tags(
    board_id: str,
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all tags for a card."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    tags = await tags_crud.get_card_tags(db, parse_uuid(card_id, "card_id"))
    return {"tags": [_serialize_tag(t) for t in tags]}


@router.post("/{board_id}/cards/{card_id}/tags", status_code=status.HTTP_201_CREATED)
async def add_card_tag(
    board_id: str,
    card_id: str,
    request: AddCardTagRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a tag to a card."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    await tags_crud.add_card_tag(db, parse_uuid(card_id, "card_id"), parse_uuid(request.tag_id, "tag_id"))
    tags = await tags_crud.get_card_tags(db, parse_uuid(card_id, "card_id"))
    return {"tags": [_serialize_tag(t) for t in tags]}


@router.delete("/{board_id}/cards/{card_id}/tags/{tag_id}")
async def remove_card_tag(
    board_id: str,
    card_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a tag from a card."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    removed = await tags_crud.remove_card_tag(db, parse_uuid(card_id, "card_id"), parse_uuid(tag_id, "tag_id"))
    if not removed:
        raise HTTPException(status_code=404, detail="Tag not found on card")
    return {"ok": True}


# ──────────────────────────────────────────────
# Edge endpoints
# ──────────────────────────────────────────────

@router.get("/{board_id}/edges")
async def list_edges_endpoint(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all edges on a board."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    edges = await boards_crud.list_edges(db, board.id)
    return {"edges": [_serialize_edge(e) for e in edges]}


@router.post("/{board_id}/edges", status_code=status.HTTP_201_CREATED)
async def create_edge_endpoint(
    board_id: str,
    request: CreateEdgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an edge between two cards."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    edge = await boards_crud.create_edge(
        db, board.id,
        from_card_id=parse_uuid(request.from_card_id, "from_card_id"),
        to_card_id=parse_uuid(request.to_card_id, "to_card_id"),
        edge_type=request.edge_type,
        label=request.label,
        style=request.style,
        source_handle=request.source_handle,
        target_handle=request.target_handle,
    )
    await db.commit()
    asyncio.create_task(collab_manager.broadcast_to_board(
        parse_uuid(board_id, "board_id"),
        {"type": "edge_created", "edge_id": str(edge.id), "board_id": board_id},
        exclude_user=current_user.id,
    ))
    return _serialize_edge(edge)


class CreateEdgeBatchRequest(BaseModel):
    edges: List[CreateEdgeRequest]


@router.post("/{board_id}/edges/batch", status_code=status.HTTP_201_CREATED)
async def create_edges_batch(
    board_id: str,
    request: CreateEdgeBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch create edges (for section-to-section connections)."""
    from sqlalchemy.exc import IntegrityError

    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    created = []
    for edge_req in request.edges:
        try:
            edge = await boards_crud.create_edge(
                db, board.id,
                from_card_id=parse_uuid(edge_req.from_card_id, "from_card_id"),
                to_card_id=parse_uuid(edge_req.to_card_id, "to_card_id"),
                edge_type=edge_req.edge_type,
                label=edge_req.label,
                style=edge_req.style,
                source_handle=edge_req.source_handle,
                target_handle=edge_req.target_handle,
            )
            await db.flush()
            created.append(edge)
        except IntegrityError:
            await db.rollback()

    await db.commit()
    return {"edges": [_serialize_edge(e) for e in created]}


@router.patch("/{board_id}/edges/{edge_id}")
async def update_edge_endpoint(
    board_id: str,
    edge_id: str,
    request: UpdateEdgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an edge's fields (label, style, type, handles)."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
    edge = await boards_crud.update_edge(db, parse_uuid(edge_id, "edge_id"), board.id, **kwargs)
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    await db.commit()
    asyncio.create_task(collab_manager.broadcast_to_board(
        parse_uuid(board_id, "board_id"),
        {"type": "edge_updated", "edge_id": edge_id, "board_id": board_id},
        exclude_user=current_user.id,
    ))
    return _serialize_edge(edge)


@router.delete("/{board_id}/edges/{edge_id}")
async def delete_edge_endpoint(
    board_id: str,
    edge_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an edge."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    deleted = await boards_crud.delete_edge(db, parse_uuid(edge_id, "edge_id"), board.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Edge not found")
    await db.commit()
    asyncio.create_task(collab_manager.broadcast_to_board(
        parse_uuid(board_id, "board_id"),
        {"type": "edge_deleted", "edge_id": edge_id, "board_id": board_id},
        exclude_user=current_user.id,
    ))
    return {"status": "deleted"}


# ──────────────────────────────────────────────
# Section endpoints
# ──────────────────────────────────────────────

@router.get("/{board_id}/sections")
async def list_sections_endpoint(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    sections = await sections_crud.list_sections(db, board.id)
    return {"sections": [_serialize_section(s) for s in sections]}

@router.post("/{board_id}/sections", status_code=status.HTTP_201_CREATED)
async def create_section_endpoint(
    board_id: str,
    request: CreateSectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    section = await sections_crud.create_section(
        db, board.id,
        title=request.title, color=request.color,
        x=request.x, y=request.y,
        width=request.width, height=request.height,
    )
    await db.commit()
    return _serialize_section(section)

@router.post("/{board_id}/sections/group", status_code=status.HTTP_201_CREATED)
async def group_cards_into_section(
    board_id: str,
    request: GroupIntoSectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Group selected cards into a new section (Heptabase-style Cmd+G)."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    # Fetch all requested cards and validate
    cards = []
    for cid_str in request.card_ids:
        card = await boards_crud.get_card_by_id(db, parse_uuid(cid_str, "card_id"), board.id)
        if not card:
            raise HTTPException(status_code=404, detail=f"Card {cid_str} not found")
        if getattr(card, 'section_id', None):
            raise HTTPException(
                status_code=400,
                detail=f"Card {cid_str} already belongs to a section. Ungroup it first."
            )
        cards.append(card)

    # Compute bounding box — prefer frontend-provided bounds (actual rendered sizes)
    padding = 60
    header_offset = 44

    if (request.bounds_x is not None and request.bounds_y is not None
            and request.bounds_width is not None and request.bounds_height is not None):
        section_x = request.bounds_x
        section_y = request.bounds_y
        section_width = request.bounds_width
        section_height = request.bounds_height
    else:
        # Fallback: compute from DB card dimensions (generous minimums for auto-sized cards)
        min_x = min(c.position_x for c in cards)
        min_y = min(c.position_y for c in cards)
        max_x = max(c.position_x + max(c.width, 280) for c in cards)
        max_y = max(c.position_y + max(c.height, 300) for c in cards)

        section_x = min_x - padding
        section_y = min_y - padding - header_offset
        section_width = (max_x - min_x) + padding * 2
        section_height = (max_y - min_y) + padding * 2 + header_offset

    # Create the section
    section = await sections_crud.create_section(
        db, board.id,
        title=request.title or "Group",
        color=request.color or "gray",
        x=section_x, y=section_y,
        width=section_width, height=section_height,
    )

    # Convert card positions to relative and assign section_id
    updated_cards = []
    for card in cards:
        rel_x = card.position_x - section_x
        rel_y = card.position_y - section_y - header_offset
        updated = await boards_crud.update_card(
            db, card.id, board.id,
            position_x=rel_x, position_y=rel_y, section_id=section.id,
        )
        updated_cards.append(updated)

    await db.commit()
    return {
        "section": _serialize_section(section),
        "cards": [_serialize_card(c) for c in updated_cards],
    }

@router.post("/{board_id}/sections/{section_id}/ungroup")
async def ungroup_section(
    board_id: str,
    section_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ungroup a section: convert child cards to absolute positions and delete section."""
    from sqlalchemy import select as sa_select
    from ..database.models import Card

    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    sid = parse_uuid(section_id, "section_id")
    section = await sections_crud.get_section_by_id(db, sid, board.id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Fetch child cards
    result = await db.execute(
        sa_select(Card).where(Card.board_id == board.id, Card.section_id == sid)
    )
    child_cards = list(result.scalars().all())

    # Convert positions back to absolute
    header_offset = 44
    updated_cards = []
    for card in child_cards:
        abs_x = card.position_x + section.x
        abs_y = card.position_y + section.y + header_offset
        updated = await boards_crud.update_card(
            db, card.id, board.id,
            position_x=abs_x, position_y=abs_y, section_id=None,
        )
        updated_cards.append(updated)

    # Delete section
    await sections_crud.delete_section(db, sid, board.id)
    await db.commit()
    return {
        "cards": [_serialize_card(c) for c in updated_cards],
    }

@router.patch("/{board_id}/sections/{section_id}")
async def update_section_endpoint(
    board_id: str,
    section_id: str,
    request: UpdateSectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
    section = await sections_crud.update_section(db, parse_uuid(section_id, "section_id"), board.id, **kwargs)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    await db.commit()
    asyncio.create_task(collab_manager.broadcast_to_board(
        parse_uuid(board_id, "board_id"),
        {"type": "section_updated", "section_id": str(section_id), "board_id": board_id},
        exclude_user=current_user.id,
    ))
    return _serialize_section(section)

@router.delete("/{board_id}/sections/{section_id}")
async def delete_section_endpoint(
    board_id: str,
    section_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select as sa_select
    from ..database.models import Card

    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    sid = parse_uuid(section_id, "section_id")

    # Convert child card positions to absolute before deleting section
    section = await sections_crud.get_section_by_id(db, sid, board.id)
    if section:
        result = await db.execute(
            sa_select(Card).where(Card.board_id == board.id, Card.section_id == sid)
        )
        child_cards = list(result.scalars().all())
        header_offset = 36
        for card in child_cards:
            abs_x = card.position_x + section.x
            abs_y = card.position_y + section.y + header_offset
            await boards_crud.update_card(
                db, card.id, board.id,
                position_x=abs_x, position_y=abs_y, section_id=None
            )

    deleted = await sections_crud.delete_section(db, sid, board.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Section not found")
    await db.commit()
    return {"status": "deleted"}


# ──────────────────────────────────────────────
# Nested Board endpoints
# ──────────────────────────────────────────────

@router.get("/{board_id}/children")
async def list_board_children(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    children = await boards_crud.get_board_children(db, board.id, current_user.id)
    return {"children": [_serialize_board(b) for b in children]}

@router.get("/{board_id}/breadcrumbs")
async def get_board_breadcrumbs(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    crumbs = await boards_crud.get_board_breadcrumbs(db, board.id, current_user.id)
    return {"breadcrumbs": crumbs}

@router.post("/{board_id}/create-child", status_code=status.HTTP_201_CREATED)
async def create_child_board(
    board_id: str,
    request: CreateChildBoardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    parent = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent board not found")
    child = await boards_crud.create_child_board(db, parent.id, current_user.id, request.name, description=request.description)
    await db.commit()
    return _serialize_board(child)

@router.put("/{board_id}/move")
async def move_board(
    board_id: str,
    request: MoveBoardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    new_parent_id = parse_uuid(request.new_parent_id, "new_parent_id") if request.new_parent_id else None
    moved = await boards_crud.move_board(db, board.id, current_user.id, new_parent_id)
    if not moved:
        raise HTTPException(status_code=400, detail="Failed to move board")
    await db.commit()
    return _serialize_board(moved)


# ──────────────────────────────────────────────
# Journal endpoints
# ──────────────────────────────────────────────

@router.post("/{board_id}/journal", status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    board_id: str,
    request: CreateJournalEntryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_type
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    journal_date = date_type.fromisoformat(request.date) if request.date else date_type.today()
    card = await boards_crud.create_journal_entry(
        db, board.id, current_user.id,
        journal_date=journal_date,
        content=request.content or "",
        title=request.title,
    )
    await db.commit()
    return _serialize_card(card)

@router.get("/{board_id}/journal")
async def list_journal_entries(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    entries = await boards_crud.list_journal_entries(db, board.id, current_user.id)
    return {"entries": [_serialize_card(c) for c in entries]}


# ──────────────────────────────────────────────
# Inbox endpoints
# ──────────────────────────────────────────────

@router.post("/{board_id}/inbox", status_code=status.HTTP_201_CREATED)
async def create_inbox_item(
    board_id: str,
    request: CreateInboxItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    card = await boards_crud.create_inbox_item(
        db, board.id, current_user.id,
        content=request.content,
        title=request.title,
    )
    await db.commit()
    return _serialize_card(card)

@router.get("/{board_id}/inbox")
async def list_inbox_items(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    items = await boards_crud.list_inbox_items(db, board.id, current_user.id)
    return {"items": [_serialize_card(c) for c in items]}

@router.patch("/{board_id}/inbox/{card_id}/process")
async def process_inbox_item(
    board_id: str,
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    card = await boards_crud.process_inbox_item(db, parse_uuid(card_id, "card_id"), board.id)
    if not card:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    await db.commit()
    return _serialize_card(card)


# ──────────────────────────────────────────────
# Chat → Canvas endpoints (Phase 3)
# ──────────────────────────────────────────────

@router.post("/{board_id}/cards/from-message", status_code=status.HTTP_201_CREATED)
async def create_card_from_message(
    board_id: str,
    request: CreateCardFromMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a card from a conversation message."""
    from ..database.models import Message, Conversation
    from sqlalchemy import select

    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    # Verify conversation ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == parse_uuid(request.conversation_id, "conversation_id"),
            Conversation.user_id == current_user.id
        )
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Load message
    msg_result = await db.execute(
        select(Message).where(Message.id == parse_uuid(request.message_id, "message_id"))
    )
    msg = msg_result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    # Extract content based on card_type
    title = None
    content = None
    extra = request.extra or {}

    if request.card_type == "query":
        content = msg.content
        title = (content[:80] + "...") if content and len(content) > 80 else content
    elif request.card_type == "council_response" and msg.stage1:
        model_name = extra.get("model")
        if model_name and isinstance(msg.stage1, list):
            for resp in msg.stage1:
                if resp.get("model") == model_name:
                    content = resp.get("response", "")
                    title = model_name.split("/")[-1]
                    extra["model"] = model_name
                    break
        if not content and isinstance(msg.stage1, list) and msg.stage1:
            resp = msg.stage1[0]
            content = resp.get("response", "")
            title = resp.get("model", "Response").split("/")[-1]
            extra["model"] = resp.get("model", "")
    elif request.card_type == "council_synthesis" and msg.stage3:
        content = msg.stage3.get("response", "")
        model_name = msg.stage3.get("model", "Chairman")
        title = f"Synthesis ({model_name.split('/')[-1]})"
        extra["model"] = model_name

    card = await boards_crud.create_card(
        db, board.id,
        card_type=request.card_type,
        title=title,
        content=content,
        position_x=request.position_x,
        position_y=request.position_y,
        source_message_id=msg.id,
        source_conversation_id=conv.id,
        extra=extra,
    )
    await db.commit()
    return _serialize_card(card)


@router.post("/{board_id}/cards/from-council-turn", status_code=status.HTTP_201_CREATED)
async def create_cards_from_council_turn(
    board_id: str,
    request: CreateCardsFromTurnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk create cards from a full council turn (query + responses + synthesis + edges)."""
    from ..database.models import Message, Conversation
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    # Load conversation with messages
    conv_result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == parse_uuid(request.conversation_id, "conversation_id"),
            Conversation.user_id == current_user.id
        )
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Find the user message and assistant message at this index
    user_msg = None
    assistant_msg = None
    for msg in conv.messages:
        if msg.message_index == request.message_index and msg.role == "user":
            user_msg = msg
        elif msg.message_index == request.message_index and msg.role == "assistant":
            assistant_msg = msg
    # If messages are at consecutive indices (user at N, assistant at N+1)
    if not assistant_msg:
        for msg in conv.messages:
            if msg.message_index == request.message_index + 1 and msg.role == "assistant":
                assistant_msg = msg
                break
    if not user_msg:
        for msg in conv.messages:
            if msg.message_index == request.message_index - 1 and msg.role == "user":
                user_msg = msg
                break

    if not assistant_msg:
        raise HTTPException(status_code=404, detail="Assistant message not found at this index")

    created_cards = []
    created_edges = []
    base_x = request.base_position_x
    base_y = request.base_position_y
    spacing_x = 320
    row_offset = 280

    # 1. Query card
    query_card = None
    if request.include_query and user_msg:
        query_text = user_msg.content or ""
        query_card = await boards_crud.create_card(
            db, board.id,
            card_type="query",
            title=(query_text[:80] + "...") if len(query_text) > 80 else query_text,
            content=query_text,
            position_x=base_x,
            position_y=base_y,
            source_message_id=user_msg.id,
            source_conversation_id=conv.id,
        )
        created_cards.append(query_card)

    # 2. Response cards
    response_cards = []
    if request.include_responses and assistant_msg.stage1 and isinstance(assistant_msg.stage1, list):
        responses = assistant_msg.stage1
        total_width = (len(responses) - 1) * spacing_x
        start_x = base_x - total_width / 2

        for i, resp in enumerate(responses):
            model_name = resp.get("model", f"Model {i+1}")
            card = await boards_crud.create_card(
                db, board.id,
                card_type="council_response",
                title=model_name.split("/")[-1],
                content=resp.get("response", ""),
                position_x=start_x + i * spacing_x,
                position_y=base_y + row_offset,
                source_message_id=assistant_msg.id,
                source_conversation_id=conv.id,
                extra={"model": model_name, "stage": 1, "index": i},
            )
            response_cards.append(card)
            created_cards.append(card)

            # Edge: query → response
            if query_card:
                edge = await boards_crud.create_edge(
                    db, board.id, query_card.id, card.id,
                    edge_type="derived_from"
                )
                created_edges.append(edge)

    # 3. Synthesis card
    synthesis_card = None
    if request.include_synthesis and assistant_msg.stage3:
        synth_model = assistant_msg.stage3.get("model", "Chairman")
        synthesis_card = await boards_crud.create_card(
            db, board.id,
            card_type="council_synthesis",
            title=f"Synthesis ({synth_model.split('/')[-1]})",
            content=assistant_msg.stage3.get("response", ""),
            position_x=base_x,
            position_y=base_y + row_offset * 2,
            source_message_id=assistant_msg.id,
            source_conversation_id=conv.id,
            extra={"model": synth_model, "stage": 3},
        )
        created_cards.append(synthesis_card)

        # Edges: each response → synthesis
        for resp_card in response_cards:
            edge = await boards_crud.create_edge(
                db, board.id, resp_card.id, synthesis_card.id,
                edge_type="synthesizes"
            )
            created_edges.append(edge)

    await db.commit()

    return {
        "cards": [_serialize_card(c) for c in created_cards],
        "edges": [_serialize_edge(e) for e in created_edges],
    }


# ──────────────────────────────────────────────
# Board Context Helper
# ──────────────────────────────────────────────

MAX_KNOWLEDGE_CARDS = 10
MAX_KNOWLEDGE_CHARS = 2000


async def _get_board_context(board, db: AsyncSession) -> Optional[str]:
    """Build context string from board's linked project and knowledge cards."""
    sections = []

    # Project context (system_prompt + KB + memory)
    if board.project_id:
        from ..database.crud import projects as projects_crud
        project = await projects_crud.get_by_id(db, board.project_id)
        if project:
            from ..database.crud.projects import get_project_context
            ctx = get_project_context(project)
            if ctx:
                sections.append(ctx)

    # Board memory (if column exists)
    board_memory = getattr(board, "memory", None) or {}
    memory_parts = []
    facts = board_memory.get("facts", [])
    if facts:
        fact_list = "\n".join(f"- {f.get('content', f)}" for f in facts[-10:])
        memory_parts.append(f"**Board Facts:**\n{fact_list}")
    decisions = board_memory.get("decisions", [])
    if decisions:
        dec_list = "\n".join(f"- {d.get('content', d)}" for d in decisions[-5:])
        memory_parts.append(f"**Board Decisions:**\n{dec_list}")
    if memory_parts:
        sections.append("\n\n".join(memory_parts))

    # Knowledge cards on this board
    all_cards = await boards_crud.list_cards(db, board.id)
    knowledge_cards = [
        c for c in all_cards
        if c.extra and c.extra.get("is_knowledge")
    ][:MAX_KNOWLEDGE_CARDS]
    if knowledge_cards:
        kb_parts = []
        for kc in knowledge_cards:
            label = kc.title or "Reference"
            content = (kc.content or "")[:MAX_KNOWLEDGE_CHARS]
            kb_parts.append(f"### {label}\n{content}")
        sections.append("**Board Knowledge:**\n" + "\n\n".join(kb_parts))

    return "\n\n---\n\n".join(sections) if sections else None


# ──────────────────────────────────────────────
# Council from Board
# ──────────────────────────────────────────────

class RunCouncilFromBoardRequest(BaseModel):
    query: str = Field(..., min_length=1)
    card_ids: List[str] = Field(default_factory=list)
    web_search: bool = False
    fast_mode: bool = False


def _json_sse(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


@router.post("/{board_id}/council", summary="Run council from board context")
async def run_council_from_board(
    board_id: str,
    request: RunCouncilFromBoardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a council deliberation using selected board cards as context.

    Returns an SSE stream identical to the conversation council endpoint.
    On completion, creates result cards and edges on the board automatically.
    """
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    # Build context from selected cards
    context_parts = []
    for cid_str in request.card_ids:
        card = await boards_crud.get_card_by_id(db, parse_uuid(cid_str, "card_id"), board.id)
        if card:
            label = card.title or card.card_type
            context_parts.append(f"[{label}]\n{card.content or ''}")

    # Include board memory facts and decisions
    board_memory = board.memory if hasattr(board, 'memory') and board.memory else {}
    if board_memory.get("facts"):
        fact_items = [f.get("content", str(f)) if isinstance(f, dict) else str(f) for f in board_memory["facts"][-10:]]
        context_parts.append("**Board Memory (Facts):**\n" + "\n".join(f"- {item}" for item in fact_items))
    if board_memory.get("decisions"):
        dec_items = [d.get("content", str(d)) if isinstance(d, dict) else str(d) for d in board_memory["decisions"][-5:]]
        context_parts.append("**Board Memory (Decisions):**\n" + "\n".join(f"- {item}" for item in dec_items))

    card_context = "\n\n---\n\n".join(context_parts) if context_parts else None

    from ..council.orchestration import run_full_council_stream

    async def event_generator():
        stage1_results = None
        stage2_results = None
        stage3_result = None
        metadata = None

        try:
            async for event in run_full_council_stream(
                request.query,
                conversation_context=card_context,
                web_search=request.web_search,
                user_id=current_user.id,
                db=db,
                fast_mode=request.fast_mode,
                project_id=str(board.project_id) if board.project_id else None,
            ):
                yield f"data: {_json_sse(event)}\n\n"

                if event.get("type") == "stage1_complete":
                    stage1_results = event.get("data", [])
                elif event.get("type") == "stage2_complete":
                    stage2_results = event.get("data", [])
                    metadata = event.get("metadata", {})
                elif event.get("type") == "stage3_complete":
                    stage3_result = event.get("data", {})
                elif event.get("type") == "complete":
                    stage1_results = event.get("stage1", stage1_results)
                    stage2_results = event.get("stage2", stage2_results)
                    stage3_result = event.get("stage3", stage3_result)
                    metadata = event.get("metadata", metadata)

            # Auto-create cards on board from results
            if stage1_results and stage3_result:
                created_cards = []
                created_edges = []

                # Get existing card count for positioning
                existing = await boards_crud.list_cards(db, board.id)
                base_x = 200.0
                base_y = max((c.position_y for c in existing), default=0) + 400

                # Query card
                query_card = await boards_crud.create_card(
                    db, board.id, card_type="query", title="Query",
                    content=request.query,
                    position_x=base_x + 200, position_y=base_y,
                )
                created_cards.append(query_card)

                # Response cards
                spacing = 280
                total_width = (len(stage1_results) - 1) * spacing
                start_x = base_x + 200 - total_width / 2

                response_cards = []
                for idx, resp in enumerate(stage1_results):
                    model = resp.get("model", "unknown")
                    card = await boards_crud.create_card(
                        db, board.id, card_type="council_response",
                        title=model.split("/")[-1],
                        content=resp.get("response", ""),
                        position_x=start_x + idx * spacing,
                        position_y=base_y + 250,
                        extra={"model": model},
                    )
                    response_cards.append(card)
                    created_cards.append(card)

                    edge = await boards_crud.create_edge(
                        db, board.id, query_card.id, card.id,
                        edge_type="derived_from"
                    )
                    created_edges.append(edge)

                # Synthesis card
                synth_content = stage3_result.get("response", "")
                synth_model = stage3_result.get("model", "chairman")
                synthesis_card = await boards_crud.create_card(
                    db, board.id, card_type="council_synthesis",
                    title="Council Synthesis",
                    content=synth_content,
                    position_x=base_x + 200,
                    position_y=base_y + 500,
                    extra={
                        "model": synth_model,
                        "stage1": stage1_results,
                        "stage2": stage2_results,
                        "metadata": metadata,
                    },
                )
                created_cards.append(synthesis_card)

                for rc in response_cards:
                    edge = await boards_crud.create_edge(
                        db, board.id, rc.id, synthesis_card.id,
                        edge_type="synthesizes"
                    )
                    created_edges.append(edge)

                # Edges from context cards to query
                for cid_str in request.card_ids:
                    try:
                        edge = await boards_crud.create_edge(
                            db, board.id, parse_uuid(cid_str, "card_id"), query_card.id,
                            edge_type="related"
                        )
                        created_edges.append(edge)
                    except Exception:
                        pass

                # Auto-save council decision to board memory
                try:
                    await boards_crud.add_board_decision(
                        db, board.id, current_user.id,
                        decision=synth_content[:500],
                        context=request.query[:200],
                    )
                except Exception:
                    pass  # Non-critical, don't fail the whole operation

                await db.commit()

                # Emit board_update event with new cards/edges
                yield f"data: {_json_sse({'type': 'board_update', 'cards': [_serialize_card(c) for c in created_cards], 'edges': [_serialize_edge(e) for e in created_edges]})}\n\n"

        except Exception as e:
            logger.exception("Council from board failed")
            yield f"data: {_json_sse({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ──────────────────────────────────────────────
# Card AI Actions
# ──────────────────────────────────────────────

class CardAIActionRequest(BaseModel):
    action: str = Field(..., pattern="^(summarize|expand|key_points|ask_council|mind_map|custom)$")
    custom_prompt: Optional[str] = None
    model: Optional[str] = None
    use_council: bool = False


CLUSTER_COLORS = ["#6366f1", "#f59e0b", "#10b981", "#ef4444", "#3b82f6", "#8b5cf6"]


@router.post("/{board_id}/cards/{card_id}/ai-action", summary="Run AI action on a card")
async def run_card_ai_action(
    board_id: str,
    card_id: str,
    request: CardAIActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run an AI action on a single card. Creates result cards linked to the source."""
    try:
        board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    except Exception as e:
        raise
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    card = await boards_crud.get_card_by_id(db, parse_uuid(card_id, "card_id"), board.id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    from ..council.card_prompts import CARD_AI_PROMPTS
    from ..llm import query_model
    from ..config import get_chairman_model

    card_content = f"{card.title or ''}\n\n{card.content or ''}".strip()
    model_id = request.model or get_chairman_model()

    if request.action == "custom" and not request.custom_prompt:
        raise HTTPException(status_code=400, detail="custom_prompt required for custom action")

    # Build prompt
    template = CARD_AI_PROMPTS.get(request.action, CARD_AI_PROMPTS["custom"])
    if request.action == "custom":
        prompt = template.format(prompt=request.custom_prompt, content=card_content)
    else:
        prompt = template.format(content=card_content)

    # Prepend board/project context if available
    board_context = await _get_board_context(board, db)
    if board_context:
        prompt = f"{board_context}\n\n---\n\n{prompt}"

    # Call LLM
    messages = [{"role": "user", "content": prompt}]
    result = await query_model(model_id, messages, user_id=current_user.id, db=db)

    if not result or not result.get("content"):
        raise HTTPException(status_code=502, detail="AI model returned no response")

    response_text = result["content"]
    created_cards = []
    created_edges = []

    if request.action == "mind_map":
        # Parse JSON array of sub-topics
        try:
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            subtopics = json.loads(json_match.group()) if json_match else []
        except (json.JSONDecodeError, AttributeError):
            subtopics = [{"title": "Mind Map Result", "content": response_text}]

        spacing = 280
        total_width = max((len(subtopics) - 1) * spacing, 0)
        start_x = card.position_x - total_width / 2

        for idx, topic in enumerate(subtopics):
            new_card = await boards_crud.create_card(
                db, board.id, card_type="note",
                title=topic.get("title", f"Topic {idx+1}"),
                content=topic.get("content", ""),
                position_x=start_x + idx * spacing,
                position_y=card.position_y + 250,
                extra={"ai_action": "mind_map", "source_card_id": str(card.id)},
            )
            created_cards.append(new_card)
            edge = await boards_crud.create_edge(
                db, board.id, card.id, new_card.id, edge_type="derived_from"
            )
            created_edges.append(edge)
    else:
        # Single result card
        action_titles = {
            "summarize": "Summary",
            "expand": "Expanded",
            "key_points": "Key Points",
            "ask_council": "Council Response",
            "custom": "AI Response",
        }
        new_card = await boards_crud.create_card(
            db, board.id, card_type="note",
            title=f"{action_titles.get(request.action, 'Result')}: {card.title or 'Card'}",
            content=response_text,
            position_x=card.position_x,
            position_y=card.position_y + 250,
            extra={
                "ai_action": request.action,
                "source_card_id": str(card.id),
                "model": model_id,
            },
        )
        created_cards.append(new_card)
        edge = await boards_crud.create_edge(
            db, board.id, card.id, new_card.id, edge_type="derived_from"
        )
        created_edges.append(edge)

    await db.commit()

    return {
        "cards": [_serialize_card(c) for c in created_cards],
        "edges": [_serialize_edge(e) for e in created_edges],
    }


# ──────────────────────────────────────────────
# Board AI Actions
# ──────────────────────────────────────────────

class BoardAIActionRequest(BaseModel):
    action: str = Field(..., pattern="^(summarize_board|cluster_themes|find_connections)$")
    card_ids: List[str] = Field(default_factory=list)
    model: Optional[str] = None


@router.post("/{board_id}/ai-action", summary="Run AI action on board")
async def run_board_ai_action(
    board_id: str,
    request: BoardAIActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a board-level AI action (summarize, cluster, find connections)."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    from ..council.card_prompts import BOARD_AI_PROMPTS, format_cards_for_prompt
    from ..llm import query_model
    from ..config import get_chairman_model

    # Gather cards
    all_cards = await boards_crud.list_cards(db, board.id)
    if request.card_ids:
        target_ids = set(request.card_ids)
        cards = [c for c in all_cards if str(c.id) in target_ids]
    else:
        cards = list(all_cards)

    if not cards:
        raise HTTPException(status_code=400, detail="No cards to process")

    card_dicts = [{"id": str(c.id), "card_type": c.card_type, "title": c.title, "content": c.content} for c in cards]
    cards_text = format_cards_for_prompt(card_dicts)

    model_id = request.model or get_chairman_model()
    template = BOARD_AI_PROMPTS[request.action]
    prompt = template.format(cards=cards_text)

    # Prepend board/project context if available
    board_context = await _get_board_context(board, db)
    if board_context:
        prompt = f"{board_context}\n\n---\n\n{prompt}"

    messages = [{"role": "user", "content": prompt}]
    result = await query_model(model_id, messages, user_id=current_user.id, db=db)

    if not result or not result.get("content"):
        raise HTTPException(status_code=502, detail="AI model returned no response")

    response_text = result["content"]
    created_cards = []
    created_edges = []
    color_updates = {}

    # Position for new cards
    min_y = min((c.position_y for c in cards), default=0)
    center_x = sum(c.position_x for c in cards) / len(cards)

    if request.action == "summarize_board":
        synth_card = await boards_crud.create_card(
            db, board.id, card_type="council_synthesis",
            title=f"Board Summary ({len(cards)} cards)",
            content=response_text,
            position_x=center_x,
            position_y=min_y - 300,
            extra={"ai_action": "summarize_board", "model": model_id},
        )
        created_cards.append(synth_card)

    elif request.action == "cluster_themes":
        try:
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            clusters = json.loads(json_match.group()) if json_match else []
        except (json.JSONDecodeError, AttributeError):
            clusters = []

        card_id_set = {str(c.id) for c in cards}
        for idx, cluster in enumerate(clusters):
            cluster_name = cluster.get("cluster_name", f"Cluster {idx+1}")
            cluster_desc = cluster.get("description", "")
            cluster_card_ids = [cid for cid in cluster.get("card_ids", []) if cid in card_id_set]

            if not cluster_card_ids:
                continue

            color = CLUSTER_COLORS[idx % len(CLUSTER_COLORS)]

            # Assign color to member cards
            for cid in cluster_card_ids:
                await boards_crud.update_card(db, parse_uuid(cid, "card_id"), board.id, color=color)
                color_updates[cid] = color

            # Create cluster label card
            cluster_members = [c for c in cards if str(c.id) in cluster_card_ids]
            cluster_center_x = sum(c.position_x for c in cluster_members) / len(cluster_members)
            cluster_min_y = min(c.position_y for c in cluster_members)

            label_card = await boards_crud.create_card(
                db, board.id, card_type="note",
                title=cluster_name,
                content=cluster_desc,
                position_x=cluster_center_x,
                position_y=cluster_min_y - 200,
                color=color,
                extra={"ai_action": "cluster_themes", "cluster_index": idx},
            )
            created_cards.append(label_card)

            for cid in cluster_card_ids:
                edge = await boards_crud.create_edge(
                    db, board.id, label_card.id, parse_uuid(cid, "card_id"),
                    edge_type="related", label="grouped"
                )
                created_edges.append(edge)

    elif request.action == "find_connections":
        try:
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            connections = json.loads(json_match.group()) if json_match else []
        except (json.JSONDecodeError, AttributeError):
            connections = []

        card_id_set = {str(c.id) for c in cards}
        for conn in connections:
            from_id = conn.get("from_id", "")
            to_id = conn.get("to_id", "")
            label = conn.get("label", "")
            if from_id in card_id_set and to_id in card_id_set and from_id != to_id:
                try:
                    edge = await boards_crud.create_edge(
                        db, board.id, parse_uuid(from_id, "from_card_id"), parse_uuid(to_id, "to_card_id"),
                        edge_type="related", label=label
                    )
                    created_edges.append(edge)
                except Exception:
                    pass  # Skip duplicate edges

    await db.commit()

    return {
        "cards": [_serialize_card(c) for c in created_cards],
        "edges": [_serialize_edge(e) for e in created_edges],
        "color_updates": color_updates if color_updates else None,
    }


# ──────────────────────────────────────────────
# Snapshot / Version History endpoints
# ──────────────────────────────────────────────

def _serialize_snapshot(snap, include_data: bool = False) -> dict:
    """Serialize a snapshot to a dict. Works with both full ORM objects and row tuples."""
    if hasattr(snap, "snapshot_data"):
        # Full ORM object
        data = {
            "id": str(snap.id),
            "board_id": str(snap.board_id),
            "user_id": str(snap.user_id),
            "name": snap.name,
            "description": snap.description,
            "trigger": snap.trigger,
            "card_count": snap.card_count,
            "edge_count": snap.edge_count,
            "section_count": snap.section_count,
            "created_at": snap.created_at.isoformat() if snap.created_at else None,
        }
        if include_data:
            data["snapshot_data"] = snap.snapshot_data
        return data
    else:
        # Row tuple from list query (id, board_id, user_id, name, description, trigger, card_count, edge_count, section_count, created_at)
        return {
            "id": str(snap[0]),
            "board_id": str(snap[1]),
            "user_id": str(snap[2]),
            "name": snap[3],
            "description": snap[4],
            "trigger": snap[5],
            "card_count": snap[6],
            "edge_count": snap[7],
            "section_count": snap[8],
            "created_at": snap[9].isoformat() if snap[9] else None,
        }


async def _maybe_auto_snapshot(
    db: AsyncSession,
    board_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Create an auto snapshot if the last one was more than 5 minutes ago."""
    from datetime import datetime, timedelta, timezone as tz
    last_time = await snapshots_crud.get_last_auto_snapshot_time(db, board_id)
    now = datetime.now(tz.utc)
    if last_time is None or (now - last_time) > timedelta(minutes=5):
        await snapshots_crud.capture_snapshot(db, board_id, user_id, trigger="auto")


@router.get("/{board_id}/snapshots")
async def list_snapshots_endpoint(
    board_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List snapshots for a board (metadata only)."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    snaps = await snapshots_crud.list_snapshots(db, board.id, limit=limit)
    return {"snapshots": [_serialize_snapshot(s) for s in snaps]}


@router.post("/{board_id}/snapshots", status_code=status.HTTP_201_CREATED)
async def create_snapshot_endpoint(
    board_id: str,
    request: CreateSnapshotRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual snapshot of the board."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    snap = await snapshots_crud.capture_snapshot(
        db, board.id, current_user.id,
        trigger="manual",
        name=request.name,
        description=request.description,
    )
    await db.commit()
    return _serialize_snapshot(snap, include_data=False)


@router.get("/{board_id}/snapshots/{snapshot_id}")
async def get_snapshot_endpoint(
    board_id: str,
    snapshot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a snapshot with full data."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    snap = await snapshots_crud.get_snapshot(db, parse_uuid(snapshot_id, "snapshot_id"))
    if not snap or snap.board_id != board.id:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return _serialize_snapshot(snap, include_data=True)


@router.post("/{board_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot_endpoint(
    board_id: str,
    snapshot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restore a board to a snapshot state. Creates a safety snapshot first."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    safety_snap = await snapshots_crud.restore_snapshot(
        db, parse_uuid(snapshot_id, "snapshot_id"), board.id, current_user.id
    )
    if not safety_snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    await db.commit()

    return {
        "status": "restored",
        "safety_snapshot_id": str(safety_snap.id),
    }


@router.delete("/{board_id}/snapshots/{snapshot_id}")
async def delete_snapshot_endpoint(
    board_id: str,
    snapshot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a snapshot."""
    board = await boards_crud.get_board_by_id(db, parse_uuid(board_id, "board_id"), current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    deleted = await snapshots_crud.delete_snapshot(db, parse_uuid(snapshot_id, "snapshot_id"))
    if not deleted:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    await db.commit()
    return {"status": "deleted"}