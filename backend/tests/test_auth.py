"""Tests for authentication module."""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from backend.auth.password import hash_password, verify_password, needs_rehash
from backend.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    get_token_hash,
    _validate_secret_key,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        hashed = hash_password("mysecretpassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_different_for_same_input(self):
        """Test that hashing same password twice gives different hashes (salting)."""
        hash1 = hash_password("samepassword")
        hash2 = hash_password("samepassword")
        # Argon2 uses random salt, so hashes should be different
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "correctpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty(self):
        """Test verifying empty password."""
        hashed = hash_password("realpassword")
        assert verify_password("", hashed) is False

    def test_verify_password_invalid_hash(self):
        """Test verifying against invalid hash returns False (not exception)."""
        assert verify_password("password", "invalidhash") is False

    def test_verify_password_unicode(self):
        """Test hashing and verifying unicode passwords."""
        password = "contraseña_日本語_пароль"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_needs_rehash_new_hash(self):
        """Test that freshly hashed passwords don't need rehash."""
        hashed = hash_password("mypassword")
        # With current settings, a new hash shouldn't need update
        assert needs_rehash(hashed) is False


class TestJWTAccessToken:
    """Tests for JWT access token creation and decoding."""

    @pytest.fixture
    def user_id(self):
        return uuid.uuid4()

    def test_create_access_token_returns_string(self, user_id):
        """Test that create_access_token returns a string."""
        token = create_access_token(user_id, "test@example.com")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_decodes_correctly(self, user_id):
        """Test that created token can be decoded."""
        token = create_access_token(user_id, "test@example.com", is_admin=True)
        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["email"] == "test@example.com"
        assert payload["is_admin"] is True
        assert payload["type"] == "access"

    def test_create_access_token_custom_expiry(self, user_id):
        """Test token with custom expiry."""
        token = create_access_token(
            user_id,
            "test@example.com",
            expires_delta=timedelta(hours=1)
        )
        payload = decode_access_token(token)
        assert payload is not None

    def test_decode_expired_token_returns_none(self, user_id):
        """Test that expired tokens return None."""
        # Create token that expires immediately
        token = create_access_token(
            user_id,
            "test@example.com",
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        payload = decode_access_token(token)
        assert payload is None

    def test_decode_invalid_token_returns_none(self):
        """Test that invalid tokens return None."""
        payload = decode_access_token("invalid.token.here")
        assert payload is None

    def test_decode_tampered_token_returns_none(self, user_id):
        """Test that tampered tokens fail verification."""
        token = create_access_token(user_id, "test@example.com")
        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "XXXXX"  # Modify payload
        tampered = ".".join(parts)

        payload = decode_access_token(tampered)
        assert payload is None

    def test_decode_refresh_token_as_access_fails(self, user_id):
        """Test that refresh tokens can't be used as access tokens."""
        refresh_token, _ = create_refresh_token(user_id)
        payload = decode_access_token(refresh_token)
        assert payload is None  # Type mismatch should fail


class TestJWTRefreshToken:
    """Tests for JWT refresh token creation and decoding."""

    @pytest.fixture
    def user_id(self):
        return uuid.uuid4()

    def test_create_refresh_token_returns_tuple(self, user_id):
        """Test that create_refresh_token returns token and expiry."""
        token, expires_at = create_refresh_token(user_id)
        assert isinstance(token, str)
        assert isinstance(expires_at, datetime)

    def test_create_refresh_token_decodes_correctly(self, user_id):
        """Test that created refresh token can be decoded."""
        token, _ = create_refresh_token(user_id)
        payload = decode_refresh_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
        assert "jti" in payload  # Unique token ID

    def test_create_refresh_token_custom_expiry(self, user_id):
        """Test refresh token with custom expiry."""
        token, expires_at = create_refresh_token(
            user_id,
            expires_delta=timedelta(days=7)
        )
        payload = decode_refresh_token(token)
        assert payload is not None

    def test_decode_expired_refresh_token_returns_none(self, user_id):
        """Test that expired refresh tokens return None."""
        token, _ = create_refresh_token(
            user_id,
            expires_delta=timedelta(seconds=-1)
        )
        payload = decode_refresh_token(token)
        assert payload is None

    def test_refresh_tokens_have_unique_jti(self, user_id):
        """Test that each refresh token has unique JTI."""
        token1, _ = create_refresh_token(user_id)
        token2, _ = create_refresh_token(user_id)

        payload1 = decode_refresh_token(token1)
        payload2 = decode_refresh_token(token2)

        assert payload1["jti"] != payload2["jti"]

    def test_decode_access_token_as_refresh_fails(self, user_id):
        """Test that access tokens can't be used as refresh tokens."""
        access_token = create_access_token(user_id, "test@example.com")
        payload = decode_refresh_token(access_token)
        assert payload is None


class TestTokenHash:
    """Tests for token hashing for storage."""

    def test_get_token_hash_returns_string(self):
        """Test that token hash returns a string."""
        hash_val = get_token_hash("some-token-value")
        assert isinstance(hash_val, str)
        # SHA256 produces 64 hex characters
        assert len(hash_val) == 64

    def test_get_token_hash_deterministic(self):
        """Test that same token produces same hash."""
        token = "my-token"
        hash1 = get_token_hash(token)
        hash2 = get_token_hash(token)
        assert hash1 == hash2

    def test_get_token_hash_different_for_different_tokens(self):
        """Test that different tokens produce different hashes."""
        hash1 = get_token_hash("token-1")
        hash2 = get_token_hash("token-2")
        assert hash1 != hash2


class TestSecretKeyValidation:
    """Tests for secret key validation."""

    def test_empty_key_invalid(self):
        """Test that empty key is invalid."""
        is_valid, msg = _validate_secret_key("", "development")
        assert is_valid is False
        assert "empty" in msg.lower()

    def test_short_key_invalid(self):
        """Test that short key is invalid."""
        is_valid, msg = _validate_secret_key("short", "development")
        assert is_valid is False
        assert "32" in msg  # Should mention minimum length

    def test_weak_pattern_production_invalid(self):
        """Test that weak patterns are invalid in production."""
        is_valid, msg = _validate_secret_key(
            "x" * 32 + "password" + "x" * 32,
            "production"
        )
        assert is_valid is False
        assert "weak" in msg.lower()

    def test_weak_pattern_development_warning(self):
        """Test that weak patterns are allowed with warning in development."""
        is_valid, msg = _validate_secret_key(
            "x" * 32 + "secret" + "x" * 32,
            "development"
        )
        # In development, weak patterns should pass (with warning logged)
        assert is_valid is True

    def test_strong_key_valid(self):
        """Test that strong key passes validation."""
        import secrets
        strong_key = secrets.token_urlsafe(64)
        is_valid, msg = _validate_secret_key(strong_key, "production")
        assert is_valid is True


class TestAuthDependencies:
    """Tests for FastAPI auth dependencies."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.is_active = True
        user.is_admin = False
        return user

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, mock_db, mock_user):
        """Test getting current user with valid token."""
        from backend.auth.dependencies import get_current_user_optional

        # Create valid token
        token = create_access_token(mock_user.id, mock_user.email)

        # Mock the credentials
        credentials = MagicMock()
        credentials.credentials = token

        # Mock database query
        with patch("backend.auth.dependencies.db_crud") as mock_crud:
            mock_crud.users.get_by_id = AsyncMock(return_value=mock_user)

            user = await get_current_user_optional(mock_db, credentials)

            assert user is not None
            assert user.id == mock_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_no_credentials(self, mock_db):
        """Test that missing credentials returns None (not exception)."""
        from backend.auth.dependencies import get_current_user_optional

        user = await get_current_user_optional(mock_db, None)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_db):
        """Test that invalid token raises HTTPException."""
        from backend.auth.dependencies import get_current_user_optional
        from fastapi import HTTPException

        credentials = MagicMock()
        credentials.credentials = "invalid-token"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_optional(mock_db, credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self, mock_db, mock_user):
        """Test that inactive user raises HTTPException."""
        from backend.auth.dependencies import get_active_user
        from fastapi import HTTPException

        mock_user.is_active = False

        with pytest.raises(HTTPException) as exc_info:
            await get_active_user(mock_user)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_admin_non_admin(self, mock_user):
        """Test that non-admin user raises HTTPException for admin routes."""
        from backend.auth.dependencies import require_admin
        from fastapi import HTTPException

        mock_user.is_admin = False

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_admin_user(self, mock_user):
        """Test that admin user passes admin check."""
        from backend.auth.dependencies import require_admin

        mock_user.is_admin = True

        result = await require_admin(mock_user)
        assert result == mock_user
