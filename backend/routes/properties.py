"""Property definition and card property value routes."""

import uuid
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from ..database.crud import properties as properties_crud
from ..database.crud import boards as boards_crud
from ..auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/boards", tags=["properties"])


# ──────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────

class CreatePropertyDefRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    property_type: str = Field(...)
    options: Optional[dict] = None
    sort_order: int = 0


class UpdatePropertyDefRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    property_type: Optional[str] = None
    options: Optional[dict] = None
    sort_order: Optional[int] = None


class BulkSetPropertiesRequest(BaseModel):
    values: Dict[str, Any]  # { property_id: value }


# ──────────────────────────────────────────────
# Serialization
# ──────────────────────────────────────────────

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


def _serialize_property_value(val) -> dict:
    return {
        "id": str(val.id),
        "card_id": str(val.card_id),
        "property_id": str(val.property_id),
        "value": val.value,
    }


# ──────────────────────────────────────────────
# Property Definition endpoints
# ──────────────────────────────────────────────

# CRITICAL: Literal paths BEFORE parameterized paths (FastAPI route ordering)

@router.get("/{board_id}/properties")
async def list_property_definitions(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all property definitions for a board."""
    bid = uuid.UUID(board_id)
    board = await boards_crud.get_board_by_id(db, bid, current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    props = await properties_crud.list_property_definitions(db, bid)
    return {"properties": [_serialize_property_def(p) for p in props]}


@router.post("/{board_id}/properties", status_code=status.HTTP_201_CREATED)
async def create_property_definition(
    board_id: str,
    request: CreatePropertyDefRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new property definition on a board."""
    bid = uuid.UUID(board_id)
    board = await boards_crud.get_board_by_id(db, bid, current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    valid_types = {"text", "number", "select", "multi_select", "date", "checkbox", "url", "email", "relation"}
    if request.property_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid property type. Must be one of: {', '.join(sorted(valid_types))}")

    prop = await properties_crud.create_property_definition(
        db, bid, request.name, request.property_type,
        options=request.options, sort_order=request.sort_order,
    )
    return _serialize_property_def(prop)


@router.get("/{board_id}/properties/all-values")
async def get_all_property_values(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all property values for all cards on a board (for table/kanban views)."""
    bid = uuid.UUID(board_id)
    board = await boards_crud.get_board_by_id(db, bid, current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    values = await properties_crud.get_all_card_properties_for_board(db, bid)
    return {"values": [_serialize_property_value(v) for v in values]}


@router.patch("/{board_id}/properties/{prop_id}")
async def update_property_definition(
    board_id: str,
    prop_id: str,
    request: UpdatePropertyDefRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a property definition."""
    bid = uuid.UUID(board_id)
    pid = uuid.UUID(prop_id)
    board = await boards_crud.get_board_by_id(db, bid, current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    updates = request.model_dump(exclude_none=True)
    if updates.get("property_type"):
        valid_types = {"text", "number", "select", "multi_select", "date", "checkbox", "url", "email", "relation"}
        if updates["property_type"] not in valid_types:
            raise HTTPException(status_code=400, detail="Invalid property type")

    prop = await properties_crud.update_property_definition(db, pid, bid, **updates)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return _serialize_property_def(prop)


@router.delete("/{board_id}/properties/{prop_id}")
async def delete_property_definition(
    board_id: str,
    prop_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a property definition and all its values."""
    bid = uuid.UUID(board_id)
    pid = uuid.UUID(prop_id)
    board = await boards_crud.get_board_by_id(db, bid, current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    deleted = await properties_crud.delete_property_definition(db, pid, bid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"ok": True}


# ──────────────────────────────────────────────
# Card Property Value endpoints
# ──────────────────────────────────────────────

@router.get("/{board_id}/cards/{card_id}/properties")
async def get_card_properties(
    board_id: str,
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all property values for a card."""
    bid = uuid.UUID(board_id)
    cid = uuid.UUID(card_id)
    board = await boards_crud.get_board_by_id(db, bid, current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    values = await properties_crud.get_card_property_values(db, cid)
    return {"values": [_serialize_property_value(v) for v in values]}


@router.put("/{board_id}/cards/{card_id}/properties")
async def bulk_set_card_properties(
    board_id: str,
    card_id: str,
    request: BulkSetPropertiesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set multiple property values on a card (upsert)."""
    bid = uuid.UUID(board_id)
    cid = uuid.UUID(card_id)
    board = await boards_crud.get_board_by_id(db, bid, current_user.id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    values = await properties_crud.bulk_set_card_properties(db, cid, request.values)
    return {"values": [_serialize_property_value(v) for v in values]}
