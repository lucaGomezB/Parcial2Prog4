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
from core.database import get_session
from core.rate_limit import limiter
from core.security import settings, create_access_token, TokenData
from .schemas import LoginRequest, TokenResponse
from . import service
from .dependencies import get_current_user
from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.Usuario.schemas import UsuarioCreate
from modules.IdentidadYAcceso.Usuario.service import crear_usuario

router = APIRouter(prefix="/auth", tags=["Autenticación"])

COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400  # Convert days to seconds


def _set_refresh_cookie(response: Response, token: str):
    """
    Helper to set the refresh_token as an httpOnly cookie.

    Configuration:
    - httponly=True: prevents JavaScript access (XSS protection).
    - samesite="lax": CSRF protection (cookie sent only for same-site requests).
    - path="/": cookie sent on all requests (including Vite proxy path /api/...).
    - max_age: cookie lifetime in seconds (matches token lifetime).
    """
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def _clear_refresh_cookie(response: Response):
    """
    Helper to remove the refresh_token cookie from the client.

    Must use the same path as _set_refresh_cookie for the deletion
    to take effect. Used during logout and failed refresh validation.
    """
    response.delete_cookie(
        key="refresh_token",
        path="/",
    )


@router.post("/register", response_model=TokenResponse)
def register(
    datos: UsuarioCreate,
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
    datos.roles_codigos = ["CLIENT"]
    user = crear_usuario(session, datos)

    # Auto-login: issue tokens immediately after registration
    token_data = TokenData(user_id=user.id, email=user.email)
    access_token = create_access_token(
        token_data,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = service.create_refresh_token(session, user.id)

    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    POST /auth/login — Authenticate a user with email and password.

    Rate limited to 5 attempts per minute per IP to prevent brute-force
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

    token_data = TokenData(user_id=user.id, email=user.email)
    access_token = create_access_token(
        token_data,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = service.create_refresh_token(session, user.id)

    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
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
    Implements TOKEN ROTATION: the old token is revoked and a new pair is issued.

    Flow:
    1. Read refresh_token from the httpOnly cookie.
    2. Validate it (hash lookup, expiry, revocation).
    3. Revoke the old token (rotation).
    4. Look up the user and issue a new token pair.
    5. Set the new refresh_token in the cookie.
    """
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se encontró refresh token",
        )

    stored_token = service.validate_refresh_token(session, raw_token)
    if not stored_token:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
        )

    # Revoke old token (token rotation — prevents replay attacks)
    service.revoke_refresh_token(session, raw_token)

    # Retrieve the token owner
    user = session.get(Usuario, stored_token.usuario_id)
    if not user:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    # Issue new token pair
    token_data = TokenData(user_id=user.id, email=user.email)
    access_token = create_access_token(
        token_data,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = service.create_refresh_token(session, user.id)

    _set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


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
        service.revoke_refresh_token(session, raw_token)
    _clear_refresh_cookie(response)
    return {"message": "Sesión cerrada correctamente"}
