"""
Cloudinary configuration — loaded from environment variables.

Follows the same pattern as core/security/config.py:
- CloudinarySettings(BaseModel) reads credentials from env
- get_cloudinary_settings() factory function
- Module-level cloudinary_settings singleton
- Global cloudinary.config() initialization
"""

import os
import cloudinary
from pydantic import BaseModel


class CloudinarySettings(BaseModel):
    """Cloudinary configuration parameters loaded from environment.

    Attributes:
        cloud_name: Cloudinary cloud name (CLOUD_NAME).
        api_key: Cloudinary API key (CLOUDINARY_API_KEY).
        api_secret: Cloudinary API secret (CLOUDINARY_API_SECRET).
    """
    cloud_name: str
    api_key: str
    api_secret: str


def get_cloudinary_settings() -> CloudinarySettings:
    """Factory that reads Cloudinary settings from environment variables.

    Returns a CloudinarySettings instance with values from .env.
    If any variable is missing, defaults to empty string (the SDK
    will raise an authentication error on API call).
    """
    return CloudinarySettings(
        cloud_name=os.getenv("CLOUD_NAME", ""),
        api_key=os.getenv("CLOUDINARY_API_KEY", ""),
        api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
    )


# Module-level singleton: import from app.core.cloudinary_config as:
#   from app.core.cloudinary_config import cloudinary_settings
cloudinary_settings = get_cloudinary_settings()

# Initialize cloudinary SDK globally at module import time.
# This is equivalent to calling cloudinary.config() once when the app starts.
cloudinary.config(
    cloud_name=cloudinary_settings.cloud_name,
    api_key=cloudinary_settings.api_key,
    api_secret=cloudinary_settings.api_secret,
)
