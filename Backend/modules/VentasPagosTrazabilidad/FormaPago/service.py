"""
FormaPago service — business logic for payment method catalog.

Simple CRUD — no complex business logic. The 'incluir_deshabilitadas'
parameter controls whether disabled payment methods are visible.
"""
from sqlmodel import Session
from typing import List, Optional
from .models import FormaPago
from .schemas import FormaPagoCreate, FormaPagoUpdate
from ..uow import VentasPagosTrazabilidadUnitOfWork


class FormaPagoService:
    """Business logic for payment method catalog CRUD."""

    @staticmethod
    def get_all(session: Session, incluir_deshabilitadas: bool = False) -> List[FormaPago]:
        """List all payment methods. Optionally include disabled ones."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.formas_pago.get_all(only_habilitados=not incluir_deshabilitadas)

    @staticmethod
    def get_by_codigo(session: Session, codigo: str) -> Optional[FormaPago]:
        """Fetch a single payment method by its code (e.g. 'EFECTIVO', 'MP')."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.formas_pago.get_by_codigo(codigo)

    @staticmethod
    def create(session: Session, data: FormaPagoCreate) -> FormaPago:
        """Create a new payment method. Requires ADMIN role."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_obj = FormaPago(**data.model_dump())
            uow.formas_pago.add(db_obj)
            return db_obj

    @staticmethod
    def update(session: Session, codigo: str, data: FormaPagoUpdate) -> Optional[FormaPago]:
        """Update an existing payment method. Only provided fields are modified."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_obj = uow.formas_pago.get_by_codigo(codigo)
            if not db_obj:
                return None
            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(db_obj, key, value)
            uow.formas_pago.add(db_obj)
            return db_obj

    @staticmethod
    def delete(session: Session, codigo: str) -> bool:
        """Delete a payment method.

        Cannot delete if referenced by existing orders (FK constraint).
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_obj = uow.formas_pago.get_by_codigo(codigo)
            if not db_obj:
                return False
            uow.session.delete(db_obj)
            return True
