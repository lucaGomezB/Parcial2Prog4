import bcrypt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
import jwt
from sqlmodel import Session, select
from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
from ..uow import IdentidadYAccesoUnitOfWork
from models.base import get_utc_now
from .config import settings
from .schemas import TokenData


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica la contraseña contra el hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_access_token(data: TokenData, expires_delta: timedelta | None = None) -> str:
    """Crea un token JWT con los datos del usuario."""
    to_encode = data.model_dump()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def authenticate_user(session: Session, email: str, password: str) -> Usuario | None:
    """Autentica un usuario con email y password."""
    stmt = select(Usuario).where(Usuario.email == email)
    user = session.exec(stmt).first()

    if not user:
        return None

    if verify_password(password, user.password_hash):
        return user

    return None


def create_refresh_token(session: Session, usuario_id: int) -> str:
    """Genera un refresh token, almacena su hash en DB y devuelve el raw token."""
    token_bytes = secrets.token_bytes(32)
    raw_token = token_bytes.hex()
    token_hash = hashlib.sha256(token_bytes).hexdigest()

    now = get_utc_now()
    expires_at = now + timedelta(days=7)

    with IdentidadYAccesoUnitOfWork(session) as uow:
        db_token = RefreshToken(
            usuario_id=usuario_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=now,
        )
        uow.refresh_tokens.add(db_token)
        # No necesita refresh(): el UoW commitea al salir del with,
        # y solo retornamos raw_token, no db_token.

    return raw_token


def validate_refresh_token(session: Session, raw_token: str) -> Optional[RefreshToken]:
    """Valida un refresh token: busca por hash, que no esté revocado y no haya expirado."""
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with IdentidadYAccesoUnitOfWork(session) as uow:
        return uow.refresh_tokens.get_by_hash(token_hash)


def revoke_refresh_token(session: Session, raw_token: str) -> bool:
    """Revoca un refresh token (setea revoked_at). Retorna True si se revocó, False si no se encontró."""
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with IdentidadYAccesoUnitOfWork(session) as uow:
        stored = uow.refresh_tokens.get_by_hash(token_hash)
        if not stored:
            return False
        stored.revoked_at = get_utc_now()
        uow.refresh_tokens.add(stored)
        return True


def cleanup_expired_tokens(session: Session):
    """Elimina todos los refresh tokens expirados de la BD."""
    with IdentidadYAccesoUnitOfWork(session) as uow:
        expired = uow.refresh_tokens.get_expired()
        for token in expired:
            uow.refresh_tokens.delete(token)
