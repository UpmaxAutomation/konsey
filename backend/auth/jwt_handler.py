"""JWT token handling for authentication."""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import jwt, JWTError

# Configuration from environment
_secret_key_env = os.getenv("SECRET_KEY", "")
_environment = os.getenv("ENVIRONMENT", "development").lower()

# Fail-fast security: Require SECRET_KEY in production
if _environment == "production" and not _secret_key_env:
    print("FATAL: SECRET_KEY environment variable is required in production.", file=sys.stderr)
    print("Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(64))\"", file=sys.stderr)
    sys.exit(1)

# Use provided key or development default (only safe in dev)
SECRET_KEY = _secret_key_env or "development-secret-key-DO-NOT-USE-IN-PRODUCTION"

# Log warning in development if using default key
if not _secret_key_env and _environment != "production":
    import logging
    logging.getLogger(__name__).warning(
        "Using default SECRET_KEY. Set SECRET_KEY env var for security."
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
