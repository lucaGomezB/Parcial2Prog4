from sqlmodel import Session, select, col
from sqlalchemy.orm import selectinload

from .models import Usuario
from ..usuario_rol import UsuarioRol
from models.base_repository import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: Session):
        super().__init__(session, Usuario)

    def get_by_email(self, email: str) -> Usuario | None:
        statement = select(Usuario).where(Usuario.email == email)
        return self.session.exec(statement).first()

    def get_all_by_role(self, rol_codigo: str, skip: int = 0, limit: int = 100):
        """Fetch paginated users filtered by role code (JOIN via UsuarioRol)."""
        statement = (
            select(Usuario)
            .join(UsuarioRol, Usuario.id == UsuarioRol.usuario_id)
            .where(UsuarioRol.rol_codigo == rol_codigo)
        )
        if self._is_soft_delete:
            statement = statement.where(col(Usuario.deleted_at).is_(None))
        statement = (
            statement
            .options(selectinload(Usuario.roles))
            .offset(skip)
            .limit(limit)
            .order_by(Usuario.id.desc())
        )
        return self.session.exec(statement).all()
