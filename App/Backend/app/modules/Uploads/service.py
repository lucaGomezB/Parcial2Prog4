"""
Upload service — business logic for Cloudinary image upload and deletion.

Key rules:
- Only image/jpeg, image/png, image/gif, image/webp are allowed
- Maximum file size is 10 MB
- All methods are @staticmethod (consistent with other services)
- No DB interaction — no UoW or Session needed
"""

import cloudinary.uploader
from fastapi import HTTPException, UploadFile

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class CloudinaryService:
    """Business logic for Cloudinary image upload and deletion.

    All methods are @staticmethod since this service has no internal state.
    """

    @staticmethod
    def upload_image(file: UploadFile) -> dict:
        """Upload an image file to Cloudinary.

        Validates:
        - Content type must be in ALLOWED_CONTENT_TYPES
        - File size must not exceed MAX_FILE_SIZE

        Returns:
            dict with secure_url and public_id from Cloudinary response.

        Raises:
            HTTPException(400) on invalid type or oversized file.
        """
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Formato no permitido. Use jpeg, png, gif o webp.",
            )

        contents = file.file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="La imagen no debe superar 10 MB.",
            )

        result = cloudinary.uploader.upload(contents, resource_type="image")
        return {"secure_url": result["secure_url"], "public_id": result["public_id"]}

    @staticmethod
    def delete_image(public_id: str) -> dict:
        """Delete an image from Cloudinary by its public ID.

        Returns:
            dict with detail message and public_id on success.

        Raises:
            HTTPException(400) if deletion fails (image not found, etc.).
        """
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
        if result.get("result") != "ok":
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo eliminar la imagen: {result.get('result')}",
            )
        return {"detail": "Imagen eliminada", "public_id": public_id}
