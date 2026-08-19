"""
DireccionEntrega (Delivery Address) repository module.

Provides database access for delivery addresses with user-scoped queries:
finding addresses by user, retrieving the principal address, and soft-delete
filtering.
"""

from sqlmodel import Session, col, select

from app.core.base_repository import BaseRepository
from .models import DireccionEntrega


class DireccionEntregaRepository(BaseRepository[DireccionEntrega]):
    """
    Repository for delivery address operations.

    Overrides base get_by_id and get_all to add soft-delete filtering.
    Provides user-scoped queries: get_by_usuario, get_principal.
    """

    def __init__(self, session: Session):
        super().__init__(session, DireccionEntrega)

    def get_by_id(self, direccion_id: int) -> DireccionEntrega | None:
        """Find an address by ID, excluding soft-deleted records."""
        statement = (
            select(DireccionEntrega)
            .where(DireccionEntrega.id == direccion_id, col(DireccionEntrega.deleted_at).is_(None))
        )
        return self.session.exec(statement).first()

    def get_by_usuario(self, usuario_id: int) -> list[DireccionEntrega]:
        """Get all non-deleted addresses for a specific user, principal first."""
        statement = (
            select(DireccionEntrega)
            .where(DireccionEntrega.usuario_id == usuario_id, col(DireccionEntrega.deleted_at).is_(None))
            .order_by(DireccionEntrega.es_principal.desc(), DireccionEntrega.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_principal(self, usuario_id: int) -> DireccionEntrega | None:
        """Get the user's principal (default) delivery address, if any."""
        statement = (
            select(DireccionEntrega)
            .where(
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.es_principal == True,
                col(DireccionEntrega.deleted_at).is_(None),
            )
        )
        return self.session.exec(statement).first()

    def get_all(self, usuario_id: int | None = None) -> list[DireccionEntrega]:
        """
        Get all non-deleted addresses, optionally filtered by user.

        When usuario_id is None, returns addresses for all users (admin view).
        Ordered by creation date descending.
        """
        statement = select(DireccionEntrega).where(col(DireccionEntrega.deleted_at).is_(None))
        if usuario_id is not None:
            statement = statement.where(DireccionEntrega.usuario_id == usuario_id)
        statement = statement.order_by(DireccionEntrega.created_at.desc())
        return self.session.exec(statement).all()

    def get_locales(self) -> list[DireccionEntrega]:
        """Get all non-deleted company stores/locations (es_local=True)."""
        statement = (
            select(DireccionEntrega)
            .where(
                DireccionEntrega.es_local == True,
                col(DireccionEntrega.deleted_at).is_(None),
            )
            .order_by(DireccionEntrega.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_by_usuario_with_locales(self, usuario_id: int, incluir_locales: bool = False) -> list[DireccionEntrega]:
        """
        Get user's addresses, optionally including all company stores (locales).

        When incluir_locales=True, returns user-scoped addresses UNION all locales,
        ordered by: locales first, then principal first, then created_at desc.
        """
        if not incluir_locales:
            return self.get_by_usuario(usuario_id)

        # Get user's own addresses + all locales
        user_addr = self.get_by_usuario(usuario_id)
        locales = self.get_locales()
        # Deduplicate by id (possible if user owns a local)
        existing_ids = {a.id for a in user_addr}
        combined = list(user_addr)
        for loc in locales:
            if loc.id not in existing_ids:
                combined.append(loc)

        # Sort: es_local first (locales), then es_principal first, then created_at desc
        combined.sort(
            key=lambda a: (
                not a.es_local,
                not a.es_principal,
                -(a.created_at.timestamp() if a.created_at else 0),
            )
        )
        return combined
