"""API routes for cross-board linked cards and global card search."""

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User, Board, Card
from ..database import crud as db_crud
from ..auth.dependencies import get_current_user
from ..utils import parse_uuid

router = APIRouter(prefix="/api", tags=["card-search"])


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────

class LinkCloneRequest(BaseModel):
    """Body for link and clone operations."""
    target_board_id: str
    position_x: float = 0.0
    position_y: float = 0.0


class CardBriefResponse(BaseModel):
    """Abbreviated card representation for search results and linked lists."""
    id: str
    board_id: str
    board_name: Optional[str] = None
    card_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    is_library: bool = False
    source_card_id: Optional[str] = None
    position_x: float = 0.0
    position_y: float = 0.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _serialize_card(card: Card, board_name: Optional[str] = None) -> dict:
    """Convert a Card ORM object to a JSON-safe dict."""
    return {
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
        "width": card.width,
        "height": card.height,
        "extra": card.extra,
        "created_at": card.created_at.isoformat() if card.created_at else None,
        "updated_at": card.updated_at.isoformat() if card.updated_at else None,
    }


# ──────────────────────────────────────────────
# LITERAL routes FIRST (before parameterized routes)
# This prevents FastAPI from matching "search" as a {card_id}.
# ──────────────────────────────────────────────

@router.get("/cards/search")
async def search_cards(
    q: Optional[str] = Query(None, description="Search query (ILIKE on title+content)"),
    card_type: Optional[str] = Query(None, description="Filter by card_type"),
    tag_ids: Optional[str] = Query(None, description="Comma-separated tag UUIDs (AND filter)"),
    is_library: Optional[bool] = Query(None, description="Filter by is_library flag"),
    limit: int = Query(20, ge=1, le=100, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cross-board card search with optional filters.

    Searches across all boards owned by the authenticated user.
    Supports text search, card_type filter, tag filter, and library filter.
    """
    # Parse tag_ids from comma-separated string
    parsed_tag_ids: Optional[List[uuid.UUID]] = None
    if tag_ids:
        try:
            parsed_tag_ids = [uuid.UUID(tid.strip()) for tid in tag_ids.split(",") if tid.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tag_ids format. Expected comma-separated UUIDs.",
            )

    cards, total = await db_crud.card_search.search_cards(
        db,
        user_id=current_user.id,
        q=q,
        card_type=card_type,
        tag_ids=parsed_tag_ids,
        is_library=is_library,
        limit=limit,
        offset=offset,
    )

    return {
        "cards": cards,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ──────────────────────────────────────────────
# PARAMETERIZED routes (after literal routes)
# ──────────────────────────────────────────────

@router.post("/cards/{card_id}/link", status_code=status.HTTP_201_CREATED)
async def link_card(
    card_id: str,
    request: LinkCloneRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a linked card on a target board that mirrors the source card.

    The linked card maintains a reference to the source and can be synced
    to receive updates when the source card's title or content changes.
    """
    # Verify the target board belongs to the user
    target_board = await db_crud.boards.get_board_by_id(
        db, parse_uuid(request.target_board_id, "target_board_id"), current_user.id
    )
    if not target_board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target board not found or not owned by user",
        )

    try:
        linked = await db_crud.card_search.create_linked_card(
            db,
            source_card_id=parse_uuid(card_id, "card_id"),
            target_board_id=parse_uuid(request.target_board_id, "target_board_id"),
            position_x=request.position_x,
            position_y=request.position_y,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    await db.commit()
    return _serialize_card(linked, board_name=target_board.name)


@router.post("/cards/{card_id}/clone", status_code=status.HTTP_201_CREATED)
async def clone_card(
    card_id: str,
    request: LinkCloneRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deep copy a card to a target board with no link.

    The cloned card is fully independent -- changes to the original
    do not propagate to the clone.
    """
    # Verify the target board belongs to the user
    target_board = await db_crud.boards.get_board_by_id(
        db, parse_uuid(request.target_board_id, "target_board_id"), current_user.id
    )
    if not target_board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target board not found or not owned by user",
        )

    try:
        cloned = await db_crud.card_search.clone_card(
            db,
            source_card_id=parse_uuid(card_id, "card_id"),
            target_board_id=parse_uuid(request.target_board_id, "target_board_id"),
            position_x=request.position_x,
            position_y=request.position_y,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    await db.commit()
    return _serialize_card(cloned, board_name=target_board.name)


@router.post("/cards/{card_id}/unlink")
async def unlink_card(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Break the link on a linked card.

    Sets source_card_id to null and changes card_type to 'note',
    making the card fully independent.
    """
    card = await db_crud.card_search.unlink_card(db, parse_uuid(card_id, "card_id"))
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )

    await db.commit()
    return _serialize_card(card)


@router.post("/cards/{card_id}/sync")
async def sync_linked_cards(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force-sync all linked instances from the source card.

    Updates title and content on every card whose source_card_id
    points to this card.
    """
    synced_count = await db_crud.card_search.sync_linked_cards(
        db, parse_uuid(card_id, "card_id")
    )
    await db.commit()
    return {"synced": synced_count, "source_card_id": card_id}


@router.get("/cards/{card_id}/linked")
async def get_linked_instances(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all cards that are linked to (mirror) the given source card."""
    instances = await db_crud.card_search.get_linked_instances(
        db, parse_uuid(card_id, "card_id")
    )
    return {
        "source_card_id": card_id,
        "linked_count": len(instances),
        "linked_cards": [_serialize_card(c) for c in instances],
    }


@router.patch("/cards/{card_id}/library")
async def toggle_library(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the is_library flag on a card.

    Library cards appear in the Global Library panel and can be
    linked or cloned to other boards.
    """
    result = await db_crud.card_search.toggle_library(db, parse_uuid(card_id, "card_id"))
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )

    await db.commit()
    return result
