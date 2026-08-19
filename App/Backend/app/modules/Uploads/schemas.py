"""
Upload schemas — Pydantic models for image upload API request/response.

These schemas define the shape of data returned by the upload and
delete endpoints.
"""

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    """Response schema for a successful image upload."""
    secure_url: str
    public_id: str


class ImageDeleteResponse(BaseModel):
    """Response schema for a successful image deletion."""
    detail: str
    public_id: str
