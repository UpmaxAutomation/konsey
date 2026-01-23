"""Authentication module for LLM Council."""

from .password import hash_password, verify_password
from .jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from .dependencies import get_current_user, get_current_user_optional

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    "get_current_user",
    "get_current_user_optional",
]
