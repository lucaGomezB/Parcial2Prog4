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
        with IdentidadYAccesoUnitOfWork(session) as uow:
            # If setting as principal, unset any existing principal for this user
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
            uow.commit()
            uow.direcciones.refresh(db_direccion)
            return db_direccion

    @staticmethod
    def get_all(session: Session, usuario_id: int, es_admin: bool = False) -> list[DireccionEntrega]:
        with IdentidadYAccesoUnitOfWork(session) as uow:
            if es_admin:
                return uow.direcciones.get_all()
            return uow.direcciones.get_by_usuario(usuario_id)

    @staticmethod
    def get_by_id(session: Session, direccion_id: int, usuario_id: int, es_admin: bool = False) -> Optional[DireccionEntrega]:
        with IdentidadYAccesoUnitOfWork(session) as uow:
            direccion = uow.direcciones.get_by_id(direccion_id)
            if not direccion:
                return None
            # Owner scoping: CLIENT users can only see their own addresses
            if not es_admin and direccion.usuario_id != usuario_id:
                return None
            return direccion

    @staticmethod
    def update(session: Session, direccion_id: int, data: DireccionEntregaUpdate, usuario_id: int, es_admin: bool = False) -> Optional[DireccionEntrega]:
        with IdentidadYAccesoUnitOfWork(session) as uow:
            direccion = uow.direcciones.get_by_id(direccion_id)
            if not direccion:
                return None
            if not es_admin and direccion.usuario_id != usuario_id:
                return None

            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(direccion, key, value)

            uow.direcciones.add(direccion)
            uow.commit()
            uow.direcciones.refresh(direccion)
            return direccion

    @staticmethod
    def set_principal(session: Session, direccion_id: int, usuario_id: int, es_admin: bool = False) -> Optional[DireccionEntrega]:
        with IdentidadYAccesoUnitOfWork(session) as uow:
            direccion = uow.direcciones.get_by_id(direccion_id)
            if not direccion:
                return None
            if not es_admin and direccion.usuario_id != usuario_id:
                return None

            # Idempotent: if already principal, return as-is
            if direccion.es_principal:
                return direccion

            # Unset any existing principal for this user
            existing_principal = uow.direcciones.get_principal(usuario_id)
            if existing_principal:
                existing_principal.es_principal = False
                uow.direcciones.add(existing_principal)

            # Set new principal
            direccion.es_principal = True
            uow.direcciones.add(direccion)
            uow.commit()
            uow.direcciones.refresh(direccion)
            return direccion

    @staticmethod
    def soft_delete(session: Session, direccion_id: int, usuario_id: int, es_admin: bool = False) -> bool:
        with IdentidadYAccesoUnitOfWork(session) as uow:
            direccion = uow.direcciones.get_by_id(direccion_id)
            if not direccion:
                return False
            if not es_admin and direccion.usuario_id != usuario_id:
                return False

            direccion.deleted_at = get_utc_now()
            uow.direcciones.add(direccion)
            uow.commit()
            return True
