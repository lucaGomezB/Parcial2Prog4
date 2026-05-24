from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from core.database import get_session 
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import IngredienteService
from .schemas import IngredienteRead, IngredienteCreate, IngredienteUpdate

router = APIRouter(prefix="/ingredientes", tags=["Ingredientes"])

# Endpoints GET - públicos (para guests)
@router.get("/", response_model=List[IngredienteRead])
def read_ingredientes(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    return IngredienteService.get_all(session, skip=skip, limit=limit)

@router.get("/{ingrediente_id}", response_model=IngredienteRead)
def read_ingrediente(ingrediente_id: int, session: Session = Depends(get_session)):
    ingrediente = IngredienteService.get_by_id(session, ingrediente_id)
    if not ingrediente:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    return ingrediente

# Endpoints protegidos - requieren ADMIN o STOCK
@router.post("/", response_model=IngredienteRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def create_ingrediente(data: IngredienteCreate, session: Session = Depends(get_session)):
    return IngredienteService.create(session, data)

@router.patch("/{ingrediente_id}", response_model=IngredienteRead, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def update_ingrediente(ingrediente_id: int, data: IngredienteUpdate, session: Session = Depends(get_session)):
    ingrediente = IngredienteService.update(session, ingrediente_id, data)
    if not ingrediente:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    return ingrediente

@router.delete("/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))])
def delete_ingrediente(ingrediente_id: int, session: Session = Depends(get_session)):
    success = IngredienteService.soft_delete(session, ingrediente_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    return None