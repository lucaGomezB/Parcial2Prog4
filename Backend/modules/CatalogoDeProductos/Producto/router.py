from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import ProductoService
from .schemas import ProductoRead, ProductoCreate, ProductoUpdate, ProductoIngredienteRead, ProductoCategoriaRead, IngredienteAsignado, CategoriaAsignada

router = APIRouter(prefix="/productos", tags=["Productos"])

# Endpoints GET - públicos (para guests)
@router.get("/", response_model=List[ProductoRead])
def read_productos(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """List all products with pagination. Public endpoint, no auth required."""
    return ProductoService.get_all(session, skip=skip, limit=limit)

@router.get("/{producto_id}", response_model=ProductoRead)
def read_producto(producto_id: int, session: Session = Depends(get_session)):
    """Get a single product by its ID. Public endpoint, no auth required."""
    producto = ProductoService.get_by_id(session, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@router.get("/{producto_id}/ingredientes", response_model=List[ProductoIngredienteRead])
def get_producto_ingredientes(producto_id: int, session: Session = Depends(get_session)):
    """Get all ingredients assigned to a product. Public endpoint, no auth required."""
    return ProductoService.get_ingredientes(session, producto_id)

@router.get("/{producto_id}/categorias", response_model=List[ProductoCategoriaRead])
def get_producto_categorias(producto_id: int, session: Session = Depends(get_session)):
    """Get all categories assigned to a product. Public endpoint, no auth required."""
    return ProductoService.get_categorias(session, producto_id)

# Endpoints protegidos - requieren ADMIN o STOCK
@router.post("/", response_model=ProductoRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def create_producto(data: ProductoCreate, session: Session = Depends(get_session)):
    """Create a new product. Requires ADMIN or STOCK role."""
    return ProductoService.create(session, data)

@router.patch("/{producto_id}", response_model=ProductoRead, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def update_producto(producto_id: int, data: ProductoUpdate, session: Session = Depends(get_session)):
    """Update an existing product by ID. Requires ADMIN or STOCK role."""
    producto = ProductoService.update(session, producto_id, data)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def delete_producto(producto_id: int, session: Session = Depends(get_session)):
    """Soft-delete a product by ID. Requires ADMIN or STOCK role."""
    if not ProductoService.soft_delete(session, producto_id):
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return None

# --- Relaciones Producto-Ingrediente ---

@router.post("/{producto_id}/ingredientes", response_model=List[ProductoIngredienteRead], dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def add_producto_ingrediente(producto_id: int, data: IngredienteAsignado, session: Session = Depends(get_session)):
    """Assign an ingredient to a product. Requires ADMIN or STOCK role."""
    result = ProductoService.add_ingrediente(session, producto_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result

@router.delete("/{producto_id}/ingredientes/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def remove_producto_ingrediente(producto_id: int, ingrediente_id: int, session: Session = Depends(get_session)):
    """Remove an ingredient assignment from a product. Requires ADMIN or STOCK role."""
    if not ProductoService.remove_ingrediente(session, producto_id, ingrediente_id):
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    return None

# --- Relaciones Producto-Categoría ---

@router.post("/{producto_id}/categorias", response_model=List[ProductoCategoriaRead], dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def add_producto_categoria(producto_id: int, data: CategoriaAsignada, session: Session = Depends(get_session)):
    """Assign a category to a product. Requires ADMIN or STOCK role."""
    result = ProductoService.add_categoria(session, producto_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result

@router.delete("/{producto_id}/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def remove_producto_categoria(producto_id: int, categoria_id: int, session: Session = Depends(get_session)):
    """Remove a category assignment from a product. Requires ADMIN or STOCK role."""
    if not ProductoService.remove_categoria(session, producto_id, categoria_id):
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    return None