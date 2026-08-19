"""
Routing helpers for consistent HTTP error handling.

Provides reusable utilities that eliminate boilerplate error-raising
patterns across routers and services.
"""

from typing import Optional, TypeVar
from fastapi import HTTPException

T = TypeVar("T")


def get_or_404(obj: Optional[T], detail: str = "No encontrado") -> T:
    """
    Return the object if it is not None, otherwise raise HTTP 404.

    Replaces the repetitive pattern:

        if not obj:
            raise HTTPException(status_code=404, detail="...")
        return obj

    with a single call:

        obj = get_or_404(obj, "mensaje")

    Args:
        obj: The object to check (usually a DB query result).
        detail: Human-readable error message for the 404 response.

    Returns:
        The object if it is not None.

    Raises:
        HTTPException: 404 with the given detail if obj is None.
    """
    if obj is None:
        raise HTTPException(status_code=404, detail=detail)
    return obj
