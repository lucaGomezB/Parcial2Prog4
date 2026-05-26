from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UsuarioCreate(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    celular: Optional[str] = None
    password: str  # Plain password, will be hashed


class UsuarioRead(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    celular: Optional[str] = None

    class Config:
        from_attributes = True


class RolSimple(BaseModel):
    codigo: str
    nombre: str


class UsuarioReadWithRoles(UsuarioRead):
    roles: List[RolSimple] = []


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[EmailStr] = None
    celular: Optional[str] = None


class UsuarioUpdateWithRoles(UsuarioUpdate):
    roles_codigos: Optional[List[str]] = None
