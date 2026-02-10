"""Authentication routes for LLM Council."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..database.connection import get_db
from ..database.models import User, RefreshToken
from ..database import crud
from sqlalchemy import select, func
from ..auth.password import hash_password, verify_password
from ..auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_token_hash,
)
from ..auth.oauth import verify_google_token, exchange_google_code
from ..auth.dependencies import get_current_user, get_current_admin_user
from ..rate_limit import limiter, RATE_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Email verification placeholder
async def send_verification_email(email: str, token: str, user_name: Optional[str] = None) -> None:
    """
    Placeholder for sending verification email.

    In production, this would integrate with an email service like:
    - SendGrid
    - AWS SES
    - Mailgun
    - Resend

    For now, it logs the verification link.
    """
    import os
    base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    verification_link = f"{base_url}/verify-email?token={token}"

    # Log the verification link (in production, send actual email)
    logger.info(
        f"[EMAIL VERIFICATION] "
        f"To: {email} | "
        f"Name: {user_name or 'User'} | "
        f"Link: {verification_link}"
    )

    # Print to console for development visibility
    print(f"\n{'='*60}")
    print(f"EMAIL VERIFICATION")
    print(f"{'='*60}")
    print(f"To: {email}")
    print(f"Subject: Verify your LLM Council account")
    print(f"")
    print(f"Hello {user_name or 'there'},")
    print(f"")
    print(f"Please verify your email by clicking the link below:")
    print(f"{verification_link}")
    print(f"")
    print(f"This link expires in 24 hours.")
    print(f"{'='*60}\n")


# Request/Response schemas

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: Optional[str] = None


class LoginRequest(BaseModel):
    """Email/password login request."""
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    """Google OAuth login request (ID token from frontend)."""
    credential: str


class GoogleCodeRequest(BaseModel):
    """Google OAuth code exchange request."""
    code: str
    redirect_uri: str


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    is_verified: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    warning: Optional[str] = None  # Optional warning (e.g., email not verified)


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


class VerifyEmailRequest(BaseModel):
    """Email verification request."""
    token: str


class ResendVerificationRequest(BaseModel):
    """Request to resend verification email."""
    email: EmailStr


# Helper functions

async def _store_refresh_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    token: str,
    expires_at: datetime,
    device_info: Optional[str] = None
) -> None:
    """Store refresh token hash in database."""
    token_hash = get_token_hash(token)
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=device_info,
    )
    db.add(refresh_token)
    await db.flush()  # Flush to ensure token is saved


async def _revoke_refresh_token(db: AsyncSession, token: str) -> bool:
    """Revoke a refresh token."""
    from sqlalchemy import update
    token_hash = get_token_hash(token)
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(is_revoked=True)
    )
    return result.rowcount > 0


async def _is_token_revoked(db: AsyncSession, token: str) -> bool:
    """Check if a refresh token is revoked."""
    from sqlalchemy import select
    token_hash = get_token_hash(token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False
        )
    )
    return result.scalar_one_or_none() is None


def _user_to_response(user: User) -> UserResponse:
    """Convert User model to response."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


# Routes

@router.post("/register", response_model=TokenResponse)
@limiter.limit(RATE_LIMITS["auth"])
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user with email and password."""
    try:
        # Check if email already exists
        existing = await crud.users.get_by_email(db, body.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check if this is the first real user (make them admin)
        # Exclude anonymous user from count
        from ..config import ANONYMOUS_USER_ID
        from sqlalchemy import select, func
        anonymous_id = uuid.UUID(ANONYMOUS_USER_ID)
        result = await db.execute(
            select(func.count(User.id)).where(User.id != anonymous_id)
        )
        real_user_count = result.scalar() or 0
        is_first_user = real_user_count == 0

        # Create user
        password_hash = hash_password(body.password)
        user = await crud.users.create(
            db,
            email=body.email,
            password_hash=password_hash,
            name=body.name,
            is_verified=False,
        )

        # Make first user an admin
        if is_first_user:
            await crud.users.update_user(db, user.id, is_admin=True)
            await db.flush()  # Flush to ensure admin status is updated
            await db.refresh(user)

        # Generate and send email verification token
        verification_token = await crud.email_verification.create_verification_token(db, user.id)
        await send_verification_email(user.email, verification_token, user.name)

        # Generate auth tokens
        access_token = create_access_token(user.id, user.email, user.is_admin)
        refresh_token, expires_at = create_refresh_token(user.id)

        # Store refresh token
        device_info = request.headers.get("User-Agent", "")[:255]
        await _store_refresh_token(db, user.id, refresh_token, expires_at, device_info)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=_user_to_response(user),
            warning="A verification email has been sent. Please check your inbox.",
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Registration error: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(RATE_LIMITS["auth"])
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password."""
    try:
        user = await crud.users.get_by_email(db, body.email)
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__

        # Check for specific Supabase errors
        if "tenant" in error_msg.lower() or "user not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection error: Invalid database credentials. Please check DATABASE_URL in Railway environment variables."
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {error_msg}"
        )

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Generate tokens
    access_token = create_access_token(user.id, user.email, user.is_admin)
    refresh_token, expires_at = create_refresh_token(user.id)

    # Store refresh token
    device_info = request.headers.get("User-Agent", "")[:255]
    await _store_refresh_token(db, user.id, refresh_token, expires_at, device_info)

    # Add warning if email not verified (don't block login)
    warning = None
    if not user.is_verified:
        warning = "Please verify your email address to ensure account security"

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_to_response(user),
        warning=warning,
    )


@router.post("/google", response_model=TokenResponse)
async def google_login(
    request: GoogleLoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """Login with Google (ID token from frontend Google Sign-In)."""
    # Verify Google token
    google_user = await verify_google_token(request.credential)

    if not google_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credentials"
        )

    google_id = google_user["id"]
    email = google_user["email"]

    # Find or create user
    user = await crud.users.get_by_google_id(db, google_id)

    if not user:
        # Check if email exists (link accounts)
        user = await crud.users.get_by_email(db, email)

        if user:
            # Link Google account to existing user
            await crud.users.update_user(
                db, user.id,
                google_id=google_id,
                avatar_url=google_user.get("picture"),
            )
        else:
            # Create new user
            user = await crud.users.create(
                db,
                email=email,
                google_id=google_id,
                name=google_user.get("name"),
                avatar_url=google_user.get("picture"),
                is_verified=google_user.get("verified_email", False),
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Generate tokens
    access_token = create_access_token(user.id, user.email, user.is_admin)
    refresh_token, expires_at = create_refresh_token(user.id)

    # Store refresh token
    device_info = req.headers.get("User-Agent", "")[:255]
    await _store_refresh_token(db, user.id, refresh_token, expires_at, device_info)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_to_response(user),
    )


@router.post("/google/code", response_model=TokenResponse)
async def google_code_exchange(
    request: GoogleCodeRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """Exchange Google authorization code for tokens (server-side OAuth)."""
    google_user = await exchange_google_code(request.code, request.redirect_uri)

    if not google_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to exchange Google code"
        )

    google_id = google_user["id"]
    email = google_user["email"]

    # Find or create user (same logic as google_login)
    user = await crud.users.get_by_google_id(db, google_id)

    if not user:
        user = await crud.users.get_by_email(db, email)
        if user:
            await crud.users.update_user(
                db, user.id,
                google_id=google_id,
                avatar_url=google_user.get("picture"),
            )
        else:
            user = await crud.users.create(
                db,
                email=email,
                google_id=google_id,
                name=google_user.get("name"),
                avatar_url=google_user.get("picture"),
                is_verified=google_user.get("verified_email", False),
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    access_token = create_access_token(user.id, user.email, user.is_admin)
    refresh_token, expires_at = create_refresh_token(user.id)

    device_info = req.headers.get("User-Agent", "")[:255]
    await _store_refresh_token(db, user.id, refresh_token, expires_at, device_info)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_to_response(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    # Decode refresh token
    payload = decode_refresh_token(request.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Check if token is revoked
    if await _is_token_revoked(db, request.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked"
        )

    # Get user
    user_id = payload.get("sub")
    user = await crud.users.get_by_id(db, uuid.UUID(user_id))

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated"
        )

    # Revoke old refresh token
    await _revoke_refresh_token(db, request.refresh_token)

    # Generate new tokens
    access_token = create_access_token(user.id, user.email, user.is_admin)
    new_refresh_token, expires_at = create_refresh_token(user.id)

    # Store new refresh token
    device_info = req.headers.get("User-Agent", "")[:255]
    await _store_refresh_token(db, user.id, new_refresh_token, expires_at, device_info)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=_user_to_response(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Logout and revoke refresh token."""
    await _revoke_refresh_token(db, request.refresh_token)
    return MessageResponse(message="Successfully logged out")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user's email address using the token sent via email.

    The token is a one-time-use token that expires after 24 hours.
    """
    # Verify the token and get user_id
    user_id = await crud.email_verification.verify_token(db, request.token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    # Get the user
    user = await crud.users.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if already verified
    if user.is_verified:
        return MessageResponse(message="Email already verified")

    # Mark user as verified
    await crud.users.verify_email(db, user_id)

    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit(RATE_LIMITS["auth"])
async def resend_verification(
    request: Request,
    body: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend verification email to user.

    Rate limited to prevent abuse.
    """
    # Find user by email
    user = await crud.users.get_by_email(db, body.email)

    if not user:
        # Don't reveal if email exists - return success anyway
        return MessageResponse(
            message="If an account exists with this email, a verification link has been sent"
        )

    # Check if already verified
    if user.is_verified:
        return MessageResponse(
            message="If an account exists with this email, a verification link has been sent"
        )

    # Check if user has OAuth-only account (no password set)
    if user.google_id and not user.password_hash:
        # Google accounts are auto-verified via Google
        return MessageResponse(
            message="If an account exists with this email, a verification link has been sent"
        )

    # Generate and send new verification token
    verification_token = await crud.email_verification.create_verification_token(db, user.id)
    await send_verification_email(user.email, verification_token, user.name)

    return MessageResponse(
        message="If an account exists with this email, a verification link has been sent"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    return _user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    updates = {}
    if name is not None:
        updates["name"] = name
    if avatar_url is not None:
        updates["avatar_url"] = avatar_url

    if updates:
        user = await crud.users.update_user(db, current_user.id, **updates)
        return _user_to_response(user)

    return _user_to_response(current_user)


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change password for current user."""
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account uses OAuth login only"
        )

    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    new_hash = hash_password(request.new_password)
    await crud.users.set_password(db, current_user.id, new_hash)

    return MessageResponse(message="Password changed successfully")


@router.post("/logout/all", response_model=MessageResponse)
async def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout from all devices (revoke all refresh tokens)."""
    from sqlalchemy import update
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id)
        .values(is_revoked=True)
    )
    return MessageResponse(message="Logged out from all devices")


# Admin endpoints
@router.get("/admin/users", response_model=List[UserResponse])
async def list_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)."""
    skip = (page - 1) * limit
    users = await crud.users.list_users(db, skip=skip, limit=limit, active_only=active_only)
    return [_user_to_response(user) for user in users]


@router.get("/admin/users/count", response_model=dict)
async def get_user_count(
    active_only: bool = Query(True),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get total user count (admin only)."""
    count = await crud.users.count_users(db, active_only=active_only)
    return {"total_users": count, "active_only": active_only}


@router.post("/admin/users/{user_id}/promote", response_model=UserResponse)
async def promote_to_admin(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Promote a user to admin (admin only)."""
    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    user = await crud.users.get_by_id(db, target_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await crud.users.update_user(db, target_user_id, is_admin=True)
    await db.flush()  # Flush to ensure admin status is updated in current transaction
    await db.refresh(user)
    
    return _user_to_response(user)


# Admin API Key Management
class SystemAPIKeyRequest(BaseModel):
    """Request to set a system-wide API key."""
    provider: str = Field(..., description="Provider name (openrouter, openai, anthropic, etc.)")
    api_key: str = Field(..., description="API key value")


@router.post("/admin/api-keys", response_model=dict)
async def set_system_api_key(
    request: SystemAPIKeyRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Set a system-wide API key (admin only)."""
    valid_providers = ["openrouter", "openai", "anthropic", "google", "x-ai", "deepseek", "mistralai", "cohere", "qwen"]
    if request.provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )
    
    await crud.api_keys.set_system_key(db, request.provider, request.api_key, encrypt=True)
    await db.flush()
    
    return {
        "status": "success",
        "message": f"System API key set for {request.provider}",
        "provider": request.provider
    }


@router.get("/admin/api-keys", response_model=dict)
async def get_system_api_keys(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all system API keys (masked, admin only)."""
    providers = ["openrouter", "openai", "anthropic", "google", "x-ai", "deepseek", "mistralai", "cohere", "qwen"]
    keys = {}
    
    for provider in providers:
        system_key = await crud.api_keys.get_system_key(db, provider)
        if system_key:
            # Mask the key
            if len(system_key) > 8:
                keys[provider] = system_key[:4] + "..." + system_key[-4:]
            else:
                keys[provider] = "***"
        else:
            keys[provider] = ""
    
    return {
        "api_keys": keys,
        "providers": providers
    }


@router.delete("/admin/api-keys/{provider}", response_model=dict)
async def delete_system_api_key(
    provider: str,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a system-wide API key (admin only)."""
    valid_providers = ["openrouter", "openai", "anthropic", "google", "x-ai", "deepseek", "mistralai", "cohere", "qwen"]
    if provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )

    deleted = await crud.api_keys.delete_system_key(db, provider)
    await db.flush()

    return {
        "status": "success",
        "message": f"System API key deleted for {provider}",
        "provider": provider,
        "deleted": deleted
    }


@router.delete("/admin/api-keys/clear-all", response_model=dict)
async def clear_all_encrypted_keys(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clear ALL encrypted API keys from the database (admin only).

    Use this when SECRET_KEY has changed and stored keys can no longer
    be decrypted. After clearing, users will need to re-enter their API keys.

    This operation:
    - Deletes all user API keys
    - Deletes all system API keys
    - Does NOT affect environment variable keys (like OPENROUTER_API_KEY in .env)

    Returns count of deleted keys.
    """
    result = await crud.api_keys.clear_all_encrypted_keys(db)
    await db.flush()

    return {
        "status": "success",
        "message": "All encrypted API keys cleared from database",
        **result,
        "note": "Environment variable keys (like OPENROUTER_API_KEY) are unaffected"
    }


# Diagnostic endpoint for debugging authentication issues
@router.get("/debug/token", response_model=dict)
async def debug_token(
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Debug endpoint to diagnose JWT token validation issues.

    Returns detailed information about:
    - Whether a token is present
    - Token decode status
    - Specific failure reasons
    - Environment configuration status

    This endpoint is intentionally public for debugging authentication issues.
    """
    import os
    from ..auth.jwt_handler import decode_access_token, SECRET_KEY
    from jose import jwt, JWTError

    result = {
        "token_present": False,
        "token_valid": False,
        "decode_success": False,
        "user_found": False,
        "user_active": False,
        "failure_reason": None,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "secret_key_set": bool(os.getenv("SECRET_KEY")),
        "secret_key_source": "env" if os.getenv("SECRET_KEY") else "default",
    }

    # Get Authorization header
    auth_header = req.headers.get("Authorization")
    if not auth_header:
        result["failure_reason"] = "No Authorization header present"
        return result

    if not auth_header.startswith("Bearer "):
        result["failure_reason"] = "Authorization header does not start with 'Bearer '"
        return result

    token = auth_header[7:]  # Remove "Bearer " prefix
    result["token_present"] = True
    result["token_length"] = len(token)

    # Try to decode without verification first (to see payload structure)
    try:
        unverified = jwt.get_unverified_claims(token)
        result["token_claims_readable"] = True
        result["token_type"] = unverified.get("type")
        result["token_user_id"] = unverified.get("sub")
        result["token_email"] = unverified.get("email")
        result["token_exp"] = unverified.get("exp")
        result["token_iat"] = unverified.get("iat")

        # Check expiration manually
        from datetime import datetime, timezone
        exp = unverified.get("exp")
        if exp:
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            result["token_expired"] = exp_dt < now
            result["token_exp_human"] = exp_dt.isoformat()
            result["current_time"] = now.isoformat()
            if result["token_expired"]:
                result["failure_reason"] = f"Token expired at {exp_dt.isoformat()}"
    except Exception as e:
        result["token_claims_readable"] = False
        result["unverified_decode_error"] = str(e)

    # Now try verified decode
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        result["decode_success"] = True
        result["verified_payload"] = True

        # Check token type
        if payload.get("type") != "access":
            result["failure_reason"] = f"Wrong token type: {payload.get('type')} (expected 'access')"
            return result

        result["token_valid"] = True

        # Try to find user
        user_id = payload.get("sub")
        if user_id:
            try:
                user = await crud.users.get_by_id(db, uuid.UUID(user_id))
                if user:
                    result["user_found"] = True
                    result["user_email"] = user.email
                    result["user_active"] = user.is_active
                    if not user.is_active:
                        result["failure_reason"] = "User account is deactivated"
                else:
                    result["failure_reason"] = f"User not found in database: {user_id}"
            except ValueError:
                result["failure_reason"] = f"Invalid user ID format: {user_id}"
        else:
            result["failure_reason"] = "No 'sub' (user_id) claim in token"

    except JWTError as e:
        result["decode_success"] = False
        result["jwt_error"] = str(e)
        result["failure_reason"] = f"JWT decode failed: {str(e)} (likely SECRET_KEY mismatch between login and validation)"
    except Exception as e:
        result["decode_success"] = False
        result["unexpected_error"] = str(e)
        result["failure_reason"] = f"Unexpected error: {str(e)}"

    return result
