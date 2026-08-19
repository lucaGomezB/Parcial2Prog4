"""
Pydantic schemas for authentication endpoints.

Defines request and response models for login, token refresh,
and token data extraction. These schemas define the contract
between the API layer and its consumers.

- LoginRequest: input model for POST /auth/login.
- TokenResponse: output model for successful authentication.
- TokenData: internal model for JWT payload structure.
- RefreshRequest: input model for token refresh (body alternative).
"""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Request body for user login. Accepts email and password."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """
    Response body returned after successful authentication.

    Contains the access_token (short-lived JWT). The refresh_token
    is set exclusively as an httpOnly cookie and is NOT included
    in the response body for security reasons (XSS protection).

    Attributes:
        access_token: JWT string for Authorization header.
        token_type: Always "bearer" per RFC 6750.
        expires_in: Access token lifetime in seconds.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """
    Alternative request body for token refresh.

    Used when the refresh token cannot be sent as a cookie
    (e.g., mobile apps, third-party clients).
    """
    refresh_token: str
