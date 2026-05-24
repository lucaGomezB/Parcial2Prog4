import bcrypt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from sqlmodel import Session, select
from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
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

    db_token = RefreshToken(
        usuario_id=usuario_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=now,
    )
    session.add(db_token)
    session.commit()
    session.refresh(db_token)

    return raw_token


def validate_refresh_token(session: Session, raw_token: str) -> Optional[RefreshToken]:
    """Valida un refresh token: busca por hash, que no esté revocado y no haya expirado."""
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = get_utc_now()

    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at.is_(None),
        RefreshToken.expires_at > now,
    )
    return session.exec(stmt).first()


def revoke_refresh_token(session: Session, raw_token: str) -> bool:
    """Revoca un refresh token (setea revoked_at). Retorna True si se revocó, False si no se encontró."""
    stored = validate_refresh_token(session, raw_token)
    if not stored:
        return False

    stored.revoked_at = get_utc_now()
    session.add(stored)
    session.commit()
    return True


def cleanup_expired_tokens(session: Session):
    """Elimina todos los refresh tokens expirados de la BD."""
    now = get_utc_now()
    stmt = select(RefreshToken).where(RefreshToken.expires_at < now)
    expired = session.exec(stmt).all()
    for token in expired:
        session.delete(token)
    session.commit()
