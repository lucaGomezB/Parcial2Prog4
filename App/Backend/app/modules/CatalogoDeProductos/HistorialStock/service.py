"""
HistorialStock service — creates audit entries for stock mutations.

Provides a utility method registrar_cambio() that is callable from any
service that modifies product or ingredient stock. The caller supplies
a Unit of Work instance; the method adds the HistorialStock row via uow.add().
The caller is responsible for the transaction boundary (commit/rollback).
"""
from typing import Optional
from .models import HistorialStock


class HistorialStockService:
    """Creates append-only stock audit entries."""

    @staticmethod
    def registrar_cambio(
        uow,
        entidad_tipo: str,
        entidad_id: int,
        stock_anterior: int,
        stock_nuevo: int,
        motivo: str,
        usuario_id: Optional[int] = None,
    ) -> HistorialStock:
        """Create and add a HistorialStock row using the UoW's add().

        The row is added to the UoW session but NOT committed.
        The caller's UoW __exit__ handles the commit.
        """
        historial = HistorialStock(
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            stock_anterior=stock_anterior,
            stock_nuevo=stock_nuevo,
            motivo=motivo,
            usuario_id=usuario_id,
        )
        uow.add(historial)
        return historial
