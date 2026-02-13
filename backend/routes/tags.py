"""Tag CRUD routes."""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from ..database.crud import tags as tags_crud
from ..auth.dependencies import get_current_user
from ..utils import parse_uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tags", tags=["tags"])


# ──────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────

class CreateTagRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#4a90e2", max_length=20)
    collection: Optional[str] = Field(None, max_length=50)


class UpdateTagRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    collection: Optional[str] = None


# ──────────────────────────────────────────────
# Serialization
# ──────────────────────────────────────────────

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
# Tag endpoints
# ──────────────────────────────────────────────

@router.get("")
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tags for the current user."""
    tags = await tags_crud.list_user_tags(db, current_user.id)
    return {"tags": [_serialize_tag(t) for t in tags]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tag(
    request: CreateTagRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tag."""
    tag = await tags_crud.create_tag(
        db, current_user.id, request.name,
        color=request.color, collection=request.collection,
    )
    return _serialize_tag(tag)


@router.patch("/{tag_id}")
async def update_tag(
    tag_id: str,
    request: UpdateTagRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a tag."""
    tid = parse_uuid(tag_id, "tag_id")
    updates = request.model_dump(exclude_none=True)
    tag = await tags_crud.update_tag(db, tid, current_user.id, **updates)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return _serialize_tag(tag)


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a tag."""
    tid = parse_uuid(tag_id, "tag_id")
    deleted = await tags_crud.delete_tag(db, tid, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"ok": True}
