"""
Database engine and session management module.

Provides the SQLModel database engine singleton and a FastAPI-compatible
session dependency generator. The engine is created once at import time
using the DATABASE_URL environment variable.

Session lifecycle:
- get_session() is a generator function used as a FastAPI dependency.
- Each request gets its own Session instance.
- The session is automatically closed when the request finishes
  (the context manager `with Session(engine) as session` handles this).
- FastAPI's dependency injection system manages the generator lifecycle:
  it calls get_session() on request start and cleans up on request end.
"""

import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Global engine instance shared across the application.
# echo=True enables SQL logging for debugging.
# Toggle via env var: SQL_ECHO=true or set echo=True directly.
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"
engine = create_engine(DATABASE_URL, echo=SQL_ECHO)


def get_session():
    """
    FastAPI dependency that provides a database session.

    Uses a context manager to ensure the session is properly closed
    after each request. The `yield` statement pauses execution and
    returns control to the caller (the request handler), then resumes
    to exit the context manager when the request completes.
    """
    with Session(engine) as session:
        yield session
