"""
Authentication router module.

Defines all authentication-related HTTP endpoints under the /auth prefix.

Endpoints:
- POST /auth/register: Public registration with auto-login.
- POST /auth/login: Public login with rate limiting.
- GET /auth/me: Private profile endpoint (requires JWT).
- POST /auth/refresh: Token rotation (requires httpOnly cookie).
- POST /auth/logout: Session termination.

Security features:
- httpOnly cookies for refresh tokens (XSS protection).
- Rate limiting on login (brute-force protection).
- Token rotation on refresh (replay attack prevention).
- Role enforcement (registration always creates CLIENT role).
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from datetime import timedelta
from sqlmodel import Session
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.core.security import settings, create_access_token, TokenData
from .schemas import LoginRequest, TokenResponse
from . import service
from .service import AuthService, _set_refresh_cookie, _clear_refresh_cookie
from .dependencies import get_current_user
from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from app.modules.IdentidadYAcceso.Usuario.schemas import UsuarioCreate
from app.modules.IdentidadYAcceso.Usuario.service import crear_usuario, obtener_usuario

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/15minutes")
def register(
    datos: UsuarioCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    POST /auth/register — Register a new user with auto-login.

    Public endpoint (no authentication required).
    Forces the CLIENT role regardless of any role data sent by the
    client. After registration, automatically logs the user in by
    issuing both access and refresh tokens.
    """
    # Security: force CLIENT role — NEVER trust client-provided roles
    datos.roles_codigos = "CLIENT"
    user = crear_usuario(session, datos)

    # Auto-login: issue tokens immediately after registration
    token_data = TokenData(
        user_id=user.id,
        email=user.email,
        roles=[rol.codigo for rol in user.roles]
    )
    access_token = create_access_token(
        token_data,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = service.create_refresh_token(session, user.id)

    _set_refresh_cookie(request, response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/15minutes")
def login(
    request: Request, #Parametro de Slowapi
    credentials: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    POST /auth/login — Authenticate a user with email and password.

    Rate limited to 5 attempts per 15 minutes per IP to prevent brute-force
    attacks. On success, returns an access_token (for Authorization header)
    and sets a refresh_token in an httpOnly cookie (for session renewal).
    """
    user = service.authenticate_user(session, credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user with roles for JWT payload
    user_with_roles = obtener_usuario(session, user.id)
    if not user_with_roles:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    token_data = TokenData(
        user_id=user.id,
        email=user.email,
        roles=[rol.codigo for rol in user_with_roles.roles]
    )
    access_token = create_access_token(
        token_data,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = service.create_refresh_token(session, user.id)

    _set_refresh_cookie(request, response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me")
def get_me(current_user: Usuario = Depends(get_current_user)):
    """
    GET /auth/me — Get the authenticated user's profile.

    Requires a valid JWT in the Authorization header. Returns user
    information including id, name, email, and role codes. The roles
    are loaded eagerly via selectinload to prevent lazy loading issues.
    """
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "apellido": current_user.apellido,
        "email": current_user.email,
        "celular": current_user.celular,
        "roles": [rol.codigo for rol in current_user.roles],
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    POST /auth/refresh — Renew access token using refresh token rotation.

    Reads the refresh_token from the httpOnly cookie (not from the request body).
    Implements TOKEN ROTATION with row-level locking (SELECT ... FOR UPDATE):
    the old token is atomically validated and revoked in a single operation,
    preventing the TOCTOU race between concurrent refresh calls.

    Flow:
    1. Read refresh_token from the httpOnly cookie.
    2. Hash it and call get_by_hash_for_update (locks the row).
    3. If found: revoke directly (we already hold the lock).
    4. If not found: check for replay attack pattern.
    5. Look up the user and issue a new token pair.
    6. Set the new refresh_token in the cookie.
    """
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se encontró refresh token",
        )

    return AuthService.refresh_token(session, raw_token, request, response)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    POST /auth/logout — Terminate the current session.

    Revokes the refresh token (soft-delete via revoked_at) and clears
    the httpOnly cookie. The access token remains valid until it expires
    naturally (short-lived, so no active revocation needed).
    """
    raw_token = request.cookies.get("refresh_token")
    if raw_token:
        revoked = service.revoke_refresh_token(session, raw_token)
        if not revoked:
            import logging
            logging.getLogger(__name__).warning("Refresh token revocation returned False during logout")
    _clear_refresh_cookie(response)
    return {"message": "Sesión cerrada correctamente"}
