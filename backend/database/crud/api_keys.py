"""CRUD operations for API keys.

Security Notes:
---------------
This module uses Fernet symmetric encryption (AES-128-CBC) to encrypt API keys at rest.
The encryption key is derived from the application's SECRET_KEY using PBKDF2-HMAC-SHA256.

Key Derivation:
- PBKDF2 with 100,000 iterations provides strong key derivation
- The salt is static but application-specific ("llm-council-api-keys-v1")
- A static salt is acceptable here because:
  1. This is key derivation, not password hashing
  2. Each SECRET_KEY produces a unique encryption key
  3. The derived key is never stored (only cached in memory)
  4. Rainbow table attacks are impractical against 32-byte keys

For password hashing (user passwords), use bcrypt/argon2 with random salts instead.
"""

import logging
import os
import uuid
import hashlib
from base64 import b64encode, b64decode
from datetime import datetime
from typing import Optional, List

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserAPIKey, SystemConfig

logger = logging.getLogger(__name__)


# Encryption key cache - avoids 100k PBKDF2 iterations on every call
_encryption_key_cache: Optional[bytes] = None
_encryption_secret_hash: Optional[str] = None

# Salt version allows rotating salts without breaking existing data
# Increment this and add migration logic if you need to re-encrypt all keys
SALT_VERSION = "v1"
SALT = f"llm-council-api-keys-{SALT_VERSION}".encode()

# PBKDF2 iterations - balance between security and performance
# 100k is OWASP recommended minimum for 2023+
PBKDF2_ITERATIONS = 100000


def _get_encryption_key() -> bytes:
    """
    Get or derive encryption key from SECRET_KEY (cached for performance).

    The key is derived using PBKDF2-HMAC-SHA256 with a static application salt.
    This is secure for key derivation (not password hashing) because:
    - The SECRET_KEY should already have sufficient entropy
    - The derived key is 256 bits (32 bytes)
    - 100k iterations provide computational resistance

    Returns:
        Base64-encoded 32-byte key suitable for Fernet
    """
    global _encryption_key_cache, _encryption_secret_hash

    secret_key = os.getenv("SECRET_KEY", "")

    # Validate SECRET_KEY exists
    if not secret_key:
        logger.warning(
            "SECRET_KEY not set - using fallback key. "
            "API key encryption will not persist across configuration changes."
        )
        secret_key = "insecure-development-key-do-not-use-in-production"

    # Create a hash of the secret for cache invalidation check
    secret_hash = hashlib.sha256(secret_key.encode()).hexdigest()

    # Check if we need to derive (first call or secret changed)
    if _encryption_key_cache is None or _encryption_secret_hash != secret_hash:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=SALT,
            iterations=PBKDF2_ITERATIONS,
        )
        _encryption_key_cache = b64encode(kdf.derive(secret_key.encode()))
        _encryption_secret_hash = secret_hash
        logger.debug("Derived new encryption key from SECRET_KEY")

    return _encryption_key_cache


def _encrypt(plaintext: str) -> str:
    """
    Encrypt a string using Fernet (AES-128-CBC with HMAC).

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded ciphertext
    """
    if not plaintext:
        raise ValueError("Cannot encrypt empty string")

    f = Fernet(_get_encryption_key())
    return f.encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    """
    Decrypt a Fernet-encrypted string.

    Args:
        ciphertext: Base64-encoded ciphertext from _encrypt()

    Returns:
        Decrypted plaintext string

    Raises:
        InvalidToken: If decryption fails (wrong key, corrupted data, or tampered)
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt empty string")

    f = Fernet(_get_encryption_key())
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error(
            "Failed to decrypt data - possible SECRET_KEY mismatch or data corruption. "
            "If SECRET_KEY was changed, encrypted data will need to be re-encrypted."
        )
        raise


# User API Key operations

async def get_user_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str
) -> Optional[str]:
    """Get decrypted API key for a user and provider."""
    # First, check if any key exists (active or not) for debugging
    all_keys_result = await db.execute(
        select(UserAPIKey).where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider
        )
    )
    all_key_record = all_keys_result.scalar_one_or_none()
    if all_key_record:
        logger.debug(f"get_user_key: found key record for {provider}, is_active={all_key_record.is_active}")
    else:
        logger.debug(f"get_user_key: no key record found for user {user_id}, provider {provider}")

    # Now get only active keys (also accept NULL as active for backward compatibility)
    result = await db.execute(
        select(UserAPIKey).where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider,
            UserAPIKey.is_active != False  # Treat NULL as active
        )
    )
    key_record = result.scalar_one_or_none()
    if key_record:
        try:
            decrypted = _decrypt(key_record.encrypted_key)
            logger.debug(f"get_user_key: successfully decrypted key for {provider}")
            return decrypted
        except Exception as e:
            # Log decryption failure without exposing key data
            logger.warning(f"Failed to decrypt API key for user {user_id}, provider {provider}: {type(e).__name__}")
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
            UserAPIKey.is_active != False  # Treat NULL as active
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

    # Check if exists (including inactive ones - we'll reactivate them)
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
        await db.flush()  # Ensure update is flushed before commit
        return existing
    else:
        new_key = UserAPIKey(
            user_id=user_id,
            provider=provider,
            encrypted_key=encrypted,
            is_active=True,  # Explicitly set to avoid NULL values
        )
        db.add(new_key)
        await db.flush()  # Ensure new key is flushed before commit
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
                decrypted = _decrypt(config.value)
                return decrypted
            except Exception as e:
                # Log decryption failure without exposing key data
                logger.warning(f"Failed to decrypt system key for provider {provider}: {type(e).__name__}")
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


async def clear_all_user_keys(db: AsyncSession) -> int:
    """Clear all user API keys (use when SECRET_KEY changes)."""
    result = await db.execute(delete(UserAPIKey))
    await db.flush()
    return result.rowcount


async def clear_all_system_keys(db: AsyncSession) -> int:
    """Clear all encrypted system API keys (use when SECRET_KEY changes)."""
    # Only delete encrypted keys (api_key entries)
    result = await db.execute(
        delete(SystemConfig).where(SystemConfig.key.like("%_api_key"))
    )
    await db.flush()
    return result.rowcount


async def clear_all_encrypted_keys(db: AsyncSession) -> dict:
    """
    Clear ALL encrypted API keys from the database.
    Use this when SECRET_KEY has changed and keys can't be decrypted.
    Returns count of deleted keys.
    """
    user_count = await clear_all_user_keys(db)
    system_count = await clear_all_system_keys(db)
    return {
        "user_keys_deleted": user_count,
        "system_keys_deleted": system_count,
        "total_deleted": user_count + system_count
    }


# Resolution function: user key -> system key -> env var

async def resolve_api_key(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    provider: str,
    allow_system_fallback: bool = False
) -> Optional[str]:
    """
    Resolve API key with priority:
    1. User's own key (if user_id provided)
    2. System-wide shared key (only if allow_system_fallback=True)

    Note: Environment variable fallback removed - users must set their own keys
    or admin must set system key explicitly.
    """
    logger.debug(f"resolve_api_key: user_id={user_id}, provider={provider}, allow_system_fallback={allow_system_fallback}")

    # Try user's key first
    if user_id:
        user_key = await get_user_key(db, user_id, provider)
        if user_key:
            logger.debug(f"resolve_api_key: found user key for {provider}")
            return user_key
        logger.debug(f"resolve_api_key: no user key found for {provider}")

    # Only try system key if explicitly allowed (for admin-set system keys)
    if allow_system_fallback:
        system_key = await get_system_key(db, provider)
        if system_key:
            logger.debug(f"resolve_api_key: found system key for {provider}")
            return system_key

        # Fallback to environment variable for OpenRouter (only if system fallback allowed)
        if provider == "openrouter":
            env_key = os.getenv("OPENROUTER_API_KEY")
            if env_key:
                logger.debug(f"resolve_api_key: found env var OPENROUTER_API_KEY")
                return env_key

    logger.debug(f"resolve_api_key: no key found for {provider}")
    return None
