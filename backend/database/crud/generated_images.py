"""CRUD operations for generated images."""

import uuid
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import GeneratedImageDB


async def create_image(
    db: AsyncSession,
    user_id: uuid.UUID,
    prompt: str,
    provider: str,
    project_id: Optional[uuid.UUID] = None,
    revised_prompt: Optional[str] = None,
    model: Optional[str] = None,
    size: Optional[str] = None,
    quality: Optional[str] = None,
    style: Optional[str] = None,
    image_url: Optional[str] = None,
    image_data: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> GeneratedImageDB:
    """Persist a generated image to the database."""
    img = GeneratedImageDB(
        user_id=user_id,
        project_id=project_id,
        prompt=prompt,
        revised_prompt=revised_prompt,
        provider=provider,
        model=model,
        size=size,
        quality=quality,
        style=style,
        image_url=image_url,
        image_data=image_data,
        metadata_json=metadata or {},
    )
    db.add(img)
    await db.flush()
    await db.refresh(img)
    return img


async def list_images(
    db: AsyncSession,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[GeneratedImageDB]:
    """List generated images for a user, optionally filtered by project."""
    query = select(GeneratedImageDB).where(
        GeneratedImageDB.user_id == user_id
    ).order_by(desc(GeneratedImageDB.created_at)).limit(limit).offset(offset)
    if project_id:
        query = query.where(GeneratedImageDB.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_image(db: AsyncSession, image_id: uuid.UUID) -> Optional[GeneratedImageDB]:
    """Get a single generated image by ID."""
    result = await db.execute(
        select(GeneratedImageDB).where(GeneratedImageDB.id == image_id)
    )
    return result.scalar_one_or_none()


async def delete_image(db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete a generated image with ownership check."""
    img = await get_image(db, image_id)
    if not img or img.user_id != user_id:
        return False
    await db.delete(img)
    await db.flush()
    return True
