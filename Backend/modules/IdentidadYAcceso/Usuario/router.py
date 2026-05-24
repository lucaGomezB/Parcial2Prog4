from fastapi import APIRouter, Depends
from sqlmodel import Session
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .schemas import UsuarioCreate, UsuarioRead
from . import service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=UsuarioRead, dependencies=[Depends(require_roles(["ADMIN"]))])
def create_user(datos: UsuarioCreate, session: Session = Depends(get_session)):
    return service.crear_usuario(session, datos)
