"""CRUD operations for email verification tokens."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EmailVerificationToken, User


# Token expiration time (24 hours)
TOKEN_EXPIRY_HOURS = 24


def generate_verification_token() -> str:
    """Generate a secure random verification token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a verification token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_verification_token(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> str:
    """
    Create a new email verification token for a user.
    Returns the raw token (to be sent to user).
    Only the hashed version is stored in the database.
    """
    # Invalidate any existing unused tokens for this user
    await db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.is_used == False
        )
        .values(is_used=True)  # Mark old tokens as used
    )

    # Generate new token
    raw_token = generate_verification_token()
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)

    verification_token = EmailVerificationToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(verification_token)
    await db.flush()

    return raw_token


async def get_token_by_hash(
    db: AsyncSession,
    token_hash: str,
) -> Optional[EmailVerificationToken]:
    """Get a verification token by its hash."""
    result = await db.execute(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def verify_token(
    db: AsyncSession,
    raw_token: str,
) -> Optional[uuid.UUID]:
    """
    Verify a token and return the associated user_id if valid.
    Returns None if token is invalid, expired, or already used.
    """
    token_hash = hash_token(raw_token)
    token = await get_token_by_hash(db, token_hash)

    if not token:
        return None

    if token.is_used:
        return None

    if token.expires_at < datetime.now(timezone.utc):
        return None

    # Mark token as used
    await db.execute(
        update(EmailVerificationToken)
        .where(EmailVerificationToken.id == token.id)
        .values(is_used=True)
    )

    return token.user_id


async def get_user_pending_token(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[EmailVerificationToken]:
    """Get the most recent unused, non-expired token for a user."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.is_used == False,
            EmailVerificationToken.expires_at > now
        )
        .order_by(EmailVerificationToken.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """
    Mark expired tokens as used (cleanup).
    Returns the number of tokens cleaned up.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.is_used == False,
            EmailVerificationToken.expires_at < now
        )
        .values(is_used=True)
    )
    return result.rowcount
