"""
Generic repository pattern implementation for CRUD operations.

Provides a type-safe BaseRepository class that encapsulates common
database operations: create, read (by ID, paginated list), update, and
delete. Designed to be subclassed by domain-specific repositories that
override methods only when custom query behavior is needed.

Key features:
- Generic type parameter T bound to SQLModel for type safety.
- Automatic soft-delete filtering when the model inherits SoftDeleteModel.
- Dynamic primary key detection supporting both conventional 'id' fields
  and semantic PKs like 'codigo' on the Rol model.
"""

from typing import Generic, List, Optional, TypeVar
from sqlmodel import SQLModel, Session, col, select
from app.core.base import SoftDeleteModel

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """
    Generic base repository providing common CRUD operations.

    Subclasses define model-specific query methods and override defaults
    when domain logic requires different PK columns, custom filters, or
    additional eager loading.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session):
                super().__init__(session, User)
    """

    def __init__(self, session: Session, model_class: type[T]):
        """
        Initialize the repository with a database session and model class.

        Detects at construction time whether the model supports soft-delete
        to automatically filter deleted records in query methods.
        """
        self.session = session
        self.model_class = model_class
        # Determine if the model class has soft-delete support
        self._is_soft_delete = False
        try:
            self._is_soft_delete = issubclass(model_class, SoftDeleteModel)
        except TypeError:
            # issubclass raises TypeError if model_class is not a class
            pass
        # Flag to disable soft-delete filtering (for ADMIN visibility of deleted records)
        self._incluir_eliminados = False

    def with_deleted(self, incluir: bool = True):
        """
        When True, soft-delete filtering is DISABLED for subsequent queries.
        Only affects models that inherit from SoftDeleteModel.
        Useful for ADMIN endpoints that need to see deleted records.

        Usage:
            repo = UsuarioRepository(session)
            repo.with_deleted(True)
            all_users = repo.get_all()
        """
        self._incluir_eliminados = incluir
        return self

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add(self, entity: T) -> T:
        """
        Stage an entity for insert or update in the current session.

        The entity is not persisted until commit() or flush() is called.
        Returns the entity itself for method chaining convenience.

        Prefer create() for new entities or update() for existing ones
        — the semantic names make the caller's intent explicit.
        """
        self.session.add(entity)
        return entity

    def create(self, entity: T) -> T:
        """
        Insert a new entity and immediately flush + refresh.

        After this call the entity has its auto-generated fields populated
        (primary key, created_at, updated_at). Use this when you need the
        generated id for subsequent operations within the same transaction.

        Returns the refreshed entity.
        """
        self.session.add(entity)
        self.session.flush()
        self.session.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        """
        Stage an existing entity for update in the current session.

        SQLAlchemy detects the entity already has a primary key and
        treats it as an update. No flush/refresh is performed — the
        caller's UoW handles commit. Returns the entity itself.

        Use this when modifying an entity fetched via get_by_id().
        """
        self.session.add(entity)
        return entity

    def refresh(self, entity: T) -> T:
        """
        Reload an entity's data from the database.

        Useful after a flush() to populate auto-generated fields
        (e.g., BIGSERIAL id, default timestamps) into the Python object.
        """
        self.session.refresh(entity)
        return entity

    def delete(self, entity: T) -> T:
        """
        Soft-delete an entity by setting its deleted_at timestamp.

        Only works for models inheriting from SoftDeleteModel.
        The entity is staged via add() — the caller's UoW commit()
        persists the change atomically.
        """
        if not self._is_soft_delete:
            raise TypeError(
                f"{self.model_class.__name__} does not support soft delete. "
                f"Inherit from SoftDeleteModel to enable this method."
            )
        from app.core.base import get_utc_now
        entity.deleted_at = get_utc_now()
        self.session.add(entity)
        return entity

    def flush(self):
        """
        Send pending SQL statements to the database without committing.

        The changes can still be reverted with rollback() if needed.
        Useful when you need the generated primary key before committing
        the full transaction (e.g., when creating related child records).
        """
        self.session.flush()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_pk_attr(self):
        """
        Resolve the primary key column attribute for the model.

        Tries the conventional 'id' field first. Falls back to inspecting
        SQLAlchemy table metadata for the actual PK column, which handles
        semantic primary keys like 'codigo' on the Rol model.

        Returns the SQLModel/SQLAlchemy column attribute that can be used
        in query expressions (e.g., select().where(pk_col == value)).
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

    def get_by_id(self, entity_id, for_update: bool = False) -> Optional[T]:
        """
        Retrieve a single entity by its primary key value.

        Automatically appends a soft-delete filter (deleted_at IS NULL)
        when the model inherits from SoftDeleteModel. Returns None if
        no matching record is found or the record is soft-deleted.

        When for_update=True, the row is locked with SELECT FOR UPDATE
        to prevent race conditions on concurrent writes.
        """
        pk_col = self._get_pk_attr()
        statement = select(self.model_class).where(pk_col == entity_id)
        if self._is_soft_delete and not self._incluir_eliminados:
            statement = statement.where(
                col(self.model_class.deleted_at).is_(None)  # type: ignore[attr-defined]
            )
        if for_update:
            statement = statement.with_for_update()
        return self.session.exec(statement).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Retrieve a paginated list of entities.

        Excludes soft-deleted records when the model inherits from
        SoftDeleteModel. Results are ordered by the primary key column
        descending to show the most recently created records first.
        """
        pk_col = self._get_pk_attr()
        statement = select(self.model_class)
        if self._is_soft_delete and not self._incluir_eliminados:
            statement = statement.where(
                col(self.model_class.deleted_at).is_(None)  # type: ignore[attr-defined]
            )
        statement = (
            statement.offset(skip)
            .limit(limit)
            .order_by(pk_col.desc())
        )
        return self.session.exec(statement).all()

    def count_all(self, search: Optional[str] = None, search_column: Optional[str] = None) -> int:
        """
        Count all non-deleted records, optionally filtered by ILIKE search.

        When search and search_column are provided, only records whose
        named column matches the search term (ILIKE) are counted.
        Soft-deleted records are excluded automatically when the model
        inherits from SoftDeleteModel.

        Args:
            search: Optional search term for ILIKE filtering.
            search_column: Name of the column to apply ILIKE search on.

        Returns:
            Integer count of matching records.
        """
        from sqlmodel import func
        statement = select(func.count()).select_from(self.model_class)
        if self._is_soft_delete and not self._incluir_eliminados:
            statement = statement.where(
                col(self.model_class.deleted_at).is_(None)  # type: ignore[attr-defined]
            )
        if search and search_column:
            column_attr = getattr(self.model_class, search_column, None)
            if column_attr is not None:
                statement = statement.where(col(column_attr).ilike(f"%{search}%"))
        result = self.session.exec(statement)
        return result.one()

    def search(self, column: str, query: str, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Paginated ILIKE search on a named column, excluding soft-deleted records.

        Args:
            column: Name of the model column to search on (e.g., "nombre").
            query: Search term for ILIKE matching.
            skip: Offset for pagination.
            limit: Maximum number of results.

        Returns:
            List of matching model instances.
        """
        pk_col = self._get_pk_attr()
        statement = select(self.model_class)
        if self._is_soft_delete and not self._incluir_eliminados:
            statement = statement.where(
                col(self.model_class.deleted_at).is_(None)  # type: ignore[attr-defined]
            )
        column_attr = getattr(self.model_class, column, None)
        if column_attr is not None:
            statement = statement.where(col(column_attr).ilike(f"%{query}%"))
        statement = statement.offset(skip).limit(limit).order_by(pk_col.desc())
        return self.session.exec(statement).all()
