"""CRUD operations for board sections."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Section


# ──────────────────────────────────────────────
# Section operations
# ──────────────────────────────────────────────

async def list_sections(
    db: AsyncSession,
    board_id: uuid.UUID
) -> List[Section]:
    """Get all sections for a board, ordered by created_at."""
    result = await db.execute(
        select(Section)
        .where(Section.board_id == board_id)
        .order_by(Section.created_at)
    )
    return list(result.scalars().all())


async def create_section(
    db: AsyncSession,
    board_id: uuid.UUID,
    title: str = "",
    color: str = "gray",
    x: float = 0.0,
    y: float = 0.0,
    width: float = 400.0,
    height: float = 300.0
) -> Section:
    """Create a new section on a board."""
    section = Section(
        id=uuid.uuid4(),
        board_id=board_id,
        title=title,
        color=color,
        x=x,
        y=y,
        width=width,
        height=height,
    )
    db.add(section)
    await db.flush()
    return section


async def update_section(
    db: AsyncSession,
    section_id: uuid.UUID,
    board_id: uuid.UUID,
    **kwargs
) -> Optional[Section]:
    """Update section fields.

    Allowed fields: title, color, x, y, width, height.
    Returns the updated section or None if not found.
    """
    allowed_fields = {"title", "color", "x", "y", "width", "height"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        return await get_section_by_id(db, section_id, board_id)

    await db.execute(
        update(Section)
        .where(Section.id == section_id, Section.board_id == board_id)
        .values(**update_data)
    )
    return await get_section_by_id(db, section_id, board_id)


async def delete_section(
    db: AsyncSession,
    section_id: uuid.UUID,
    board_id: uuid.UUID
) -> bool:
    """Delete a section from a board."""
    result = await db.execute(
        delete(Section)
        .where(Section.id == section_id, Section.board_id == board_id)
    )
    return result.rowcount > 0


async def get_section_by_id(
    db: AsyncSession,
    section_id: uuid.UUID,
    board_id: uuid.UUID
) -> Optional[Section]:
    """Get a single section by ID within a board."""
    result = await db.execute(
        select(Section)
        .where(Section.id == section_id, Section.board_id == board_id)
    )
    return result.scalar_one_or_none()
