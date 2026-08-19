"""
Core security utilities — password hashing, JWT management, and configuration.

Centralises all security infrastructure that was previously scattered across
Auth and Usuario modules. Domain modules consume from here instead of
implementing their own security logic.

Usage:
    from app.core.security import get_password_hash, verify_password
    from app.core.security import create_access_token, decode_token
    from app.core.security import TokenData, Settings, settings
"""

from .config import Settings, settings
from .passwords import get_password_hash, verify_password
from .tokens import TokenData, create_access_token, decode_token

__all__ = [
    "Settings", "settings",
    "get_password_hash", "verify_password",
    "TokenData", "create_access_token", "decode_token",
]
