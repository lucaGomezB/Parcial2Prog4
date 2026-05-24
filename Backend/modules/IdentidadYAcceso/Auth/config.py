import os
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


def get_settings() -> Settings:
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        # En desarrollo, usar una key temporal. En producción, esto debe configurarse.
        import secrets
        secret_key = secrets.token_hex(32)
        print("WARNING: SECRET_KEY not configured in .env. Using temporary key.")
        print("   Add SECRET_KEY=your_secret_key to .env for production.")
    
    return Settings(
        SECRET_KEY=secret_key,
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        REFRESH_TOKEN_EXPIRE_DAYS=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    )


settings = get_settings()