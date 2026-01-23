"""CRUD operations for user settings."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserSettings


async def get_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[UserSettings]:
    """Get settings for a user."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    user_id: uuid.UUID,
    council_models: Optional[list] = None,
    chairman_model: Optional[str] = None,
) -> UserSettings:
    """Create settings for a user."""
    settings = UserSettings(
        user_id=user_id,
        council_models=council_models or [
            "openai/gpt-4o",
            "google/gemini-2.5-flash",
            "anthropic/claude-sonnet-4",
            "x-ai/grok-3",
        ],
        chairman_model=chairman_model or "google/gemini-2.5-flash",
    )
    db.add(settings)
    await db.flush()
    return settings


async def update_settings(
    db: AsyncSession,
    user_id: uuid.UUID,
    **kwargs
) -> Optional[UserSettings]:
    """Update user settings."""
    kwargs["updated_at"] = datetime.utcnow()
    await db.execute(
        update(UserSettings)
        .where(UserSettings.user_id == user_id)
        .values(**kwargs)
    )
    return await get_by_user_id(db, user_id)


async def set_council_config(
    db: AsyncSession,
    user_id: uuid.UUID,
    council_models: list,
    chairman_model: str
) -> Optional[UserSettings]:
    """Set council configuration."""
    return await update_settings(
        db, user_id,
        council_models=council_models,
        chairman_model=chairman_model
    )


async def set_enhanced_features(
    db: AsyncSession,
    user_id: uuid.UUID,
    features: dict
) -> Optional[UserSettings]:
    """Set enhanced features configuration."""
    return await update_settings(db, user_id, enhanced_features=features)


async def set_personas(
    db: AsyncSession,
    user_id: uuid.UUID,
    personas: dict
) -> Optional[UserSettings]:
    """Set model personas."""
    return await update_settings(db, user_id, personas=personas)


async def add_custom_persona(
    db: AsyncSession,
    user_id: uuid.UUID,
    persona_id: str,
    persona_data: dict
) -> Optional[UserSettings]:
    """Add a custom persona."""
    settings = await get_by_user_id(db, user_id)
    if not settings:
        return None

    custom_personas = settings.custom_personas or {}
    custom_personas[persona_id] = persona_data

    return await update_settings(db, user_id, custom_personas=custom_personas)


async def remove_custom_persona(
    db: AsyncSession,
    user_id: uuid.UUID,
    persona_id: str
) -> Optional[UserSettings]:
    """Remove a custom persona."""
    settings = await get_by_user_id(db, user_id)
    if not settings:
        return None

    custom_personas = settings.custom_personas or {}
    custom_personas.pop(persona_id, None)

    return await update_settings(db, user_id, custom_personas=custom_personas)


async def set_budget_config(
    db: AsyncSession,
    user_id: uuid.UUID,
    budget_config: dict
) -> Optional[UserSettings]:
    """Set budget configuration."""
    return await update_settings(db, user_id, budget_config=budget_config)


async def set_theme(
    db: AsyncSession,
    user_id: uuid.UUID,
    theme: str
) -> Optional[UserSettings]:
    """Set UI theme."""
    return await update_settings(db, user_id, theme=theme)
