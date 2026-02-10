"""CRUD operations for property definitions and card property values."""

import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PropertyDefinition, CardPropertyValue


# ──────────────────────────────────────────────
# Property Definition operations
# ──────────────────────────────────────────────

async def list_property_definitions(
    db: AsyncSession,
    board_id: uuid.UUID
) -> List[PropertyDefinition]:
    """Get all property definitions for a board, ordered by sort_order."""
    result = await db.execute(
        select(PropertyDefinition)
        .where(PropertyDefinition.board_id == board_id)
        .order_by(PropertyDefinition.sort_order, PropertyDefinition.created_at)
    )
    return list(result.scalars().all())


async def create_property_definition(
    db: AsyncSession,
    board_id: uuid.UUID,
    name: str,
    property_type: str,
    options: Optional[dict] = None,
    sort_order: int = 0
) -> PropertyDefinition:
    """Create a new property definition on a board."""
    prop = PropertyDefinition(
        id=uuid.uuid4(),
        board_id=board_id,
        name=name,
        property_type=property_type,
        options=options,
        sort_order=sort_order,
    )
    db.add(prop)
    await db.flush()
    return prop


async def get_property_definition_by_id(
    db: AsyncSession,
    prop_id: uuid.UUID,
    board_id: uuid.UUID
) -> Optional[PropertyDefinition]:
    """Get a single property definition by ID within a board."""
    result = await db.execute(
        select(PropertyDefinition)
        .where(PropertyDefinition.id == prop_id, PropertyDefinition.board_id == board_id)
    )
    return result.scalar_one_or_none()


async def update_property_definition(
    db: AsyncSession,
    prop_id: uuid.UUID,
    board_id: uuid.UUID,
    **kwargs
) -> Optional[PropertyDefinition]:
    """Update property definition fields."""
    allowed_fields = {"name", "property_type", "options", "sort_order"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not update_data:
        return await get_property_definition_by_id(db, prop_id, board_id)

    await db.execute(
        update(PropertyDefinition)
        .where(PropertyDefinition.id == prop_id, PropertyDefinition.board_id == board_id)
        .values(**update_data)
    )
    return await get_property_definition_by_id(db, prop_id, board_id)


async def delete_property_definition(
    db: AsyncSession,
    prop_id: uuid.UUID,
    board_id: uuid.UUID
) -> bool:
    """Delete a property definition and all its values."""
    result = await db.execute(
        delete(PropertyDefinition)
        .where(PropertyDefinition.id == prop_id, PropertyDefinition.board_id == board_id)
    )
    return result.rowcount > 0


# ──────────────────────────────────────────────
# Card Property Value operations
# ──────────────────────────────────────────────

async def get_card_property_values(
    db: AsyncSession,
    card_id: uuid.UUID
) -> List[CardPropertyValue]:
    """Get all property values for a card."""
    result = await db.execute(
        select(CardPropertyValue)
        .where(CardPropertyValue.card_id == card_id)
    )
    return list(result.scalars().all())


async def bulk_set_card_properties(
    db: AsyncSession,
    card_id: uuid.UUID,
    values_dict: Dict[str, Any]
) -> List[CardPropertyValue]:
    """Set multiple property values on a card (upsert pattern).

    values_dict: { property_id_str: value }
    """
    for prop_id_str, value in values_dict.items():
        prop_id = uuid.UUID(prop_id_str)
        # Check if value already exists
        result = await db.execute(
            select(CardPropertyValue)
            .where(
                CardPropertyValue.card_id == card_id,
                CardPropertyValue.property_id == prop_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(CardPropertyValue(
                id=uuid.uuid4(),
                card_id=card_id,
                property_id=prop_id,
                value=value,
            ))
    await db.flush()
    return await get_card_property_values(db, card_id)


async def get_all_card_properties_for_board(
    db: AsyncSession,
    board_id: uuid.UUID
) -> List[CardPropertyValue]:
    """Get all property values for all cards on a board (for table/kanban views)."""
    from ..models import Card
    result = await db.execute(
        select(CardPropertyValue)
        .join(Card, CardPropertyValue.card_id == Card.id)
        .where(Card.board_id == board_id)
    )
    return list(result.scalars().all())
