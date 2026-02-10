"""Asset library API routes."""

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db, USE_DATABASE, ANONYMOUS_USER_ID
from ..database.crud import generated_images as img_crud
from ..database.crud import assets as assets_crud

router = APIRouter(prefix="/api", tags=["assets"])


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None


class AssetResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    name: str
    asset_type: str
    source: str
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    tags: List[str] = []
    metadata: dict = {}
    created_at: str


def _asset_to_dict(asset) -> dict:
    return {
        "id": str(asset.id),
        "project_id": str(asset.project_id),
        "user_id": str(asset.user_id),
        "name": asset.name,
        "asset_type": asset.asset_type,
        "source": asset.source,
        "url": asset.url,
        "thumbnail_url": asset.thumbnail_url,
        "file_size": asset.file_size,
        "mime_type": asset.mime_type,
        "tags": asset.tags or [],
        "metadata": asset.metadata_json or {},
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }


@router.get("/projects/{project_id}/assets")
async def list_project_assets(
    project_id: uuid.UUID,
    asset_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List project assets with optional filtering."""
    if not USE_DATABASE:
        return []
    items = await assets_crud.list_assets(
        db, project_id, asset_type=asset_type, search=search, limit=limit, offset=offset
    )
    return [_asset_to_dict(a) for a in items]


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single asset."""
    if not USE_DATABASE:
        raise HTTPException(404, "Database not enabled")
    asset = await assets_crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return _asset_to_dict(asset)


@router.patch("/assets/{asset_id}")
async def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update asset metadata/tags."""
    if not USE_DATABASE:
        raise HTTPException(404, "Database not enabled")
    user_id = uuid.UUID(ANONYMOUS_USER_ID)
    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.tags is not None:
        updates["tags"] = body.tags
    if body.metadata is not None:
        updates["metadata_json"] = body.metadata
    asset = await assets_crud.update_asset(db, asset_id, user_id, **updates)
    if not asset:
        raise HTTPException(404, "Asset not found or not owned by user")
    return _asset_to_dict(asset)


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete an asset."""
    if not USE_DATABASE:
        raise HTTPException(404, "Database not enabled")
    user_id = uuid.UUID(ANONYMOUS_USER_ID)
    deleted = await assets_crud.delete_asset(db, asset_id, user_id)
    if not deleted:
        raise HTTPException(404, "Asset not found or not owned by user")
    return {"status": "deleted"}


@router.post("/projects/{project_id}/assets/from-image/{image_id}")
async def create_card_from_image(
    project_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Create an asset entry from a generated image (for placing on board as card)."""
    if not USE_DATABASE:
        raise HTTPException(404, "Database not enabled")
    user_id = uuid.UUID(ANONYMOUS_USER_ID)
    img = await img_crud.get_image(db, image_id)
    if not img:
        raise HTTPException(404, "Image not found")
    asset = await assets_crud.create_asset(
        db,
        project_id=project_id,
        user_id=user_id,
        name=img.prompt[:100],
        asset_type="image",
        source="generated",
        url=img.image_url,
        thumbnail_url=img.image_url,
        mime_type="image/png",
        metadata={"image_id": str(img.id), "provider": img.provider, "prompt": img.prompt},
    )
    return _asset_to_dict(asset)
