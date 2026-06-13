"""Generic paginated response schema for list endpoints."""
from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper.
    
    Attributes:
        items: List of items for the current page.
        total: Total number of records matching the query (not just this page).
        skip: Offset used for this page.
        limit: Maximum items per page.
    """
    items: list[T]
    total: int
    skip: int
    limit: int
