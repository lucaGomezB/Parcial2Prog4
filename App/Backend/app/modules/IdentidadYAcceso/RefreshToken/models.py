"""
RefreshToken domain model module.

Defines the SQLModel table for refresh token storage. Only the SHA-256
hash of each token is persisted — never the raw token value — ensuring
that database compromise does not expose active session tokens.

Key design decisions:
- token_hash (SHA-256): enables lookup without storing the raw token.
- expires_at: natural expiration (7 days by default).
- revoked_at: soft-revocation for logout and token rotation.
- CASCADE on user delete: tokens are cleaned up automatically.
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from app.core.base import get_utc_now


class RefreshToken(SQLModel, table=True):
    """
    Refresh token entity — stored in the 'refresh_token' table.

    Stores the SHA-256 hash of each refresh token along with its
    expiration and revocation status. The raw token (64-char hex)
    is returned to the client via httpOnly cookie and never persisted.

    Fields:
        id: Auto-generated primary key.
        usuario_id: FK to usuario.id (CASCADE on user delete).
        token_hash: SHA-256 hex digest of the raw token (unique, 64 chars).
        expires_at: Token expiration timestamp.
        revoked_at: Optional revocation timestamp (NULL = active).
        created_at: Token creation timestamp.

    Relationships:
        usuario: Parent user (back_populates refresh_tokens).
    """
    __tablename__ = "refresh_token"

    id: Optional[int] = Field(default=None, primary_key=True)

    usuario_id: int = Field(
        foreign_key="usuario.id",
        ondelete="CASCADE",
        nullable=False
    )

    token_hash: str = Field(
        unique=True,
        max_length=64,
        nullable=False
    )

    expires_at: datetime = Field(nullable=False)
    revoked_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(
        default_factory=get_utc_now,
        nullable=False
    )

    usuario: "Usuario" = Relationship(back_populates="refresh_tokens")
