from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from core.database import get_session
from modules.IdentidadYAcceso.Usuario.models import Usuario
from .config import settings
from .schemas import TokenData

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> Usuario:
    """
    Dependency que extrae el usuario actual desde el token JWT.
    Carga eager los roles para permitir chequeos RBAC posteriores.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        token_data = TokenData(**payload)
    except JWTError:
        raise credentials_exception

    stmt = (
        select(Usuario)
        .where(Usuario.id == token_data.user_id)
        .options(selectinload(Usuario.roles))
    )
    user = session.exec(stmt).first()

    if not user:
        raise credentials_exception

    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> Usuario | None:
    """
    Similar a get_current_user pero retorna None si no hay token.
    Útil para endpoints que pueden ser accedidos por usuarios autenticados o anonimos.
    """
    if not credentials:
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        token_data = TokenData(**payload)

        stmt = (
            select(Usuario)
            .where(Usuario.id == token_data.user_id)
            .options(selectinload(Usuario.roles))
        )
        return session.exec(stmt).first()
    except JWTError:
        return None


def require_roles(allowed_roles: list):
    """
    Fábrica de dependencias para RBAC.
    Uso: dependencies=[Depends(require_roles(["ADMIN", "STOCK"]))]
    
    Verifica que el usuario autenticado tenga al menos UNO de los roles especificados.
    """
    def role_checker(current_user: Usuario = Depends(get_current_user)):
        user_role_codes = [rol.codigo for rol in current_user.roles]
        if not any(role in user_role_codes for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción"
            )
        return current_user
    return role_checker
