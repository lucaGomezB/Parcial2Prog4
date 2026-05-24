from pydantic import BaseModel, EmailStr
from typing import Optional


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
