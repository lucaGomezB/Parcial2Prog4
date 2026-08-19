"""
Base Unit of Work pattern for transactional boundaries.

Provides a generic context-managed transaction boundary with helper methods
for session-level operations. Domain UoWs inherit from this class and only
need to override __init__ to wire typed repositories.

Usage:
    from app.core.base_uow import BaseUnitOfWork

    class MyDomainUnitOfWork(BaseUnitOfWork):
        def __init__(self, session: Session):
            super().__init__(session)
            self.my_repo = MyRepository(session)
"""

from sqlmodel import Session


class BaseUnitOfWork:
    """
    Generic transactional boundary for domain operations.

    Subclasses only override __init__ to wire domain-specific repositories.
    The context manager (__enter__/__exit__) handles commit on success
    and rollback on exception automatically.

    Usage:
        with MyDomainUnitOfWork(session) as uow:
            uow.my_repo.add(entity)
            # auto-commits on exit, rollbacks on exception
    """

    def __init__(self, session: Session):
        self.session = session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        return False

    def add(self, entity):
        """Stage an entity for insert or update in the current session."""
        self.session.add(entity)
        return entity

    def flush(self):
        """Send pending SQL to DB without committing (preserves rollback)."""
        self.session.flush()

    def refresh(self, entity):
        """Reload entity from DB after flush to get generated values."""
        self.session.refresh(entity)
        return entity

    def delete(self, entity):
        """Mark an entity for deletion on next flush/commit."""
        self.session.delete(entity)

    def commit(self):
        """Persist all pending changes to the database."""
        self.session.commit()

    def rollback(self):
        """Undo all pending changes since the last commit."""
        self.session.rollback()
