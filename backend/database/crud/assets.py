"""CRUD operations for asset library."""

import uuid
from typing import Optional, List
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AssetLibraryItem


async def create_asset(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    asset_type: str = "image",
    source: str = "generated",
    url: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    file_size: Optional[int] = None,
    mime_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[dict] = None,
) -> AssetLibraryItem:
    """Create an asset library entry."""
    asset = AssetLibraryItem(
        project_id=project_id,
        user_id=user_id,
        name=name,
        asset_type=asset_type,
        source=source,
        url=url,
        thumbnail_url=thumbnail_url,
        file_size=file_size,
        mime_type=mime_type,
        tags=tags or [],
        metadata_json=metadata or {},
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


async def list_assets(
    db: AsyncSession,
    project_id: uuid.UUID,
    asset_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[AssetLibraryItem]:
    """List project assets with optional filtering."""
    query = select(AssetLibraryItem).where(
        AssetLibraryItem.project_id == project_id
    ).order_by(desc(AssetLibraryItem.created_at)).limit(limit).offset(offset)
    if asset_type:
        query = query.where(AssetLibraryItem.asset_type == asset_type)
    if search:
        query = query.where(
            or_(
                AssetLibraryItem.name.ilike(f"%{search}%"),
                AssetLibraryItem.tags.any(search),
            )
        )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_asset(db: AsyncSession, asset_id: uuid.UUID) -> Optional[AssetLibraryItem]:
    """Get a single asset by ID."""
    result = await db.execute(
        select(AssetLibraryItem).where(AssetLibraryItem.id == asset_id)
    )
    return result.scalar_one_or_none()


async def update_asset(
    db: AsyncSession,
    asset_id: uuid.UUID,
    user_id: uuid.UUID,
    **updates,
) -> Optional[AssetLibraryItem]:
    """Update asset metadata/tags with ownership check."""
    asset = await get_asset(db, asset_id)
    if not asset or asset.user_id != user_id:
        return None
    allowed = {"name", "tags", "metadata_json"}
    for key, value in updates.items():
        if key in allowed and value is not None:
            setattr(asset, key, value)
    await db.flush()
    await db.refresh(asset)
    return asset


async def delete_asset(db: AsyncSession, asset_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete an asset with ownership check."""
    asset = await get_asset(db, asset_id)
    if not asset or asset.user_id != user_id:
        return False
    await db.delete(asset)
    await db.flush()
    return True
