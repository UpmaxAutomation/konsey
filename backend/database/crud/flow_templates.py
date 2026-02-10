"""CRUD operations for user-created flow templates."""

import uuid
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserFlowTemplate

logger = logging.getLogger(__name__)


async def create_template(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    steps: list,
    project_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None,
    icon: str = "zap",
    category: str = "custom",
    config: Optional[dict] = None,
) -> UserFlowTemplate:
    template = UserFlowTemplate(
        user_id=user_id,
        project_id=project_id,
        name=name,
        description=description,
        icon=icon,
        category=category,
        steps=steps,
        config=config or {},
    )
    db.add(template)
    await db.flush()
    return template


async def list_templates(
    db: AsyncSession,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
) -> list[UserFlowTemplate]:
    q = select(UserFlowTemplate).where(
        or_(
            UserFlowTemplate.user_id == user_id,
            UserFlowTemplate.is_public == True,
        )
    )
    if project_id:
        q = q.where(
            or_(
                UserFlowTemplate.project_id == project_id,
                UserFlowTemplate.project_id.is_(None),
            )
        )
    q = q.order_by(UserFlowTemplate.updated_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_template(
    db: AsyncSession,
    template_id: uuid.UUID,
) -> Optional[UserFlowTemplate]:
    result = await db.execute(
        select(UserFlowTemplate).where(UserFlowTemplate.id == template_id)
    )
    return result.scalar_one_or_none()


async def update_template(
    db: AsyncSession,
    template_id: uuid.UUID,
    user_id: uuid.UUID,
    **updates,
) -> Optional[UserFlowTemplate]:
    result = await db.execute(
        select(UserFlowTemplate).where(
            UserFlowTemplate.id == template_id,
            UserFlowTemplate.user_id == user_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        return None
    for key, value in updates.items():
        if hasattr(template, key) and value is not None:
            setattr(template, key, value)
    template.updated_at = datetime.utcnow()
    await db.flush()
    return template


async def delete_template(
    db: AsyncSession,
    template_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(UserFlowTemplate).where(
            UserFlowTemplate.id == template_id,
            UserFlowTemplate.user_id == user_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        return False
    await db.delete(template)
    await db.flush()
    return True
