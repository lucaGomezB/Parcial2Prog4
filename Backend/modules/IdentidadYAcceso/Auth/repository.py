"""
Refresh token repository module.

Provides database access for RefreshToken entities, extending the
generic BaseRepository with domain-specific queries: finding valid
tokens by hash, listing expired tokens for cleanup, and hard deletion.
"""

from datetime import datetime

from sqlmodel import Session, select

from models.base_repository import BaseRepository
from modules.IdentidadYAcceso.RefreshToken.models import RefreshToken


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
            RefreshToken.expires_at > datetime.utcnow(),
        )
        return self.session.exec(statement).first()

    def get_expired(self) -> list[RefreshToken]:
        """
        Find all refresh tokens that have passed their expiration date.

        Used by cleanup_expired_tokens() to purge stale records
        and prevent database bloat.
        """
        statement = select(RefreshToken).where(
            RefreshToken.expires_at < datetime.utcnow()
        )
        return self.session.exec(statement).all()

    def delete(self, token: RefreshToken):
        """
        Permanently remove a refresh token from the database.

        Unlike soft-revocation (setting revoked_at), this performs a
        hard DELETE. Used only for expired token garbage collection.
        """
        self.session.delete(token)
