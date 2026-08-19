"""
Authentication service module.

Implements core authentication logic:

- Password verification via core.security (bcrypt constant-time comparison).
- Access token creation via core.security (short-lived JWT signed with HS256).
- Refresh token creation (opaque token, SHA-256 hash stored in DB).
- Refresh token validation (hash lookup, expiry and revocation checks).
- Refresh token revocation (soft-delete for logout and rotation).
- Refresh token rotation: full flow (FOR UPDATE, replay detection, rotation, cookie).
- Expired token cleanup (hard-delete for garbage collection).

Token rotation strategy: each refresh operation revokes the previous
refresh token and issues a new one, preventing token reuse in case
of theft.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Request, Response, status
from sqlmodel import Session
from app.core.security import settings, verify_password, create_access_token, TokenData

from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from app.modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
from ..uow import IdentidadYAccesoUnitOfWork
from app.core.base import get_utc_now
from .schemas import TokenResponse

COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400  # Convert days to seconds


def _set_refresh_cookie(request: Request, response: Response, token: str):
    """
    Helper to set the refresh_token as an httpOnly cookie.

    Configuration:
    - httponly=True: prevents JavaScript access (XSS protection).
    - samesite="lax": CSRF protection (cookie sent only for same-site requests).
    - secure=True: only sent over HTTPS (prevents man-in-the-middle).
    - path="/": cookie sent on all requests (including Vite proxy path /api/...).
    - max_age: cookie lifetime in seconds (matches token lifetime).
    """
    secure = request.url.scheme == "https"
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def _clear_refresh_cookie(response: Response):
    """
    Helper to remove the refresh_token cookie from the client.

    Must use the same path as _set_refresh_cookie for the deletion
    to take effect. Used during logout and failed refresh validation.
    """
    response.delete_cookie(
        key="refresh_token",
        path="/",
    )


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
        uow.refresh_tokens.create(db_token)

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
        uow.refresh_tokens.update(stored)
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


class AuthService:
    """
    Authentication service class for operations that require request/response
    object access (cookie handling).

    Module-level functions handle simpler operations. This class encapsulates
    the full token rotation flow which requires HTTP cookie manipulation.
    """

    @staticmethod
    def refresh_token(
        session: Session,
        raw_token: str,
        request: Request,
        response: Response,
    ) -> TokenResponse:
        """
        Refresh access token using refresh token rotation.

        Reads the refresh_token from the httpOnly cookie (not from the request body).
        Implements TOKEN ROTATION with row-level locking (SELECT ... FOR UPDATE):
        the old token is atomically validated and revoked in a single operation,
        preventing the TOCTOU race between concurrent refresh calls.

        Flow (all within a single UoW transaction):
        1. Hash raw_token and call get_by_hash_for_update (locks the row).
        2. If found: revoke directly (we already hold the lock).
        3. If not found: check for replay attack pattern.
        4. Look up the user and issue a new token pair.
        5. Set the new refresh_token in the cookie.

        Returns TokenResponse with the new access token.
        Raises HTTPException(401) on any validation failure.
        """
        logger = logging.getLogger(__name__)
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

        with IdentidadYAccesoUnitOfWork(session) as uow:
            # Atomically find AND lock the token row.
            # SELECT ... FOR UPDATE prevents concurrent refresh calls from both
            # passing validation before either has a chance to revoke (TOCTOU race).
            stored_token = uow.refresh_tokens.get_by_hash_for_update(token_hash)

            if not stored_token:
                # Token is not valid (expired, revoked, or never existed).
                # Check if this is a replay attack (hash exists but was already revoked).
                was_revoked = uow.refresh_tokens.get_by_hash_including_revoked(token_hash)

                if was_revoked and was_revoked.revoked_at is not None:
                    # Replay attack detected — revoke ALL active tokens for this user
                    logger.warning(
                        "REPLAY ATTACK DETECTED: revoked token reused for usuario_id=%s. "
                        "Revoking ALL active tokens.",
                        was_revoked.usuario_id,
                    )
                    uow.refresh_tokens.revoke_all_for_user(was_revoked.usuario_id)

                _clear_refresh_cookie(response)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token invalido o expirado",
                )

            # Token is valid and we hold the row lock — revoke it NOW (token rotation).
            # Because we used FOR UPDATE, no concurrent transaction could have
            # validated this same token between our lookup and this revocation.
            stored_token.revoked_at = get_utc_now()
            uow.refresh_tokens.update(stored_token)

            # Retrieve the token owner with eager-loaded roles
            user = uow.usuarios.get_with_roles(stored_token.usuario_id)
            if not user:
                _clear_refresh_cookie(response)
                raise HTTPException(status_code=401, detail="Usuario no encontrado")

            # Issue new access token
            token_data = TokenData(
                user_id=user.id,
                email=user.email,
                roles=[rol.codigo for rol in user.roles]
            )
            access_token = create_access_token(
                token_data,
                timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )

            # Create new refresh token inline (same UoW, no nesting)
            raw_new_token = str(uuid.uuid4())
            new_hash = hashlib.sha256(raw_new_token.encode('utf-8')).hexdigest()
            now = get_utc_now()
            db_token = RefreshToken(
                usuario_id=user.id,
                token_hash=new_hash,
                expires_at=now + timedelta(days=7),
                created_at=now,
            )
        uow.refresh_tokens.create(db_token)

        # After UoW commit — set cookie and return
        _set_refresh_cookie(request, response, raw_new_token)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
