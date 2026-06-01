"""
Unit of Work module for the Identidad Y Acceso (Identity & Access) bounded context.

Implements the Unit of Work pattern to coordinate transactions across
multiple repositories within a single database session. This ensures
that operations spanning users, roles, addresses, and tokens are
committed atomically or rolled back together on failure.

Repositories exposed:
- direcciones: DireccionEntregaRepository
- usuarios: UsuarioRepository
- roles: RolRepository
- refresh_tokens: RefreshTokenRepository
"""

from sqlmodel import Session

from .Auth.repository import RefreshTokenRepository
from .DireccionEntrega.repository import DireccionEntregaRepository
from .Rol.repository import RolRepository
from .Usuario.repository import UsuarioRepository


class IdentidadYAccesoUnitOfWork:
    """
    Unit of Work for Identity & Access domain transactions.

    Usage:
        with IdentidadYAccesoUnitOfWork(session) as uow:
            uow.usuarios.add(new_user)
            uow.roles.add(new_role)
            # Auto-commits on success, rollbacks on exception

    The context manager (__enter__/__exit__) handles commit/rollback
    automatically. If an exception occurs, the transaction is rolled back.
    """

    def __init__(self, session: Session):
        self.session = session
        self.direcciones = DireccionEntregaRepository(session)
        self.usuarios = UsuarioRepository(session)
        self.roles = RolRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        return False  # Re-raise exceptions if any

    def flush(self):
        """Send pending SQL to the database without committing."""
        self.session.flush()

    def commit(self):
        """Persist all pending changes to the database."""
        self.session.commit()

    def rollback(self):
        """Undo all pending changes since the last commit."""
        self.session.rollback()
