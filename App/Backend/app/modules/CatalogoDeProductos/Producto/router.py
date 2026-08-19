"""
Producto router — API endpoints for product management.

Endpoints are split into:
    - Public GET endpoints (no auth required) for browsing the catalog
    - Protected POST/PATCH/DELETE endpoints requiring ADMIN or STOCK roles

Prefix: /productos
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session
from typing import List, Optional
from app.core.database import get_session
from app.core.paginated_response import PaginatedResponse
from app.core.dependencies import AdminOrStock
from app.core.routing import get_or_404
from app.modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import ProductoService
from .schemas import ProductoRead, ProductoCreate, ProductoUpdate, ProductoIngredienteRead, ProductoCategoriaRead, IngredienteAsignado, CategoriaAsignada, IngredienteStockDetail, ProductoIngredientesCompartidos

router = APIRouter(prefix="/productos", tags=["Productos"])

# --- Public GET endpoints (no auth required) ---

@router.get("/", response_model=PaginatedResponse[ProductoRead])
def read_productos(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    categoria_id: Optional[list[int]] = Query(None),
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """GET /productos — List all products with pagination, optional search, category filter, and sort. Public endpoint, no auth required."""
    return ProductoService.get_all(
        session, skip=skip, limit=limit, search=search, categoria_id=categoria_id,
        sort_by=sort_by, sort_order=sort_order,
    )

@router.get("/ingredientes-compartidos", response_model=List[ProductoIngredientesCompartidos])
def get_ingredientes_compartidos(session: Session = Depends(get_session)):
    """GET /productos/ingredientes-compartidos — Map of products to ingredients shared with other products."""
    return ProductoService.get_ingredientes_compartidos(session)

@router.get("/{producto_id}", response_model=ProductoRead)
def read_producto(producto_id: int, session: Session = Depends(get_session)):
    """GET /productos/{id} — Get a single product by its ID. Public endpoint, no auth required."""
    producto = ProductoService.get_by_id(session, producto_id)
    return get_or_404(producto, "Producto no encontrado")

@router.get("/{producto_id}/ingredientes", response_model=List[ProductoIngredienteRead])
def get_producto_ingredientes(producto_id: int, session: Session = Depends(get_session)):
    """GET /productos/{id}/ingredientes — Get all ingredients assigned to a product. Public endpoint."""
    return ProductoService.get_ingredientes(session, producto_id)

@router.get("/{producto_id}/ingredientes-stock", response_model=List[IngredienteStockDetail])
def get_producto_ingredientes_stock(producto_id: int, session: Session = Depends(get_session)):
    """GET /productos/{id}/ingredientes-stock — Per-ingredient stock breakdown for derived stock.
    Shows which ingredients limit production and the deficit to produce at least 1 unit."""
    result = ProductoService.get_ingredientes_stock_detail(session, producto_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result

@router.get("/{producto_id}/categorias", response_model=List[ProductoCategoriaRead])
def get_producto_categorias(producto_id: int, session: Session = Depends(get_session)):
    """GET /productos/{id}/categorias — Get all categories assigned to a product. Public endpoint."""
    return ProductoService.get_categorias(session, producto_id)

# --- Protected endpoints — require ADMIN or STOCK role ---

@router.post("/", response_model=ProductoRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(AdminOrStock))])
def create_producto(data: ProductoCreate, session: Session = Depends(get_session)):
    """POST /productos — Create a new product. Requires ADMIN or STOCK role."""
    return ProductoService.create(session, data)

@router.patch("/{producto_id}", response_model=ProductoRead, dependencies=[Depends(require_roles(AdminOrStock))])
def update_producto(producto_id: int, data: ProductoUpdate, session: Session = Depends(get_session)):
    """PATCH /productos/{id} — Update an existing product by ID. Requires ADMIN or STOCK role."""
    producto = ProductoService.update(session, producto_id, data)
    return get_or_404(producto, "Producto no encontrado")

@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(AdminOrStock))])
def delete_producto(producto_id: int, session: Session = Depends(get_session)):
    """DELETE /productos/{id} — Soft-delete a product by ID. Requires ADMIN or STOCK role."""
    get_or_404(ProductoService.soft_delete(session, producto_id), "Producto no encontrado")
    return None

# --- Product-Ingredient relationship endpoints ---

@router.post("/{producto_id}/ingredientes", response_model=List[ProductoIngredienteRead], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(AdminOrStock))])
def add_producto_ingrediente(producto_id: int, data: IngredienteAsignado, session: Session = Depends(get_session)):
    """POST /productos/{id}/ingredientes — Assign an ingredient to a product. Requires ADMIN or STOCK role."""
    result = ProductoService.add_ingrediente(session, producto_id, data)
    return get_or_404(result, "Producto no encontrado")

@router.delete("/{producto_id}/ingredientes/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(AdminOrStock))])
def remove_producto_ingrediente(producto_id: int, ingrediente_id: int, session: Session = Depends(get_session)):
    """DELETE /productos/{id}/ingredientes/{ingrediente_id} — Remove an ingredient assignment. Requires ADMIN or STOCK role."""
    get_or_404(ProductoService.remove_ingrediente(session, producto_id, ingrediente_id), "Relación no encontrada")
    return None

@router.patch("/{producto_id}/ingredientes/{ingrediente_id}", response_model=List[ProductoIngredienteRead], dependencies=[Depends(require_roles(AdminOrStock))])
def update_producto_ingrediente_cantidad(producto_id: int, ingrediente_id: int, data: IngredienteAsignado, session: Session = Depends(get_session)):
    """PATCH /productos/{id}/ingredientes/{ingrediente_id} — Update ingredient association fields (cantidad, removible, principal, unidad). Requires ADMIN or STOCK role."""
    result = ProductoService.update_ingrediente(session, producto_id, ingrediente_id, data)
    return get_or_404(result, "Relación no encontrada")

# --- Product-Category relationship endpoints ---

@router.post("/{producto_id}/categorias", response_model=List[ProductoCategoriaRead], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(AdminOrStock))])
def add_producto_categoria(producto_id: int, data: CategoriaAsignada, session: Session = Depends(get_session)):
    """POST /productos/{id}/categorias — Assign a category to a product. Requires ADMIN or STOCK role."""
    result = ProductoService.add_categoria(session, producto_id, data)
    return get_or_404(result, "Producto no encontrado")

@router.delete("/{producto_id}/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(AdminOrStock))])
def remove_producto_categoria(producto_id: int, categoria_id: int, session: Session = Depends(get_session)):
    """DELETE /productos/{id}/categorias/{categoria_id} — Remove a category assignment. Requires ADMIN or STOCK role."""
    get_or_404(ProductoService.remove_categoria(session, producto_id, categoria_id), "Relación no encontrada")
    return None
