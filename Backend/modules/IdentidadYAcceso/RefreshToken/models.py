from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from models.base import get_utc_now


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_token"

    id: Optional[int] = Field(default=None, primary_key=True)  # BIGSERIAL

    usuario_id: int = Field(
        foreign_key="usuario.id",
        ondelete="CASCADE",   # Strong: if user deleted, ALL their refresh tokens are deleted
        nullable=False
    )

    token_hash: str = Field(
        unique=True,
        max_length=64,
        nullable=False
    )  # SHA-256 hex digest = 64 chars

    expires_at: datetime = Field(nullable=False)       # TIMESTAMPZ
    revoked_at: Optional[datetime] = Field(default=None)  # TIMESTAMPZ, NULL = valid token

    created_at: datetime = Field(
        default_factory=get_utc_now,
        nullable=False
    )

    usuario: "Usuario" = Relationship(back_populates="refresh_tokens")
