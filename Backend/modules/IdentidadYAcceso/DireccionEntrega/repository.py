from sqlmodel import Session, col, select

from models.base_repository import BaseRepository
from .models import DireccionEntrega


class DireccionEntregaRepository(BaseRepository[DireccionEntrega]):
    def __init__(self, session: Session):
        super().__init__(session, DireccionEntrega)

    def get_by_id(self, direccion_id: int) -> DireccionEntrega | None:
        statement = (
            select(DireccionEntrega)
            .where(DireccionEntrega.id == direccion_id, col(DireccionEntrega.deleted_at).is_(None))
        )
        return self.session.exec(statement).first()

    def get_by_usuario(self, usuario_id: int) -> list[DireccionEntrega]:
        statement = (
            select(DireccionEntrega)
            .where(DireccionEntrega.usuario_id == usuario_id, col(DireccionEntrega.deleted_at).is_(None))
            .order_by(DireccionEntrega.es_principal.desc(), DireccionEntrega.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_principal(self, usuario_id: int) -> DireccionEntrega | None:
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
        statement = select(DireccionEntrega).where(col(DireccionEntrega.deleted_at).is_(None))
        if usuario_id is not None:
            statement = statement.where(DireccionEntrega.usuario_id == usuario_id)
        statement = statement.order_by(DireccionEntrega.created_at.desc())
        return self.session.exec(statement).all()
