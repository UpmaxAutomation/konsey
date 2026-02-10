"""CRUD operations for board templates."""

import uuid
from typing import Optional, List
from sqlalchemy import select, desc, or_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BoardTemplate, Card, Section, Edge


async def create_template(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    category: str = "general",
    icon: str = "layout",
    template_data: dict = None,
    preview_data: dict = None,
    is_public: bool = False,
    project_id: Optional[uuid.UUID] = None,
) -> BoardTemplate:
    """Create a board template from serialized board state."""
    tmpl = BoardTemplate(
        user_id=user_id,
        project_id=project_id,
        name=name,
        description=description,
        category=category,
        icon=icon,
        template_data=template_data or {},
        preview_data=preview_data or {},
        is_public=is_public,
    )
    db.add(tmpl)
    await db.flush()
    await db.refresh(tmpl)
    return tmpl


async def list_templates(
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    public_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> List[BoardTemplate]:
    """List board templates with filters."""
    query = select(BoardTemplate).order_by(desc(BoardTemplate.created_at)).limit(limit).offset(offset)
    if public_only:
        query = query.where(BoardTemplate.is_public == True)
    elif user_id:
        query = query.where(
            or_(BoardTemplate.user_id == user_id, BoardTemplate.is_public == True)
        )
    if category:
        query = query.where(BoardTemplate.category == category)
    if search:
        query = query.where(
            or_(
                BoardTemplate.name.ilike(f"%{search}%"),
                BoardTemplate.description.ilike(f"%{search}%"),
            )
        )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_template(db: AsyncSession, template_id: uuid.UUID) -> Optional[BoardTemplate]:
    """Get a single board template."""
    result = await db.execute(
        select(BoardTemplate).where(BoardTemplate.id == template_id)
    )
    return result.scalar_one_or_none()


async def apply_template(
    db: AsyncSession,
    board_id: uuid.UUID,
    template_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    """Apply a board template — create cards, sections, edges from template_data."""
    tmpl = await get_template(db, template_id)
    if not tmpl:
        return {"error": "Template not found"}

    data = tmpl.template_data
    id_map = {}
    created_cards = []
    created_sections = []

    # Create sections
    for section_data in data.get("sections", []):
        old_id = section_data.get("id", str(uuid.uuid4()))
        new_section = Section(
            board_id=board_id,
            title=section_data.get("title", "Section"),
            color=section_data.get("color", "gray"),
            position_x=section_data.get("position_x", 0),
            position_y=section_data.get("position_y", 0),
            width=section_data.get("width", 400),
            height=section_data.get("height", 300),
        )
        db.add(new_section)
        await db.flush()
        await db.refresh(new_section)
        id_map[old_id] = str(new_section.id)
        created_sections.append(str(new_section.id))

    # Create cards
    for card_data in data.get("cards", []):
        old_id = card_data.get("id", str(uuid.uuid4()))
        section_id = None
        if card_data.get("section_id") and card_data["section_id"] in id_map:
            section_id = uuid.UUID(id_map[card_data["section_id"]])
        new_card = Card(
            board_id=board_id,
            title=card_data.get("title", "Card"),
            content=card_data.get("content", ""),
            card_type=card_data.get("card_type", "note"),
            position_x=card_data.get("position_x", 0),
            position_y=card_data.get("position_y", 0),
            width=card_data.get("width", 280),
            height=card_data.get("height", 200),
            section_id=section_id,
        )
        db.add(new_card)
        await db.flush()
        await db.refresh(new_card)
        id_map[old_id] = str(new_card.id)
        created_cards.append(str(new_card.id))

    # Create edges
    for edge_data in data.get("edges", []):
        source = id_map.get(edge_data.get("source"))
        target = id_map.get(edge_data.get("target"))
        if source and target:
            new_edge = Edge(
                board_id=board_id,
                source_card_id=uuid.UUID(source),
                target_card_id=uuid.UUID(target),
                edge_type=edge_data.get("edge_type", "related"),
                label=edge_data.get("label"),
            )
            db.add(new_edge)

    await db.flush()

    # Increment use count
    await increment_use_count(db, template_id)

    return {"cards": created_cards, "sections": created_sections}


async def delete_template(db: AsyncSession, template_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete a board template with ownership check."""
    tmpl = await get_template(db, template_id)
    if not tmpl or tmpl.user_id != user_id:
        return False
    await db.delete(tmpl)
    await db.flush()
    return True


async def increment_use_count(db: AsyncSession, template_id: uuid.UUID) -> None:
    """Increment the use count of a template."""
    await db.execute(
        update(BoardTemplate)
        .where(BoardTemplate.id == template_id)
        .values(use_count=BoardTemplate.use_count + 1)
    )
    await db.flush()
