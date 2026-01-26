"""JWT token handling for authentication."""

import os
import sys
import uuid
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import jwt, JWTError

logger = logging.getLogger(__name__)

# Configuration from environment
_secret_key_env = os.getenv("SECRET_KEY", "")
_environment = os.getenv("ENVIRONMENT", "development").lower()

# Minimum recommended secret key length (32 bytes = 256 bits for HS256)
MIN_SECRET_KEY_LENGTH = 32


def _validate_secret_key(key: str, environment: str) -> tuple[bool, str]:
    """Validate the secret key meets security requirements."""
    if not key:
        return False, "SECRET_KEY is empty"

    if len(key) < MIN_SECRET_KEY_LENGTH:
        return False, f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters (got {len(key)})"

    # Check for common weak patterns
    weak_patterns = [
        "secret", "password", "changeme", "default", "example",
        "12345", "abcde", "qwerty", "admin", "test"
    ]
    key_lower = key.lower()
    for pattern in weak_patterns:
        if pattern in key_lower:
            if environment == "production":
                return False, f"SECRET_KEY contains weak pattern: '{pattern}'"
            else:
                logger.warning(f"SECRET_KEY contains weak pattern: '{pattern}' - acceptable in development only")

    return True, "OK"


# Fail-fast security: Require strong SECRET_KEY in production
if _environment == "production":
    if not _secret_key_env:
        logger.critical("FATAL: SECRET_KEY environment variable is required in production.")
        logger.critical("Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(64))\"")
        sys.exit(1)

    is_valid, error_msg = _validate_secret_key(_secret_key_env, _environment)
    if not is_valid:
        logger.critical(f"FATAL: {error_msg}")
        logger.critical("Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(64))\"")
        sys.exit(1)

# Development default - generates a random key per process (safe for dev, not for sessions across restarts)
_dev_default_key = f"dev-{secrets.token_hex(32)}"

# Use provided key or development default (only safe in dev)
if _secret_key_env:
    SECRET_KEY = _secret_key_env
    is_valid, error_msg = _validate_secret_key(_secret_key_env, _environment)
    if not is_valid and _environment != "production":
        logger.warning(f"SECRET_KEY validation: {error_msg} - proceeding in development mode")
else:
    SECRET_KEY = _dev_default_key
    if _environment != "production":
        logger.warning(
            "Using auto-generated development SECRET_KEY. "
            "Sessions will not persist across server restarts. "
            "Set SECRET_KEY env var for persistent sessions."
        )

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    is_admin: bool = False,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: uuid.UUID,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, datetime]:
    """Create a JWT refresh token. Returns (token, expires_at)."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),  # Unique token ID for revocation
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate an access token."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify it's an access token
        if payload.get("type") != "access":
            logger.warning(f"Token type mismatch: got '{payload.get('type')}', expected 'access'")
            return None

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            logger.warning(f"Token expired for user {payload.get('sub')}")
            return None

        return payload

    except JWTError as e:
        # Log the specific error - this is critical for debugging SECRET_KEY mismatches
        logger.warning(f"JWT decode failed: {type(e).__name__}: {str(e)}")
        # Common causes: Signature verification failed (SECRET_KEY mismatch), malformed token
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a refresh token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            return None

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            return None

        return payload

    except JWTError:
        return None


def get_token_hash(token: str) -> str:
    """Create a hash of a token for storage (for refresh token revocation)."""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()
