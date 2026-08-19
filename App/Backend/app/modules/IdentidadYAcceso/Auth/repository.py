"""
Repository module for authentication.

Provides:
- AuthRepository: user lookup by email (authentication).
- RefreshTokenRepository: refresh token lifecycle management.
"""

from sqlmodel import Session, select

from app.core.base import get_utc_now
from app.core.base_repository import BaseRepository
from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from app.modules.IdentidadYAcceso.RefreshToken.models import RefreshToken


class AuthRepository(BaseRepository[Usuario]):
    """
    Repository for user authentication lookups.

    Provides the find_by_email method used by authenticate_user
    to locate a user by their email address.
    """

    def __init__(self, session: Session):
        super().__init__(session, Usuario)

    def find_by_email(self, email: str) -> Usuario | None:
        """Find a user by email. Returns None if not found."""
        statement = select(Usuario).where(Usuario.email == email)
        return self.session.exec(statement).first()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """
    Repository for RefreshToken CRUD operations.

    Extends BaseRepository with auth-specific queries:
    - get_by_hash: finds non-revoked, non-expired tokens by SHA-256 hash.
    - get_expired: finds all tokens past their expiration date.
    - delete: hard-deletes a token record.
    """

    def __init__(self, session: Session):
        super().__init__(session, RefreshToken)

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """
        Find a valid (non-revoked, non-expired) refresh token by its SHA-256 hash.

        Three conditions must hold:
        1. token_hash matches (exact lookup).
        2. revoked_at IS NULL (token not yet invalidated).
        3. expires_at > now (token not expired).
        """
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > get_utc_now(),
        )
        return self.session.exec(statement).first()

    def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        """
        Find a valid refresh token by hash WITH row-level lock (FOR UPDATE).

        Uses SELECT ... FOR UPDATE to serialize concurrent refresh attempts.
        Only one transaction can hold the lock on this row at a time,
        preventing the TOCTOU race between validation and revocation
        in the /auth/refresh endpoint.

        Same filtering as get_by_hash: non-revoked, non-expired tokens only.
        """
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > get_utc_now(),
        ).with_for_update()
        return self.session.exec(statement).first()

    def get_by_hash_including_revoked(self, token_hash: str) -> RefreshToken | None:
        """
        Find a refresh token by its SHA-256 hash, INCLUDING revoked tokens.

        Unlike get_by_hash, this method does NOT filter by revoked_at IS NULL.
        Used for replay attack detection: we need to find a token even if it
        was already revoked in a previous rotation.

        Also does NOT filter by expiration — a revoked token might be expired
        but we still need to detect the replay pattern.
        """
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
        return self.session.exec(statement).first()

    def revoke_all_for_user(self, usuario_id: int):
        """
        Revoke ALL non-expired, non-revoked refresh tokens for a user.

        Used when a replay attack is detected: we assume the user's session
        has been compromised and invalidate every active token they hold.

        Only revokes tokens that are still active (not yet revoked and not
        yet expired) to avoid touching already-invalidated records.
        """
        now = get_utc_now()
        statement = select(RefreshToken).where(
            RefreshToken.usuario_id == usuario_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        active_tokens = self.session.exec(statement).all()
        for token in active_tokens:
            token.revoked_at = now
            self.session.add(token)

    def get_expired(self) -> list[RefreshToken]:
        """
        Find all refresh tokens that have passed their expiration date.

        Used by cleanup_expired_tokens() to purge stale records
        and prevent database bloat.
        """
        statement = select(RefreshToken).where(
            RefreshToken.expires_at < get_utc_now()
        )
        return self.session.exec(statement).all()

    def delete(self, token: RefreshToken):
        """
        Permanently remove a refresh token from the database.

        Unlike soft-revocation (setting revoked_at), this performs a
        hard DELETE. Used only for expired token garbage collection.
        """
        self.session.delete(token)
