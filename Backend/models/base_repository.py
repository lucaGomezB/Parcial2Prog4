from typing import Generic, List, Optional, TypeVar
from sqlmodel import SQLModel, Session, col, select
from models.base import SoftDeleteModel

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """Generic base repository providing common CRUD operations.

    Features:
    - `add()`, `refresh()`, `flush()` shared by all subclasses
    - `get_by_id()`, `get_all()` with automatic soft-delete filtering
      when the model class inherits from SoftDeleteModel
    - Subclasses override `get_by_id()` / `get_all()` only for
      domain-specific query behavior (different PK, custom filters, etc.)
    """

    def __init__(self, session: Session, model_class: type[T]):
        self.session = session
        self.model_class = model_class
        # Detect soft-delete support at class level (compile-time check)
        self._is_soft_delete = False
        try:
            self._is_soft_delete = issubclass(model_class, SoftDeleteModel)
        except TypeError:
            pass

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add(self, entity: T) -> T:
        """Stage an entity for insert/update."""
        self.session.add(entity)
        return entity

    def refresh(self, entity: T) -> T:
        """Reload an entity from the database (populates generated fields)."""
        self.session.refresh(entity)
        return entity

    def flush(self):
        """Flush pending changes to the database without committing."""
        self.session.flush()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_pk_attr(self):
        """Return the SQLModel attribute for the primary key column.

        Tries the conventional ``id`` first, then falls back to the
        actual PK column from SQLAlchemy table metadata (handles
        semantic PKs like ``codigo`` on ``Rol``).
        """
        try:
            return self.model_class.id  # type: ignore[attr-defined]
        except AttributeError:
            pass
        try:
            pk_name = list(
                self.model_class.__table__.primary_key.columns.keys()  # type: ignore[attr-defined]
            )[0]
            return getattr(self.model_class, pk_name)
        except (AttributeError, IndexError, KeyError) as exc:
            raise AttributeError(
                f"{self.model_class.__name__} has no detectable PK column"
            ) from exc

    # ------------------------------------------------------------------
    # Read operations (default implementations)
    # ------------------------------------------------------------------

    def get_by_id(self, entity_id) -> Optional[T]:
        """Fetch a single entity by primary key.

        Automatically filters out soft-deleted rows when the model
        inherits from SoftDeleteModel.
        """
        pk_col = self._get_pk_attr()
        statement = select(self.model_class).where(pk_col == entity_id)
        if self._is_soft_delete:
            statement = statement.where(
                col(self.model_class.deleted_at).is_(None)  # type: ignore[attr-defined]
            )
        return self.session.exec(statement).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Fetch a paginated list of entities.

        Automatically excludes soft-deleted rows when the model
        inherits from SoftDeleteModel. Ordered by the primary key
        column descending (handles semantic PKs like ``codigo``).
        """
        pk_col = self._get_pk_attr()
        statement = select(self.model_class)
        if self._is_soft_delete:
            statement = statement.where(
                col(self.model_class.deleted_at).is_(None)  # type: ignore[attr-defined]
            )
        statement = (
            statement.offset(skip)
            .limit(limit)
            .order_by(pk_col.desc())
        )
        return self.session.exec(statement).all()
