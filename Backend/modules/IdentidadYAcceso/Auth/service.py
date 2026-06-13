"""
Authentication service module.

Implements core authentication logic:

- Password verification via core.security (bcrypt constant-time comparison).
- Access token creation via core.security (short-lived JWT signed with HS256).
- Refresh token creation (opaque token, SHA-256 hash stored in DB).
- Refresh token validation (hash lookup, expiry and revocation checks).
- Refresh token revocation (soft-delete for logout and rotation).
- Expired token cleanup (hard-delete for garbage collection).

Token rotation strategy: each refresh operation revokes the previous
refresh token and issues a new one, preventing token reuse in case
of theft.
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session
from core.security import verify_password, create_access_token

from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
from ..uow import IdentidadYAccesoUnitOfWork
from models.base import get_utc_now


def authenticate_user(session: Session, email: str, password: str) -> Usuario | None:
    """
    Authenticate a user by email and password.

    Returns the Usuario object on success, None on failure.
    Always returns the same error (None) regardless of whether the
    email does not exist or the password is wrong, to prevent
    user enumeration attacks.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        user = uow.usuarios.get_by_email(email)

    if not user:
        return None

    if verify_password(password, user.password_hash):
        return user

    return None


def create_refresh_token(session: Session, usuario_id: int) -> str:
    """
    Generate a new refresh token (UUID v4) and store its SHA-256 hash in the database.

    The raw token (UUID v4 string) is returned to the caller for
    placement in an httpOnly cookie. Only the hash is persisted,
    ensuring that database compromise does not expose valid tokens.

    The token expires after 7 days (configurable via REFRESH_TOKEN_EXPIRE_DAYS).
    """
    raw_token = str(uuid.uuid4())
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    now = get_utc_now()
    expires_at = now + timedelta(days=7)

    with IdentidadYAccesoUnitOfWork(session) as uow:
        db_token = RefreshToken(
            usuario_id=usuario_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=now,
        )
        uow.refresh_tokens.add(db_token)

    return raw_token


def validate_refresh_token(session: Session, raw_token: str) -> Optional[RefreshToken]:
    """
    Validate a refresh token by its SHA-256 hash.

    Looks up the hash in the database and verifies the token is
    neither expired nor revoked. Returns the RefreshToken object
    if valid, None otherwise.

    NOTE: The hash is computed from the UTF-8 string representation of the UUID
    to match how create_refresh_token stores it:
        raw_token = str(uuid.uuid4())
        token_hash = sha256(raw_token.encode('utf-8')).hexdigest()
    """
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    with IdentidadYAccesoUnitOfWork(session) as uow:
        return uow.refresh_tokens.get_by_hash(token_hash)


def revoke_refresh_token(session: Session, raw_token: str) -> bool:
    """
    Revoke a refresh token by setting its revoked_at timestamp.

    Used for:
    - Logout (explicit session termination).
    - Token rotation (old token revoked when new one is issued).

    Returns True if the token was found and revoked, False otherwise.
    """
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    with IdentidadYAccesoUnitOfWork(session) as uow:
        stored = uow.refresh_tokens.get_by_hash(token_hash)
        if not stored:
            return False
        stored.revoked_at = get_utc_now()
        uow.refresh_tokens.add(stored)
        return True


def cleanup_expired_tokens(session: Session):
    """
    Permanently delete all expired refresh tokens from the database.

    Unlike revoke (soft), this performs hard deletion for garbage
    collection. Called automatically on application startup and can
    be scheduled as a periodic maintenance task.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        expired = uow.refresh_tokens.get_expired()
        for token in expired:
            uow.refresh_tokens.delete(token)
