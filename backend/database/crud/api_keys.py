"""CRUD operations for API keys."""

import os
import uuid
from base64 import b64encode, b64decode
from datetime import datetime
from typing import Optional, List

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserAPIKey, SystemConfig


# Encryption key derivation
def _get_encryption_key() -> bytes:
    """Get or derive encryption key from SECRET_KEY."""
    secret_key = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")
    salt = b"llm-council-api-keys"  # Static salt for deterministic key derivation

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(secret_key.encode())
    return b64encode(key)


def _encrypt(plaintext: str) -> str:
    """Encrypt a string."""
    f = Fernet(_get_encryption_key())
    return f.encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    """Decrypt a string."""
    f = Fernet(_get_encryption_key())
    return f.decrypt(ciphertext.encode()).decode()


# User API Key operations

async def get_user_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str
) -> Optional[str]:
    """Get decrypted API key for a user and provider."""
    result = await db.execute(
        select(UserAPIKey).where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider,
            UserAPIKey.is_active == True
        )
    )
    key_record = result.scalar_one_or_none()
    if key_record:
        try:
            return _decrypt(key_record.encrypted_key)
        except Exception:
            return None
    return None


async def list_user_providers(
    db: AsyncSession,
    user_id: uuid.UUID
) -> List[str]:
    """List providers for which user has API keys configured."""
    result = await db.execute(
        select(UserAPIKey.provider).where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.is_active == True
        )
    )
    return [row[0] for row in result.fetchall()]


async def set_user_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    api_key: str
) -> UserAPIKey:
    """Set or update API key for a user and provider."""
    encrypted = _encrypt(api_key)

    # Check if exists
    result = await db.execute(
        select(UserAPIKey).where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.execute(
            update(UserAPIKey)
            .where(UserAPIKey.id == existing.id)
            .values(
                encrypted_key=encrypted,
                is_active=True,
                updated_at=datetime.utcnow()
            )
        )
        return existing
    else:
        new_key = UserAPIKey(
            user_id=user_id,
            provider=provider,
            encrypted_key=encrypted,
        )
        db.add(new_key)
        await db.flush()
        return new_key


async def delete_user_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str
) -> bool:
    """Delete API key for a user and provider."""
    result = await db.execute(
        delete(UserAPIKey).where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider
        )
    )
    return result.rowcount > 0


async def deactivate_user_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str
) -> bool:
    """Deactivate (soft delete) API key."""
    result = await db.execute(
        update(UserAPIKey)
        .where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider
        )
        .values(is_active=False, updated_at=datetime.utcnow())
    )
    return result.rowcount > 0


# System Config operations (for shared/default keys)

async def get_system_key(db: AsyncSession, provider: str) -> Optional[str]:
    """Get system-wide API key for a provider."""
    key_name = f"{provider}_api_key"
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == key_name)
    )
    config = result.scalar_one_or_none()
    if config:
        if config.encrypted:
            try:
                return _decrypt(config.value)
            except Exception:
                return None
        return config.value
    return None


async def set_system_key(
    db: AsyncSession,
    provider: str,
    api_key: str,
    encrypt: bool = True
) -> SystemConfig:
    """Set system-wide API key for a provider."""
    key_name = f"{provider}_api_key"
    value = _encrypt(api_key) if encrypt else api_key

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == key_name)
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.execute(
            update(SystemConfig)
            .where(SystemConfig.key == key_name)
            .values(value=value, encrypted=encrypt, updated_at=datetime.utcnow())
        )
        return existing
    else:
        config = SystemConfig(
            key=key_name,
            value=value,
            encrypted=encrypt,
        )
        db.add(config)
        await db.flush()
        return config


async def delete_system_key(db: AsyncSession, provider: str) -> bool:
    """Delete system-wide API key."""
    key_name = f"{provider}_api_key"
    result = await db.execute(
        delete(SystemConfig).where(SystemConfig.key == key_name)
    )
    return result.rowcount > 0


# Resolution function: user key -> system key -> env var

async def resolve_api_key(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    provider: str
) -> Optional[str]:
    """
    Resolve API key with priority:
    1. User's own key (if user_id provided)
    2. System-wide shared key
    3. Environment variable
    """
    # Try user's key first
    if user_id:
        user_key = await get_user_key(db, user_id, provider)
        if user_key:
            return user_key

    # Try system key
    system_key = await get_system_key(db, provider)
    if system_key:
        return system_key

    # Fall back to environment
    env_key = os.getenv(f"{provider.upper()}_API_KEY")
    if env_key:
        return env_key

    # Special case for OpenRouter
    if provider != "openrouter":
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            return openrouter_key

    return None
