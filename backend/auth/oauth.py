"""Google OAuth authentication."""

import os
from typing import Optional, Dict, Any

import httpx
from pydantic import BaseModel


# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

# Google OAuth endpoints
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


class GoogleUser(BaseModel):
    """Google user profile data."""
    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    verified_email: bool = False


async def verify_google_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Google ID token (from frontend Google Sign-In).
    Returns user info if valid, None otherwise.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Verify with Google's tokeninfo endpoint
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            )

            if response.status_code != 200:
                return None

            data = response.json()

            # Verify audience (client ID)
            if data.get("aud") != GOOGLE_CLIENT_ID:
                return None

            return {
                "id": data.get("sub"),
                "email": data.get("email"),
                "name": data.get("name"),
                "picture": data.get("picture"),
                "verified_email": data.get("email_verified") == "true",
            }

    except Exception:
        return None


async def exchange_google_code(code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
    """
    Exchange Google authorization code for tokens and user info.
    Used for traditional OAuth flow (server-side).
    """
    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            if token_response.status_code != 200:
                return None

            tokens = token_response.json()
            access_token = tokens.get("access_token")

            if not access_token:
                return None

            # Get user info
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_response.status_code != 200:
                return None

            user_data = userinfo_response.json()

            return {
                "id": user_data.get("sub"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "picture": user_data.get("picture"),
                "verified_email": user_data.get("email_verified", False),
            }

    except Exception:
        return None


def get_google_auth_url(redirect_uri: str, state: Optional[str] = None) -> str:
    """Generate Google OAuth authorization URL."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }

    if state:
        params["state"] = state

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"
