"""
RFC 7807 Problem Details for HTTP APIs.

Provides a helper to generate standardized error responses.
"""
from decimal import Decimal
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def problem_response(
    status: int,
    title: str,
    detail: str,
    type_url: str = "about:blank",
    instance: str | None = None,
    extra: dict | None = None,
) -> JSONResponse:
    """Generate an RFC 7807 Problem Details JSON response.

    Args:
        status: HTTP status code.
        title: Short, human-readable description.
        detail: Longer explanation specific to this occurrence.
        type_url: URI identifying the problem type. Defaults to "about:blank".
        instance: URI reference identifying the specific occurrence.
        extra: Additional fields to include (e.g., validation errors).

    Returns:
        JSONResponse with Content-Type: application/problem+json.
    """
    body: dict = {
        "type": type_url,
        "title": title,
        "status": status,
        "detail": detail,
    }
    if instance:
        body["instance"] = instance
    if extra:
        body.update(extra)

    # Use jsonable_encoder to handle non-serializable types (e.g. Decimal)
    # that may appear in Pydantic validation error metadata.
    serializable_body = jsonable_encoder(body)

    return JSONResponse(
        status_code=status,
        content=serializable_body,
        headers={"Content-Type": "application/problem+json"},
    )
