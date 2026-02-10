"""CRUD operations for knowledge layers."""

import uuid
from typing import Optional, List

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KnowledgeLayer


# ──────────────────────────────────────────────
# Knowledge Layer operations
# ──────────────────────────────────────────────

async def create_layer(
    db: AsyncSession,
    project_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    persona_prompt: Optional[str] = None,
    methodology_prompt: Optional[str] = None,
    color: str = "blue",
    icon: str = "book",
) -> KnowledgeLayer:
    """Create a new knowledge layer for a project."""
    # Get max sort_order for this project
    result = await db.execute(
        select(KnowledgeLayer.sort_order)
        .where(KnowledgeLayer.project_id == project_id)
        .order_by(KnowledgeLayer.sort_order.desc())
        .limit(1)
    )
    max_order = result.scalar_one_or_none() or 0

    layer = KnowledgeLayer(
        id=uuid.uuid4(),
        project_id=project_id,
        name=name,
        description=description,
        persona_prompt=persona_prompt,
        methodology_prompt=methodology_prompt,
        color=color,
        icon=icon,
        sort_order=max_order + 1,
    )
    db.add(layer)
    await db.flush()
    return layer


async def get_layer(
    db: AsyncSession,
    layer_id: uuid.UUID,
) -> Optional[KnowledgeLayer]:
    """Get a single knowledge layer by ID."""
    result = await db.execute(
        select(KnowledgeLayer).where(KnowledgeLayer.id == layer_id)
    )
    return result.scalar_one_or_none()


async def list_layers(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> List[KnowledgeLayer]:
    """List all knowledge layers for a project, ordered by sort_order."""
    result = await db.execute(
        select(KnowledgeLayer)
        .where(KnowledgeLayer.project_id == project_id)
        .order_by(KnowledgeLayer.sort_order, KnowledgeLayer.created_at)
    )
    return list(result.scalars().all())


async def update_layer(
    db: AsyncSession,
    layer_id: uuid.UUID,
    **kwargs,
) -> Optional[KnowledgeLayer]:
    """Update knowledge layer fields."""
    allowed_fields = {
        "name", "description", "persona_prompt", "methodology_prompt",
        "color", "icon", "sort_order", "is_active",
    }
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        return await get_layer(db, layer_id)

    await db.execute(
        update(KnowledgeLayer)
        .where(KnowledgeLayer.id == layer_id)
        .values(**update_data)
    )
    return await get_layer(db, layer_id)


async def delete_layer(
    db: AsyncSession,
    layer_id: uuid.UUID,
) -> bool:
    """Delete a knowledge layer."""
    result = await db.execute(
        delete(KnowledgeLayer).where(KnowledgeLayer.id == layer_id)
    )
    return result.rowcount > 0


async def reorder_layers(
    db: AsyncSession,
    project_id: uuid.UUID,
    layer_ids: List[uuid.UUID],
) -> None:
    """Reorder layers based on the provided ID list."""
    for i, lid in enumerate(layer_ids):
        await db.execute(
            update(KnowledgeLayer)
            .where(
                KnowledgeLayer.id == lid,
                KnowledgeLayer.project_id == project_id,
            )
            .values(sort_order=i)
        )
