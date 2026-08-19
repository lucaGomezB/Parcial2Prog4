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
from app.core.base_uow import BaseUnitOfWork

from .Auth.repository import RefreshTokenRepository
from .DireccionEntrega.repository import DireccionEntregaRepository
from .Rol.repository import RolRepository
from .Usuario.repository import UsuarioRepository


class IdentidadYAccesoUnitOfWork(BaseUnitOfWork):
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
        super().__init__(session)
        self.direcciones = DireccionEntregaRepository(session)
        self.usuarios = UsuarioRepository(session)
        self.roles = RolRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
