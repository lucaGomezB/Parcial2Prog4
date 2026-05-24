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
    return ProductoService.get_all(session, skip=skip, limit=limit)

@router.get("/{producto_id}", response_model=ProductoRead)
def read_producto(producto_id: int, session: Session = Depends(get_session)):
    producto = ProductoService.get_by_id(session, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@router.get("/{producto_id}/ingredientes", response_model=List[ProductoIngredienteRead])
def get_producto_ingredientes(producto_id: int, session: Session = Depends(get_session)):
    return ProductoService.get_ingredientes(session, producto_id)

@router.get("/{producto_id}/categorias", response_model=List[ProductoCategoriaRead])
def get_producto_categorias(producto_id: int, session: Session = Depends(get_session)):
    return ProductoService.get_categorias(session, producto_id)

# Endpoints protegidos - requieren ADMIN o STOCK
@router.post("/", response_model=ProductoRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def create_producto(data: ProductoCreate, session: Session = Depends(get_session)):
    return ProductoService.create(session, data)

@router.patch("/{producto_id}", response_model=ProductoRead, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def update_producto(producto_id: int, data: ProductoUpdate, session: Session = Depends(get_session)):
    producto = ProductoService.update(session, producto_id, data)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def delete_producto(producto_id: int, session: Session = Depends(get_session)):
    if not ProductoService.soft_delete(session, producto_id):
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return None

# --- Relaciones Producto-Ingrediente ---

@router.post("/{producto_id}/ingredientes", response_model=List[ProductoIngredienteRead], dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def add_producto_ingrediente(producto_id: int, data: IngredienteAsignado, session: Session = Depends(get_session)):
    result = ProductoService.add_ingrediente(session, producto_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result

@router.delete("/{producto_id}/ingredientes/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def remove_producto_ingrediente(producto_id: int, ingrediente_id: int, session: Session = Depends(get_session)):
    if not ProductoService.remove_ingrediente(session, producto_id, ingrediente_id):
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    return None

# --- Relaciones Producto-Categoría ---

@router.post("/{producto_id}/categorias", response_model=List[ProductoCategoriaRead], dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def add_producto_categoria(producto_id: int, data: CategoriaAsignada, session: Session = Depends(get_session)):
    result = ProductoService.add_categoria(session, producto_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result

@router.delete("/{producto_id}/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def remove_producto_categoria(producto_id: int, categoria_id: int, session: Session = Depends(get_session)):
    if not ProductoService.remove_categoria(session, producto_id, categoria_id):
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    return None