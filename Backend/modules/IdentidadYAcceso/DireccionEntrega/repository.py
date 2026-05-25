from sqlmodel import Session, col, select

from .models import DireccionEntrega


class DireccionEntregaRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, direccion: DireccionEntrega):
        self.session.add(direccion)
        return direccion

    def flush(self):
        self.session.flush()

    def refresh(self, direccion: DireccionEntrega):
        self.session.refresh(direccion)
        return direccion

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
