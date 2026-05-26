from datetime import datetime

from sqlmodel import Session, select

from models.base_repository import BaseRepository
from modules.IdentidadYAcceso.RefreshToken.models import RefreshToken


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: Session):
        super().__init__(session, RefreshToken)

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.utcnow(),
        )
        return self.session.exec(statement).first()

    def get_expired(self) -> list[RefreshToken]:
        statement = select(RefreshToken).where(
            RefreshToken.expires_at < datetime.utcnow()
        )
        return self.session.exec(statement).all()

    def delete(self, token: RefreshToken):
        self.session.delete(token)
