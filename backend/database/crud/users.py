"""CRUD operations for users."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import User, UserSettings


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    return result.scalar_one_or_none()


async def get_by_google_id(db: AsyncSession, google_id: str) -> Optional[User]:
    """Get user by Google ID."""
    result = await db.execute(
        select(User).where(User.google_id == google_id)
    )
    return result.scalar_one_or_none()


async def get_with_settings(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Get user with settings loaded."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.settings))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    email: str,
    password_hash: Optional[str] = None,
    google_id: Optional[str] = None,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    is_verified: bool = False,
) -> User:
    """Create a new user with default settings."""
    user = User(
        email=email.lower(),
        password_hash=password_hash,
        google_id=google_id,
        name=name,
        avatar_url=avatar_url,
        is_verified=is_verified,
    )
    db.add(user)
    await db.flush()  # Get the user ID

    # Create default settings
    settings = UserSettings(
        user_id=user.id,
        council_models=[
            "openai/gpt-4o",
            "google/gemini-2.5-flash",
            "anthropic/claude-sonnet-4",
            "x-ai/grok-3",
        ],
        chairman_model="google/gemini-2.5-flash",
    )
    db.add(settings)
    await db.flush()

    return user


async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    **kwargs
) -> Optional[User]:
    """Update user fields."""
    kwargs["updated_at"] = datetime.utcnow()
    await db.execute(
        update(User).where(User.id == user_id).values(**kwargs)
    )
    return await get_by_id(db, user_id)


async def set_password(db: AsyncSession, user_id: uuid.UUID, password_hash: str) -> None:
    """Set user password hash."""
    await db.execute(
        update(User).where(User.id == user_id).values(
            password_hash=password_hash,
            updated_at=datetime.utcnow()
        )
    )


async def verify_email(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Mark user email as verified."""
    await db.execute(
        update(User).where(User.id == user_id).values(
            is_verified=True,
            updated_at=datetime.utcnow()
        )
    )


async def deactivate(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Deactivate user account."""
    await db.execute(
        update(User).where(User.id == user_id).values(
            is_active=False,
            updated_at=datetime.utcnow()
        )
    )


async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Delete user and all related data (cascade)."""
    await db.execute(
        delete(User).where(User.id == user_id)
    )


async def list_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True
) -> list[User]:
    """List users with pagination."""
    query = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    if active_only:
        query = query.where(User.is_active == True)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_users(db: AsyncSession, active_only: bool = True) -> int:
    """Count total users."""
    from sqlalchemy import func
    query = select(func.count(User.id))
    if active_only:
        query = query.where(User.is_active == True)
    result = await db.execute(query)
    return result.scalar() or 0
