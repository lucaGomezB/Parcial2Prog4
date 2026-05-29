from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from datetime import timedelta
from sqlmodel import Session
from core.database import get_session
from .schemas import LoginRequest, TokenResponse, TokenData
from . import service
from .dependencies import get_current_user
from .config import settings
from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.Usuario.schemas import UsuarioCreate
from modules.IdentidadYAcceso.Usuario.service import crear_usuario

router = APIRouter(prefix="/auth", tags=["Autenticación"])

COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400  # días → segundos


def _set_refresh_cookie(response: Response, token: str):
    """Setea el refresh_token como httpOnly cookie."""
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/api/auth/refresh",
    )


def _clear_refresh_cookie(response: Response):
    """Elimina la cookie de refresh_token."""
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth/refresh",
    )


@router.post("/register", response_model=TokenResponse)
def register(
    datos: UsuarioCreate,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    Registra un nuevo usuario con rol CLIENT.
    Endpoint público — no requiere autenticación.
    Auto-login: devuelve access_token + refresh_token en cookie.
    """
    # Forzar rol CLIENT — ignorar cualquier roles_codigos enviado
    datos.roles_codigos = ["CLIENT"]
    user = crear_usuario(session, datos)

    # Auto-login
    token_data = TokenData(user_id=user.id, email=user.email)
    access_token = service.create_access_token(
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
def login(
    credentials: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    Autentica al usuario.
    - access_token en el body (para Authorization header)
    - refresh_token en httpOnly cookie (seguro contra XSS)
    """
    user = service.authenticate_user(session, credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = TokenData(user_id=user.id, email=user.email)
    access_token = service.create_access_token(
        token_data,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = service.create_refresh_token(session, user.id)

    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        # !!!!!! Devolver un mensaje, no el token directamente. !!!!!!!!!
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me")
def get_me(current_user: Usuario = Depends(get_current_user)):
    """
    Devuelve la información del usuario autenticado + sus roles.
    Requiere token JWT válido.
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
    Valida el refresh_token desde la httpOnly cookie y emite un nuevo par.
    Implementa TOKEN ROTATION: el token anterior es revocado.
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

    # Revoke old token (rotation)
    service.revoke_refresh_token(session, raw_token)

    # Get user
    user = session.get(Usuario, stored_token.usuario_id)
    if not user:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    # Issue new pair
    token_data = TokenData(user_id=user.id, email=user.email)
    access_token = service.create_access_token(
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
    """Revoca el refresh token y limpia la cookie."""
    raw_token = request.cookies.get("refresh_token")
    if raw_token:
        service.revoke_refresh_token(session, raw_token)
    _clear_refresh_cookie(response)
    return {"message": "Sesión cerrada correctamente"}
