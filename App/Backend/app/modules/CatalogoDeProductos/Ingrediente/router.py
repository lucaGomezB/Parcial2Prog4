"""
Ingrediente router — API endpoints for ingredient management.

Endpoints:
    GET /            — List ingredients (public)
    GET /{id}        — Single ingredient (public)
    POST /           — Create ingredient (ADMIN or STOCK)
    PATCH /{id}      — Update ingredient (ADMIN or STOCK)
    PATCH /{id}/precio — Update price (triggers product repricing)
    PATCH /{id}/stock  — Update stock only
    DELETE /{id}     — Soft-delete (ADMIN or STOCK)

Prefix: /ingredientes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List, Optional
from app.core.database import get_session
from app.core.paginated_response import PaginatedResponse
from app.core.dependencies import AdminOrStock
from app.core.routing import get_or_404
from app.modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import IngredienteService
from .schemas import IngredienteRead, IngredienteCreate, IngredienteUpdate, IngredientePrecioUpdate, IngredienteStockUpdate, AfectadoProductoRead

router = APIRouter(prefix="/ingredientes", tags=["Ingredientes"])

# --- Public GET endpoints ---

@router.get("/", response_model=PaginatedResponse[IngredienteRead])
def read_ingredientes(skip: int = 0, limit: int = 100, search: Optional[str] = None, session: Session = Depends(get_session)):
    """GET /ingredientes — List all ingredients with pagination. Public endpoint."""
    return IngredienteService.get_all(session, skip=skip, limit=limit, search=search)

@router.get("/{ingrediente_id}", response_model=IngredienteRead)
def read_ingrediente(ingrediente_id: int, session: Session = Depends(get_session)):
    """GET /ingredientes/{id} — Get a single ingredient by its ID. Public endpoint."""
    ingrediente = IngredienteService.get_by_id(session, ingrediente_id)
    return get_or_404(ingrediente, "Ingrediente no encontrado")

# --- Protected endpoints — ADMIN or STOCK ---

@router.post("/", response_model=IngredienteRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(AdminOrStock))])
def create_ingrediente(data: IngredienteCreate, session: Session = Depends(get_session)):
    """POST /ingredientes — Create a new ingredient. Requires ADMIN or STOCK role."""
    return IngredienteService.create(session, data)

@router.patch("/{ingrediente_id}", response_model=IngredienteRead, dependencies=[Depends(require_roles(AdminOrStock))])
def update_ingrediente(ingrediente_id: int, data: IngredienteUpdate, session: Session = Depends(get_session)):
    """PATCH /ingredientes/{id} — Update an existing ingredient by ID. Requires ADMIN or STOCK role."""
    ingrediente = IngredienteService.update(session, ingrediente_id, data)
    return get_or_404(ingrediente, "Ingrediente no encontrado")

@router.patch("/{ingrediente_id}/precio", response_model=IngredienteRead, dependencies=[Depends(require_roles(AdminOrStock))])
def actualizar_precio_ingrediente(
    ingrediente_id: int,
    data: IngredientePrecioUpdate,
    session: Session = Depends(get_session),
):
    """PATCH /ingredientes/{id}/precio — Update the price of an ingredient.
    Triggers recalculation of all product prices that use this ingredient. Requires ADMIN or STOCK role."""
    return IngredienteService.actualizar_precio(session, ingrediente_id, data.precio)

@router.patch("/{ingrediente_id}/stock", response_model=IngredienteRead, dependencies=[Depends(require_roles(AdminOrStock))])
def actualizar_stock_ingrediente(
    ingrediente_id: int,
    data: IngredienteStockUpdate,
    session: Session = Depends(get_session),
):
    """PATCH /ingredientes/{id}/stock — Update the stock of an ingredient.
    Does NOT affect product prices. Requires ADMIN or STOCK role."""
    return IngredienteService.actualizar_stock(session, ingrediente_id, data.stock)

@router.get("/{ingrediente_id}/productos", response_model=List[AfectadoProductoRead])
def get_productos_afectados(ingrediente_id: int, session: Session = Depends(get_session)):
    """GET /ingredientes/{id}/productos — Get products affected by this ingredient with derived stock values. Public endpoint."""
    from app.modules.CatalogoDeProductos.uow import CatalogoDeProductosUnitOfWork
    uow = CatalogoDeProductosUnitOfWork(session)
    producto_ids = uow.productos.get_productos_afectados_por_ingrediente(ingrediente_id)
    if not producto_ids:
        return []
    productos = uow.productos.get_by_ids(producto_ids)
    stock_map = uow.productos.compute_derived_stock_batch(producto_ids)
    return [
        AfectadoProductoRead(
            id=p.id, nombre=p.nombre,
            stock_derivado=stock_map.get(p.id, 0),
            es_producto_terminado=p.es_producto_terminado,
            stock_manual=p.stock_manual,
        )
        for p in productos
    ]


@router.delete("/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(AdminOrStock))])
def delete_ingrediente(ingrediente_id: int, session: Session = Depends(get_session)):
    """DELETE /ingredientes/{id} — Soft-delete an ingredient by ID. Requires ADMIN or STOCK role."""
    get_or_404(IngredienteService.soft_delete(session, ingrediente_id), "Ingrediente no encontrado")
    return None
