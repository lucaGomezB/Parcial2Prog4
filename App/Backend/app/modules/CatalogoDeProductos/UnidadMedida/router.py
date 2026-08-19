"""
UnidadMedida router — API endpoints for measurement unit management.

Endpoints:
    GET    /          — list all (ADMIN, STOCK, PEDIDOS), optional ?tipo= query
    GET    /{id}      — get one (ADMIN, STOCK, PEDIDOS)
    POST   /          — create (ADMIN only)
    PUT    /{id}      — update (ADMIN only)
    DELETE /{id}      — delete (ADMIN only), FK-protected
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import Optional

from app.core.database import get_session
from app.core.dependencies import AdminOnly, AdminOrStockOrPedidos
from app.core.routing import get_or_404
from app.modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import UnidadMedidaService
from .schemas import UnidadMedidaCreate, UnidadMedidaUpdate, UnidadMedidaRead

router = APIRouter(prefix="/unidades-medida", tags=["Unidades de Medida"])


# --- Read endpoints (ADMIN, STOCK, PEDIDOS) ---

@router.get("/", response_model=list[UnidadMedidaRead],
            dependencies=[Depends(require_roles(AdminOrStockOrPedidos))])
def read_unidades_medida(
    tipo: Optional[str] = Query(None, description="Filter by tipo: masa, volumen, unidad, area"),
    session: Session = Depends(get_session),
):
    """GET /unidades-medida — List all measurement units, optional tipo filter."""
    return UnidadMedidaService.get_all(session, tipo_filter=tipo)


@router.get("/{unidad_id}", response_model=UnidadMedidaRead,
            dependencies=[Depends(require_roles(AdminOrStockOrPedidos))])
def read_unidad_medida(unidad_id: int, session: Session = Depends(get_session)):
    """GET /unidades-medida/{id} — Get a single measurement unit by ID."""
    unit = UnidadMedidaService.get_by_id(session, unidad_id)
    return get_or_404(unit, "Unidad de medida no encontrada")


# --- Write endpoints (ADMIN only) ---

@router.post("/", response_model=UnidadMedidaRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(AdminOnly))])
def create_unidad_medida(data: UnidadMedidaCreate, session: Session = Depends(get_session)):
    """POST /unidades-medida — Create a new measurement unit. ADMIN only."""
    return UnidadMedidaService.create(session, data)


@router.put("/{unidad_id}", response_model=UnidadMedidaRead,
            dependencies=[Depends(require_roles(AdminOnly))])
def update_unidad_medida(unidad_id: int, data: UnidadMedidaUpdate,
                         session: Session = Depends(get_session)):
    """PUT /unidades-medida/{id} — Update a measurement unit. ADMIN only."""
    unit = UnidadMedidaService.update(session, unidad_id, data)
    return get_or_404(unit, "Unidad de medida no encontrada")


@router.delete("/{unidad_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(AdminOnly))])
def delete_unidad_medida(unidad_id: int, session: Session = Depends(get_session)):
    """DELETE /unidades-medida/{id} — Delete a measurement unit. ADMIN only.

    Fails with 400 if the unit is referenced by any Producto or ProductoIngrediente.
    """
    from sqlalchemy.exc import IntegrityError

    try:
        deleted = UnidadMedidaService.delete(session, unidad_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    get_or_404(deleted, "Unidad de medida no encontrada")
    return None
