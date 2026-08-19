"""
HistorialStock models — Append-only stock audit log.

This is an APPEND-ONLY table: rows are INSERTed, never UPDATEd or DELETEd.
Every stock mutation in the system (product or ingredient) creates one row.
"""
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HistorialStock(SQLModel, table=True):
    """Append-only audit log for product and ingredient stock changes."""

    __tablename__ = "historialstock"

    id: Optional[int] = Field(default=None, primary_key=True)
    entidad_tipo: str = Field(max_length=20, nullable=False)
    entidad_id: int = Field(nullable=False)
    stock_anterior: int = Field(nullable=False)
    stock_nuevo: int = Field(nullable=False)
    motivo: str = Field(max_length=30, nullable=False)
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuario.id", ondelete="SET NULL")
    # Append-only — only created_at, no updated_at
    created_at: datetime = Field(default_factory=_get_utc_now, nullable=False)
