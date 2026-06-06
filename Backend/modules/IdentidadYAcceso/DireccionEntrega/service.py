"""
DireccionEntrega (Delivery Address) service module.

Implements business logic for delivery address management with
owner-scoping: regular users can only access their own addresses,
while ADMIN users have cross-user access.

Key behavior:
- Only one address per user can be marked as 'principal' at a time.
- Setting a new principal atomically unsets the previous one.
- All operations are soft-delete aware.
"""

from typing import Optional
from fastapi import HTTPException, status
from sqlmodel import Session

from .models import DireccionEntrega
from .schemas import DireccionEntregaCreate, DireccionEntregaUpdate
from models.base import get_utc_now
from ..uow import IdentidadYAccesoUnitOfWork


class DireccionEntregaService:

    @staticmethod
    def create(session: Session, data: DireccionEntregaCreate, usuario_id: int) -> DireccionEntrega:
        """
        Create a new delivery address for the given user.

        If setting as principal, any existing principal address for
        this user is automatically unset first (atomic operation within
        the same transaction).
        """
        with IdentidadYAccesoUnitOfWork(session) as uow:
            # Unset existing principal if this new address is marked as principal
            if data.es_principal:
                existing_principal = uow.direcciones.get_principal(usuario_id)
                if existing_principal:
                    existing_principal.es_principal = False
                    uow.direcciones.add(existing_principal)

            db_direccion = DireccionEntrega(
                usuario_id=usuario_id,
                alias=data.alias,
                linea1=data.linea1,
                linea2=data.linea2,
                ciudad=data.ciudad,
                provincia=data.provincia,
                codigo_postal=data.codigo_postal,
                latitud=data.latitud,
                longitud=data.longitud,
                es_principal=data.es_principal,
            )
            uow.direcciones.add(db_direccion)
            uow.flush()
            uow.direcciones.refresh(db_direccion)
            return db_direccion

    @staticmethod
    def get_all(session: Session, usuario_id: int, es_admin: bool = False) -> list[DireccionEntrega]:
        """
        Get all addresses for a user.

        ADMIN users can see all addresses across all users.
        Regular users only see their own addresses.
        """
        with IdentidadYAccesoUnitOfWork(session) as uow:
            if es_admin:
                return uow.direcciones.get_all()
            return uow.direcciones.get_by_usuario(usuario_id)

    @staticmethod
    def get_by_id(
        session: Session, direccion_id: int, usuario_id: int, es_admin: bool = False
    ) -> Optional[DireccionEntrega]:
        """
        Get a specific address by ID with owner scoping.

        Regular users cannot access addresses belonging to other users.
        """
        with IdentidadYAccesoUnitOfWork(session) as uow:
            direccion = uow.direcciones.get_by_id(direccion_id)
            if not direccion:
                return None
            # Owner scoping: CLIENT users can only see their own addresses
            if not es_admin and direccion.usuario_id != usuario_id:
                return None
            return direccion

    @staticmethod
    def update(
        session: Session, direccion_id: int, data: DireccionEntregaUpdate,
        usuario_id: int, es_admin: bool = False
    ) -> Optional[DireccionEntrega]:
        """
        Partially update a delivery address.

        Supports changing es_principal: setting True auto-unsets any existing
        principal for the user; setting False removes principal from this address.
        Regular users are scoped to their own addresses.
        """
        with IdentidadYAccesoUnitOfWork(session) as uow:
            direccion = uow.direcciones.get_by_id(direccion_id)
            if not direccion:
                return None
            if not es_admin and direccion.usuario_id != usuario_id:
                return None

            values = data.model_dump(exclude_unset=True)

            # Handle es_principal changes atomically
            if 'es_principal' in values:
                if values['es_principal']:
                    # Setting as principal: unset any existing principal first
                    existing_principal = uow.direcciones.get_principal(usuario_id)
                    if existing_principal and existing_principal.id != direccion_id:
                        existing_principal.es_principal = False
                        uow.direcciones.add(existing_principal)
                    direccion.es_principal = True
                else:
                    # Unsetting principal on this address
                    direccion.es_principal = False
                del values['es_principal']

            for key, value in values.items():
                setattr(direccion, key, value)

            uow.direcciones.add(direccion)
            return direccion

    @staticmethod
    def set_principal(
        session: Session, direccion_id: int, usuario_id: int, es_admin: bool = False
    ) -> Optional[DireccionEntrega]:
        """
        Set a specific address as the user's principal (default) address.

        Atomically unsets any existing principal for the same user.
        Idempotent: if the address is already principal, returns unchanged.
        """
        with IdentidadYAccesoUnitOfWork(session) as uow:
            direccion = uow.direcciones.get_by_id(direccion_id)
            if not direccion:
                return None
            if not es_admin and direccion.usuario_id != usuario_id:
                return None

            # Idempotent: already principal, nothing to do
            if direccion.es_principal:
                return direccion

            # Unset any existing principal for this user
            existing_principal = uow.direcciones.get_principal(usuario_id)
            if existing_principal:
                existing_principal.es_principal = False
                uow.direcciones.add(existing_principal)

            # Set the new principal
            direccion.es_principal = True
            uow.direcciones.add(direccion)
            return direccion

    @staticmethod
    def soft_delete(
        session: Session, direccion_id: int, usuario_id: int, es_admin: bool = False
    ) -> bool:
        """
        Soft-delete a delivery address (sets deleted_at timestamp).

        Regular users can only delete their own addresses.
        Returns True if deleted, False if not found.
        """
        with IdentidadYAccesoUnitOfWork(session) as uow:
            direccion = uow.direcciones.get_by_id(direccion_id)
            if not direccion:
                return False
            if not es_admin and direccion.usuario_id != usuario_id:
                return False

            direccion.deleted_at = get_utc_now()
            uow.direcciones.add(direccion)
            return True
