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
    # #region agent log
    import os
    import json
    from datetime import datetime
    debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-get","hypothesisId":"H62","location":"api_keys.py:48","message":"get_user_key:entry","data":{"user_id":str(user_id),"provider":provider},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion
    result = await db.execute(
        select(UserAPIKey).where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider,
            UserAPIKey.is_active == True
        )
    )
    key_record = result.scalar_one_or_none()
    # #region agent log
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-get","hypothesisId":"H63","location":"api_keys.py:61","message":"get_user_key:query_result","data":{"user_id":str(user_id),"provider":provider,"found_record":bool(key_record),"key_id":str(key_record.id) if key_record else None,"is_active":key_record.is_active if key_record else None},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion
    if key_record:
        try:
            decrypted = _decrypt(key_record.encrypted_key)
            # #region agent log
            if os.path.exists(os.path.dirname(debug_log_path)):
                try:
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-get","hypothesisId":"H64","location":"api_keys.py:64","message":"get_user_key:decrypted","data":{"user_id":str(user_id),"provider":provider,"key_length":len(decrypted) if decrypted else 0},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                except Exception:
                    pass
            # #endregion
            return decrypted
        except Exception as e:
            # #region agent log
            if os.path.exists(os.path.dirname(debug_log_path)):
                try:
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-get","hypothesisId":"H65","location":"api_keys.py:66","message":"get_user_key:decrypt_failed","data":{"user_id":str(user_id),"provider":provider,"error":str(e)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                except Exception:
                    pass
            # #endregion
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
    # #region agent log
    import os
    import json
    from datetime import datetime
    debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-set","hypothesisId":"H66","location":"api_keys.py:121","message":"set_user_key:entry","data":{"user_id":str(user_id),"provider":provider,"has_api_key":bool(api_key),"key_length":len(api_key) if api_key else 0},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion
    encrypted = _encrypt(api_key)

    # Check if exists
    result = await db.execute(
        select(UserAPIKey).where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.provider == provider
        )
    )
    existing = result.scalar_one_or_none()
    # #region agent log
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-set","hypothesisId":"H67","location":"api_keys.py:137","message":"set_user_key:existing_check","data":{"user_id":str(user_id),"provider":provider,"has_existing":bool(existing),"existing_id":str(existing.id) if existing else None,"existing_is_active":existing.is_active if existing else None},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion

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
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-set","hypothesisId":"H68","location":"api_keys.py:149","message":"set_user_key:updated","data":{"user_id":str(user_id),"provider":provider,"key_id":str(existing.id)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        return existing
    else:
        new_key = UserAPIKey(
            user_id=user_id,
            provider=provider,
            encrypted_key=encrypted,
        )
        db.add(new_key)
        await db.flush()  # Ensure new key is flushed before commit
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-set","hypothesisId":"H69","location":"api_keys.py:159","message":"set_user_key:created","data":{"user_id":str(user_id),"provider":provider,"key_id":str(new_key.id)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
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
    # #region agent log
    import os
    import json
    from datetime import datetime
    debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-system","hypothesisId":"H25","location":"api_keys.py:159","message":"get_system_key:entry","data":{"provider":provider},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion
    key_name = f"{provider}_api_key"
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == key_name)
    )
    config = result.scalar_one_or_none()
    # #region agent log
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-system","hypothesisId":"H26","location":"api_keys.py:165","message":"get_system_key:query_result","data":{"provider":provider,"key_name":key_name,"found_config":bool(config)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion
    if config:
        if config.encrypted:
            try:
                decrypted = _decrypt(config.value)
                # #region agent log
                if os.path.exists(os.path.dirname(debug_log_path)):
                    try:
                        with open(debug_log_path, 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-system","hypothesisId":"H27","location":"api_keys.py:169","message":"get_system_key:decrypted","data":{"provider":provider,"key_length":len(decrypted) if decrypted else 0},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                    except Exception:
                        pass
                # #endregion
                return decrypted
            except Exception as e:
                # #region agent log
                if os.path.exists(os.path.dirname(debug_log_path)):
                    try:
                        with open(debug_log_path, 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-system","hypothesisId":"H28","location":"api_keys.py:171","message":"get_system_key:decrypt_failed","data":{"provider":provider,"error":str(e)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                    except Exception:
                        pass
                # #endregion
                return None
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-system","hypothesisId":"H29","location":"api_keys.py:177","message":"get_system_key:not_encrypted","data":{"provider":provider,"key_length":len(config.value) if config.value else 0},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
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
    # #region agent log
    import os
    import json
    from datetime import datetime
    debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-resolve","hypothesisId":"H21","location":"api_keys.py:220","message":"resolve_api_key:entry","data":{"user_id":str(user_id) if user_id else None,"provider":provider,"allow_system_fallback":allow_system_fallback},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion
    # Try user's key first
    if user_id:
        user_key = await get_user_key(db, user_id, provider)
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-resolve","hypothesisId":"H22","location":"api_keys.py:236","message":"resolve_api_key:user_key_result","data":{"user_id":str(user_id),"provider":provider,"has_user_key":bool(user_key)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        if user_key:
            return user_key

    # Only try system key if explicitly allowed (for admin-set system keys)
    if allow_system_fallback:
        system_key = await get_system_key(db, provider)
        # #region agent log
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-resolve","hypothesisId":"H23","location":"api_keys.py:242","message":"resolve_api_key:system_key_result","data":{"provider":provider,"has_system_key":bool(system_key)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        if system_key:
            return system_key

    # No fallback to environment variables - users must set their own keys
    # #region agent log
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"api-key-resolve","hypothesisId":"H24","location":"api_keys.py:247","message":"resolve_api_key:no_key_found","data":{"provider":provider,"user_id":str(user_id) if user_id else None},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion
    return None
