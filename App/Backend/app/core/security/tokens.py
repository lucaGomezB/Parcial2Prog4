"""
JWT token creation and decoding.

Access tokens are signed JWTs (HS256) containing user identification data.
The module provides:
    - TokenData: Pydantic model for JWT payload structure.
    - create_access_token: Sign and return a new JWT.
    - decode_token: Verify and decode a JWT, returning TokenData or None.
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import jwt
from .config import settings


class TokenData(BaseModel):
    """Payload structure embedded inside the JWT.

    NOT a request/response schema — used internally for encoding
    and decoding JWT payloads.

    Attributes:
        user_id: Database ID of the authenticated user.
        email: Email of the authenticated user (for display purposes).
        roles: List of role codes assigned to the user (e.g., ["CLIENT", "ADMIN"]).
    """
    user_id: int
    email: str
    roles: list[str] = []


def create_access_token(data: TokenData, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token with user data.

    The token payload includes: user_id, email, exp (expiration),
    and iat (issued at). The token is signed with HMAC-SHA256
    using the configured SECRET_KEY.
    """
    to_encode = data.model_dump()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and verify a JWT token.

    Verifies the HMAC-SHA256 signature using SECRET_KEY and checks
    expiration (exp claim). Returns TokenData if valid, None if the
    token is invalid, expired, or malformed.

    Note: Returns None for all error cases (invalid, expired, malformed)
    rather than raising exceptions. The caller decides how to handle
    authentication failures (e.g., 401 vs optional auth).
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return TokenData(**payload)
    except jwt.InvalidTokenError:
        return None
