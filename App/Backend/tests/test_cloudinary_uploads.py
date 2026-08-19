"""
Tests for Cloudinary Uploads module.

These tests verify that:
- CloudinarySettings loads from environment variables correctly
- ImageUploadResponse and ImageDeleteResponse schemas are structured correctly
- CloudinaryService.upload_image validates file type and size, delegates to cloudinary SDK
- CloudinaryService.delete_image delegates to cloudinary SDK and handles failures
"""
import os
from unittest.mock import MagicMock, patch, ANY
import pytest
from fastapi import HTTPException, UploadFile


# ── RED phase tests for Task 1.2 — CloudinaryConfiguration ──

class TestCloudinarySettings:
    """Tests for CloudinarySettings — config loading from environment."""

    def test_settings_reads_from_environment_variables(self):
        """CloudinarySettings loads cloud_name, api_key, api_secret from env."""
        from app.core.cloudinary_config import CloudinarySettings

        with patch.dict(os.environ, {
            "CLOUD_NAME": "test-cloud",
            "CLOUDINARY_API_KEY": "test-key-123",
            "CLOUDINARY_API_SECRET": "test-secret-abc",
        }, clear=True):
            settings = CloudinarySettings(
                cloud_name=os.getenv("CLOUD_NAME", ""),
                api_key=os.getenv("CLOUDINARY_API_KEY", ""),
                api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
            )
            assert settings.cloud_name == "test-cloud"
            assert settings.api_key == "test-key-123"
            assert settings.api_secret == "test-secret-abc"

    def test_settings_defaults_to_empty_strings_when_vars_missing(self):
        """When env vars are missing, CloudinarySettings gets empty strings (graceful)."""
        from app.core.cloudinary_config import CloudinarySettings

        with patch.dict(os.environ, {}, clear=True):
            settings = CloudinarySettings(
                cloud_name=os.getenv("CLOUD_NAME", ""),
                api_key=os.getenv("CLOUDINARY_API_KEY", ""),
                api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
            )
            assert settings.cloud_name == ""
            assert settings.api_key == ""
            assert settings.api_secret == ""

    def test_get_cloudinary_settings_returns_a_settings_instance(self):
        """get_cloudinary_settings() returns a CloudinarySettings with env values."""
        from app.core.cloudinary_config import CloudinarySettings, get_cloudinary_settings

        with patch.dict(os.environ, {
            "CLOUD_NAME": "factory-cloud",
            "CLOUDINARY_API_KEY": "factory-key",
            "CLOUDINARY_API_SECRET": "factory-secret",
        }, clear=True):
            settings = get_cloudinary_settings()
            assert isinstance(settings, CloudinarySettings)
            assert settings.cloud_name == "factory-cloud"
            assert settings.api_key == "factory-key"
            assert settings.api_secret == "factory-secret"

    def test_module_level_singleton_exists(self):
        """module-level cloudinary_settings singleton is a CloudinarySettings instance."""
        with patch.dict(os.environ, {
            "CLOUD_NAME": "singleton-cloud",
            "CLOUDINARY_API_KEY": "singleton-key",
            "CLOUDINARY_API_SECRET": "singleton-secret",
        }, clear=True):
            # Force reimport to pick up patched env
            import importlib
            import app.core.cloudinary_config

            importlib.reload(app.core.cloudinary_config)

            from app.core.cloudinary_config import cloudinary_settings, CloudinarySettings
            assert isinstance(cloudinary_settings, CloudinarySettings)
            assert cloudinary_settings.cloud_name == "singleton-cloud"


# ── RED phase tests for Task 1.3 — Upload Schemas ──

class TestUploadSchemas:
    """Tests for ImageUploadResponse and ImageDeleteResponse schemas."""

    def test_image_upload_response_has_required_fields(self):
        """ImageUploadResponse accepts secure_url and public_id strings."""
        from app.modules.Uploads.schemas import ImageUploadResponse

        resp = ImageUploadResponse(
            secure_url="https://res.cloudinary.com/demo/image/upload/v1/img.jpg",
            public_id="sample_public_id",
        )
        assert resp.secure_url == "https://res.cloudinary.com/demo/image/upload/v1/img.jpg"
        assert resp.public_id == "sample_public_id"

    def test_image_delete_response_has_required_fields(self):
        """ImageDeleteResponse accepts detail and public_id strings."""
        from app.modules.Uploads.schemas import ImageDeleteResponse

        resp = ImageDeleteResponse(
            detail="Imagen eliminada",
            public_id="sample_public_id",
        )
        assert resp.detail == "Imagen eliminada"
        assert resp.public_id == "sample_public_id"


# ── RED phase tests for Task 1.4 — CloudinaryService ──

def _make_upload_file(filename="test.jpg", content_type="image/jpeg", content=b"fake-image"):
    """Helper: create an UploadFile mock that behaves like FastAPI's UploadFile."""
    mock = MagicMock(spec=UploadFile)
    mock.filename = filename
    mock.content_type = content_type
    mock.file = MagicMock()
    mock.file.read.return_value = content
    return mock


class TestUploadImage:
    """CloudinaryService.upload_image tests."""

    def test_uploads_valid_jpeg_and_returns_url_and_public_id(self):
        """Valid JPEG upload calls cloudinary.uploader.upload and returns result dict."""
        from app.modules.Uploads.service import CloudinaryService

        mock_file = _make_upload_file("photo.jpg", "image/jpeg", b"jpg-data")

        with patch("app.modules.Uploads.service.cloudinary") as mock_cloudinary:
            mock_cloudinary.uploader.upload.return_value = {
                "secure_url": "https://res.cloudinary.com/demo/image/upload/v1/abc123.jpg",
                "public_id": "abc123",
            }

            result = CloudinaryService.upload_image(mock_file)

        assert result == {
            "secure_url": "https://res.cloudinary.com/demo/image/upload/v1/abc123.jpg",
            "public_id": "abc123",
        }
        mock_cloudinary.uploader.upload.assert_called_once_with(b"jpg-data", resource_type="image")

    def test_raises_400_for_invalid_content_type(self):
        """Non-image content types raise HTTPException 400."""
        from app.modules.Uploads.service import CloudinaryService

        mock_file = _make_upload_file("doc.pdf", "application/pdf", b"pdf-data")

        with pytest.raises(HTTPException) as exc:
            CloudinaryService.upload_image(mock_file)

        assert exc.value.status_code == 400
        assert "Formato no permitido" in exc.value.detail

    def test_raises_400_for_file_too_large(self):
        """Files larger than 10 MB raise HTTPException 400."""
        from app.modules.Uploads.service import CloudinaryService

        large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        mock_file = _make_upload_file("big.jpg", "image/jpeg", large_content)

        with pytest.raises(HTTPException) as exc:
            CloudinaryService.upload_image(mock_file)

        assert exc.value.status_code == 400
        assert "10 MB" in exc.value.detail

    def test_accepts_png_gif_and_webp_formats(self):
        """PNG, GIF, and WebP content types are treated as valid images."""
        from app.modules.Uploads.service import CloudinaryService

        for ct, ext in [("image/png", "png"), ("image/gif", "gif"), ("image/webp", "webp")]:
            mock_file = _make_upload_file(f"img.{ext}", ct, b"small-data")

            with patch("app.modules.Uploads.service.cloudinary") as mock_cloudinary:
                mock_cloudinary.uploader.upload.return_value = {
                    "secure_url": f"https://res.cloudinary.com/demo/{ext}/abc.jpg",
                    "public_id": f"abc{ext}",
                }
                result = CloudinaryService.upload_image(mock_file)

            assert "secure_url" in result
            assert "public_id" in result


class TestDeleteImage:
    """CloudinaryService.delete_image tests."""

    def test_deletes_image_and_returns_detail(self):
        """Valid public_id deletion returns detail and public_id."""
        from app.modules.Uploads.service import CloudinaryService

        with patch("app.modules.Uploads.service.cloudinary") as mock_cloudinary:
            mock_cloudinary.uploader.destroy.return_value = {"result": "ok"}

            result = CloudinaryService.delete_image("img-to-delete")

        assert result == {"detail": "Imagen eliminada", "public_id": "img-to-delete"}
        mock_cloudinary.uploader.destroy.assert_called_once_with("img-to-delete", resource_type="image")

    def test_raises_400_when_cloudinary_deletion_fails(self):
        """Non-ok result from Cloudinary destroy raises HTTPException 400."""
        from app.modules.Uploads.service import CloudinaryService

        with patch("app.modules.Uploads.service.cloudinary") as mock_cloudinary:
            mock_cloudinary.uploader.destroy.return_value = {"result": "not found"}

            with pytest.raises(HTTPException) as exc:
                CloudinaryService.delete_image("non-existent-id")

        assert exc.value.status_code == 400
        assert "No se pudo eliminar" in exc.value.detail
