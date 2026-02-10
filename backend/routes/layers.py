"""Knowledge layer CRUD routes."""

import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..database.models import User
from ..database.crud import knowledge_layers as kl_crud
from ..database.crud import document_chunks as dc_crud
from ..auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/layers", tags=["layers"])


# ──────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────

class CreateLayerRequest(BaseModel):
    project_id: str
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    persona_prompt: Optional[str] = Field(default=None, max_length=10000)
    methodology_prompt: Optional[str] = Field(default=None, max_length=10000)
    color: str = Field(default="blue", max_length=20)
    icon: str = Field(default="book", max_length=20)


class UpdateLayerRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    persona_prompt: Optional[str] = None
    methodology_prompt: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None


class AssignDocumentsRequest(BaseModel):
    document_ids: List[str]


class ReorderRequest(BaseModel):
    project_id: str
    layer_ids: List[str]


# ──────────────────────────────────────────────
# Serialization
# ──────────────────────────────────────────────

def _serialize_layer(layer) -> dict:
    return {
        "id": str(layer.id),
        "project_id": str(layer.project_id),
        "name": layer.name,
        "description": layer.description,
        "persona_prompt": layer.persona_prompt,
        "methodology_prompt": layer.methodology_prompt,
        "color": layer.color,
        "icon": layer.icon,
        "sort_order": layer.sort_order,
        "is_active": layer.is_active,
        "created_at": layer.created_at.isoformat() if layer.created_at else None,
    }


# ──────────────────────────────────────────────
# Layer endpoints — literal routes FIRST
# ──────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_layer(
    request: CreateLayerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new knowledge layer for a project."""
    try:
        project_id = uuid.UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    layer = await kl_crud.create_layer(
        db, project_id, request.name,
        description=request.description,
        persona_prompt=request.persona_prompt,
        methodology_prompt=request.methodology_prompt,
        color=request.color,
        icon=request.icon,
    )
    await db.commit()
    return _serialize_layer(layer)


@router.get("/project/{project_id}")
async def list_layers(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge layers for a project."""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    layers = await kl_crud.list_layers(db, pid)

    # Get chunk counts per layer
    layer_counts = await dc_crud.get_layer_chunk_counts(db, pid)

    result = []
    for layer in layers:
        data = _serialize_layer(layer)
        data["chunk_count"] = layer_counts.get(str(layer.id), 0)
        result.append(data)

    return {"layers": result}


@router.post("/reorder")
async def reorder_layers(
    request: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder layers for a project."""
    try:
        pid = uuid.UUID(request.project_id)
        lids = [uuid.UUID(lid) for lid in request.layer_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    await kl_crud.reorder_layers(db, pid, lids)
    await db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────
# Parameterized routes AFTER literal routes
# ──────────────────────────────────────────────

@router.get("/{layer_id}")
async def get_layer(
    layer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single knowledge layer."""
    try:
        lid = uuid.UUID(layer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid layer_id format")

    layer = await kl_crud.get_layer(db, lid)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    return _serialize_layer(layer)


@router.patch("/{layer_id}")
async def update_layer(
    layer_id: str,
    request: UpdateLayerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a knowledge layer."""
    try:
        lid = uuid.UUID(layer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid layer_id format")

    updates = request.model_dump(exclude_none=True)
    layer = await kl_crud.update_layer(db, lid, **updates)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    await db.commit()
    return _serialize_layer(layer)


@router.delete("/{layer_id}")
async def delete_layer(
    layer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a knowledge layer."""
    try:
        lid = uuid.UUID(layer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid layer_id format")

    deleted = await kl_crud.delete_layer(db, lid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Layer not found")

    await db.commit()
    return {"ok": True}


@router.post("/{layer_id}/assign-documents")
async def assign_documents(
    layer_id: str,
    request: AssignDocumentsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign documents to a knowledge layer."""
    try:
        lid = uuid.UUID(layer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid layer_id format")

    layer = await kl_crud.get_layer(db, lid)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    total_updated = 0
    for doc_id in request.document_ids:
        count = await dc_crud.assign_layer_to_document(
            db, layer.project_id, doc_id, lid
        )
        total_updated += count

    await db.commit()
    return {"ok": True, "updated_chunks": total_updated}
