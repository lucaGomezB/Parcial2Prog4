"""
CarritoSnapshot repository — data access layer for cart snapshots.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, delete, col

from app.core.base_repository import BaseRepository
from .models import CarritoSnapshot


class CarritoSnapshotRepository(BaseRepository[CarritoSnapshot]):
    """Repository for CarritoSnapshot CRUD and TTL cleanup.

    Inherits from BaseRepository[CarritoSnapshot] for standard CRUD operations
    (create, add, get_by_id, get_all, count_all, search, flush, refresh, with_deleted).
    Overrides delete() for hard-delete since CarritoSnapshot uses TTL, not soft-delete.
    """

    def __init__(self, session: Session):
        super().__init__(session, CarritoSnapshot)

    def get_by_external_reference(self, external_reference: str) -> Optional[CarritoSnapshot]:
        """Lookup a snapshot by its external_reference (shared with Pago)."""
        statement = select(CarritoSnapshot).where(
            CarritoSnapshot.external_reference == external_reference
        )
        return self.session.exec(statement).first()

    def delete(self, snapshot: CarritoSnapshot) -> None:
        """Hard delete — CarritoSnapshot uses TTL, not soft-delete."""
        self.session.delete(snapshot)

    def delete_expired(self) -> int:
        """Delete all snapshots where expires_at < NOW(). Returns count deleted."""
        now = datetime.now(timezone.utc)
        statement = delete(CarritoSnapshot).where(
            col(CarritoSnapshot.expires_at) < now
        )
        result = self.session.exec(statement)
        self.session.flush()
        return result.rowcount
