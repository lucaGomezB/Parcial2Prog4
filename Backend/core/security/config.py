"""
JWT configuration — loaded from environment variables.

The settings singleton is imported by auth services and dependencies
to sign and verify tokens. In production, SECRET_KEY MUST be set in .env.

Security notes:
    - SECRET_KEY: Keep secret. If missing, a temporary key is generated
      (development only — all existing tokens invalidated on restart).
    - ALGORITHM: HS256 (HMAC-SHA256) symmetric signing.
    - ACCESS_TOKEN_EXPIRE_MINUTES: Short-lived (30m default).
    - REFRESH_TOKEN_EXPIRE_DAYS: Long-lived (7d default).
"""

import os
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    """JWT configuration parameters loaded from environment.

    Attributes:
        SECRET_KEY: Master key for signing JWTs. Keep secret.
        ALGORITHM: Signing algorithm (HS256 = HMAC-SHA256 symmetric).
        ACCESS_TOKEN_EXPIRE_MINUTES: Short-lived access token TTL.
        REFRESH_TOKEN_EXPIRE_DAYS: Long-lived refresh token TTL.
    """
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


def get_settings() -> Settings:
    """Factory that reads JWT settings from environment variables.

    Falls back to a temporary random key if SECRET_KEY is not set.
    In production, SECRET_KEY MUST be configured in .env; regenerating
    it on each restart invalidates all existing tokens.
    """
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        import secrets
        secret_key = secrets.token_hex(32)
        print("WARNING: SECRET_KEY not configured in .env. Using temporary key.")
        print("   Add SECRET_KEY=your_secret_key to .env for production.")

    return Settings(
        SECRET_KEY=secret_key,
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        REFRESH_TOKEN_EXPIRE_DAYS=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    )


# Module-level singleton: import from core.security as:
#   from core.security import settings
settings = get_settings()
