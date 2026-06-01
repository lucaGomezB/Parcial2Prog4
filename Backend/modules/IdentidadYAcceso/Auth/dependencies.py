"""
FastAPI dependency injection module for authentication and authorization.

Provides three key dependencies:

1. get_current_user: Extracts and validates the JWT from the Authorization
   header, loads the corresponding user from the database with roles.
2. get_current_user_optional: Same as above but returns None instead of
   raising 401 for unauthenticated requests (for mixed-access endpoints).
3. require_roles: Dependency factory for Role-Based Access Control (RBAC).
   Returns a dependency that checks if the authenticated user has at least
   one of the specified role codes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from core.database import get_session
from modules.IdentidadYAcceso.Usuario.models import Usuario
from .config import settings
from .schemas import TokenData

# HTTPBearer extracts the token from the "Authorization: Bearer <token>" header.
# auto_error=False means we handle missing tokens manually (for optional auth).
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> Usuario:
    """
    Extract and validate the authenticated user from the JWT.

    Decodes the Bearer token, extracts user_id from payload, loads
    the user from DB with eager-loaded roles. Raises 401 if the token
    is missing, invalid, expired, or the user does not exist.

    Uses selectinload(Usuario.roles) to avoid N+1 queries when accessing
    the user's role list later in the request lifecycle.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        # Decode and verify the JWT signature using SECRET_KEY
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        token_data = TokenData(**payload)
    except jwt.InvalidTokenError:
        raise credentials_exception

    # Load user with roles (eager loading to prevent lazy loading issues)
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
    Like get_current_user but tolerates missing/invalid tokens.

    Returns the user if a valid token is present, or None for anonymous
    requests. Useful for mixed-access endpoints that show different
    content depending on authentication state.
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
    except jwt.InvalidTokenError:
        return None


def require_roles(allowed_roles: list):
    """
    Dependency factory for Role-Based Access Control (RBAC).

    Usage in endpoint definitions:
        @router.get("/admin-only", dependencies=[Depends(require_roles(["ADMIN"]))])

    The returned role_checker function is used as a FastAPI dependency.
    It first runs get_current_user (nested dependency), then checks if
    the authenticated user has at least ONE of the allowed_roles.
    Raises 403 Forbidden if the user lacks the required role.

    Note: 403 (Forbidden) differs from 401 (Unauthorized).
    401 = not authenticated, 403 = authenticated but insufficient permissions.
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
