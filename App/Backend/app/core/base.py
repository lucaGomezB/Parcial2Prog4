"""
Base SQLModel configuration and shared mixins.

Provides foundational model classes used across all domain modules:

- TimestampModel: adds automatic created_at and updated_at columns.
- SoftDeleteModel: adds deleted_at for logical (soft) deletion.

These are mixin classes designed to be inherited by domain models
(e.g., Usuario inherits from both TimestampModel and SoftDeleteModel).
Table naming follows snake_case convention matching PostgreSQL standards.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


def get_utc_now():
    """
    Returns the current UTC datetime, timezone-aware.

    Used as a default_factory for datetime fields to ensure
    consistent timezone handling across all models. The modern
    approach uses timezone.utc instead of the deprecated utcnow().
    """
    return datetime.now(timezone.utc)


class TimestampModel(SQLModel):
    """
    Mixin that adds created_at and updated_at timestamp columns.

    - created_at: set once on insert, never updated.
    - updated_at: automatically updated on every row modification
      via SQLAlchemy's onupdate mechanism.

    Both fields use get_utc_now() as the default factory.
    """

    created_at: datetime = Field(
        default_factory=get_utc_now,
        nullable=False
    )

    updated_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column_kwargs={"onupdate": get_utc_now},
        nullable=False
    )


class SoftDeleteModel(SQLModel):
    """
    Mixin that adds soft-delete capability via a deleted_at column.

    When deleted_at is NULL, the record is active.
    When deleted_at has a timestamp, the record is considered deleted.

    All repository queries must filter: WHERE deleted_at IS NULL.
    This pattern preserves referential integrity for related records
    (e.g., orders referencing a deleted user) while hiding deleted data.
    """

    deleted_at: Optional[datetime] = Field(default=None, index=True)
