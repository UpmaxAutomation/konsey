"""CRUD operations for folders."""

from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Folder


async def list_by_user(
    db: AsyncSession,
    user_id: str,
) -> List[Folder]:
    """List folders for a user."""
    result = await db.execute(
        select(Folder)
        .where(Folder.user_id == user_id)
        .order_by(Folder.created_at.desc())
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    folder_id: str,
    user_id: str,
    name: str,
    color: str,
    icon: str,
) -> Folder:
    """Create a folder for a user."""
    folder = Folder(
        id=folder_id,
        user_id=user_id,
        name=name,
        color=color,
        icon=icon,
    )
    db.add(folder)
    await db.flush()
    return folder


async def delete_by_id(
    db: AsyncSession,
    folder_id: str,
    user_id: str,
) -> bool:
    """Delete a folder by id for a user."""
    result = await db.execute(
        delete(Folder).where(
            Folder.id == folder_id,
            Folder.user_id == user_id,
        )
    )
    return result.rowcount > 0
