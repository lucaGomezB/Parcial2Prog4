"""
Pydantic schemas for Usuario (User) endpoints.

Defines request and response models for user creation, reading,
and updating. Separates input schemas (what the client sends) from
output schemas (what the API returns) for security and clarity.

Key schemas:
- UsuarioCreate: Input for POST /usuarios and POST /auth/register.
- UsuarioRead: Safe output (no password_hash) for GET endpoints.
- UsuarioReadWithRoles: Extended output including role assignments.
- UsuarioUpdate/UsuarioUpdateWithRoles: Partial update input models.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UsuarioCreate(BaseModel):
    """
    Request schema for creating a new user.

    Note: 'password' is plain text input (will be hashed before storage).
    The 'roles_codigos' field is optional — if omitted, the user is
    created without roles. When used via POST /auth/register, this
    field is overwritten to force the CLIENT role.
    """
    nombre: str
    apellido: str
    email: EmailStr  # Validates email format automatically
    celular: Optional[str] = None
    password: str  # Plain password — will be bcrypt-hashed by the service
    roles_codigos: Optional[List[str]] = None


class UsuarioRead(BaseModel):
    """
    Response schema for user data (safe output).

    Excludes password_hash entirely — hashed passwords are never
    returned to the client. Uses from_attributes=True for ORM
    model conversion.
    """
    id: int
    nombre: str
    apellido: str
    email: str
    celular: Optional[str] = None

    class Config:
        from_attributes = True


class RolSimple(BaseModel):
    """
    Simplified role representation within user responses.

    Includes only the role's semantic code and display name,
    not internal details or timestamps.
    """
    codigo: str
    nombre: str


class UsuarioReadWithRoles(UsuarioRead):
    """
    Extended user response including role assignments.

    Inherits all fields from UsuarioRead (id, nombre, etc.) and adds
    a list of RolSimple objects representing the user's roles.
    """
    roles: List[RolSimple] = []


class UsuarioUpdate(BaseModel):
    """
    Request schema for partial user update (PATCH).

    All fields are optional — only the fields sent by the client
    will be updated. Uses exclude_unset=True in the service layer
    to avoid overwriting existing values with None.
    """
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[EmailStr] = None
    celular: Optional[str] = None


class UsuarioUpdateWithRoles(UsuarioUpdate):
    """
    Extended update schema including role reassignment.

    If roles_codigos is sent (even as an empty list), the user's
    roles are replaced entirely. If roles_codigos is omitted (None),
    existing roles remain unchanged.
    """
    roles_codigos: Optional[List[str]] = None
