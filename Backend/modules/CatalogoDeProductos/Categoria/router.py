# router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import CategoriaService
from .schemas import CategoriaRead, CategoriaCreate, CategoriaTree, CategoriaUpdate

router = APIRouter(prefix="/categorias", tags=["Categorías"])

@router.get("/tree", response_model=list[CategoriaTree]) #Obtener las categorias que no tienen padre y no están borradas
def get_tree(session: Session = Depends(get_session)):
    return CategoriaService.get_root_categories(session)

@router.get("/", response_model=list[CategoriaRead]) # Obtener todas las categorias
def read_categorias(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    return CategoriaService.get_all(session, skip=skip, limit=limit)

@router.get("/{categoria_id}", response_model=CategoriaRead)
def read_categoria(categoria_id: int, session: Session = Depends(get_session)):
    categoria = CategoriaService.get_by_id(session, categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="No encontrada")
    return categoria

# Endpoints protegidos - requieren ADMIN o STOCK
@router.post("/", response_model=CategoriaCreate, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def create_categoria(data: CategoriaCreate, session: Session = Depends(get_session)):
    return CategoriaService.create(session, data)

@router.patch("/{categoria_id}", response_model=CategoriaUpdate, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def update_categoria(categoria_id: int, data: CategoriaUpdate, session: Session = Depends(get_session)):
    categoria = CategoriaService.update(session, categoria_id, data)
    if not categoria:
        raise HTTPException(status_code=404, detail="No encontrada")
    return categoria

@router.delete("/{categoria_id}", dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def delete_categoria(categoria_id: int, session: Session = Depends(get_session)):
    obj = CategoriaService.soft_delete(session, categoria_id)
    if not obj:
        raise HTTPException(status_code=404, detail="No encontrada")
    return {"detail": "Eliminado lógicamente"}