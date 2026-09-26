"""
common/services/media_service.py — Media & Cloudinary Storage Service
Handles uploading images to Cloudinary CDN if credentials exist in settings,
otherwise gracefully falls back to optimized Base64 data URI storage without disrupting user experience.
"""
import base64
import logging
import os
from io import BytesIO
from django.conf import settings
from PIL import Image, ImageOps

logger = logging.getLogger("common.services.media")


class MediaService:

    @classmethod
    def is_cloudinary_configured(cls) -> bool:
        """Returns True if Cloudinary URL or all required Cloudinary settings are non-empty."""
        c_url = getattr(settings, "CLOUDINARY_URL", "")
        cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", "")
        api_key = getattr(settings, "CLOUDINARY_API_KEY", "")
        api_secret = getattr(settings, "CLOUDINARY_API_SECRET", "")
        return bool(c_url or (cloud_name and api_key and api_secret))

    @classmethod
    def optimize_image_base64(cls, file_obj_or_bytes, max_dim: int = 1400, quality: int = 80) -> str:
        """
        Compresses image using Pillow and returns a JPEG base64 data URI fallback.
        """
        try:
            if hasattr(file_obj_or_bytes, "read"):
                file_obj_or_bytes.seek(0)
                image = Image.open(file_obj_or_bytes)
            elif isinstance(file_obj_or_bytes, bytes):
                image = Image.open(BytesIO(file_obj_or_bytes))
            elif isinstance(file_obj_or_bytes, str):
                if file_obj_or_bytes.startswith("data:image"):
                    _, encoded = file_obj_or_bytes.split(",", 1)
                    data = base64.b64decode(encoded)
                    image = Image.open(BytesIO(data))
                elif os.path.exists(file_obj_or_bytes):
                    image = Image.open(file_obj_or_bytes)
                else:
                    try:
                        data = base64.b64decode(file_obj_or_bytes)
                        image = Image.open(BytesIO(data))
                    except Exception:
                        return file_obj_or_bytes
            else:
                return str(file_obj_or_bytes)

            # Auto-rotate image based on EXIF orientation if present
            try:
                image = ImageOps.exif_transpose(image)
            except Exception:
                pass

            # Handle transparency (RGBA, LA, P with transparency) smoothly by compositing onto white canvas
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                rgba_img = image.convert("RGBA")
                bg = Image.new("RGB", rgba_img.size, (255, 255, 255))
                bg.paste(rgba_img, mask=rgba_img.split()[3])
                image = bg
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # Resize if exceeds max_dim without upscaling
            width, height = image.size
            if width > max_dim or height > max_dim:
                if width > height:
                    new_height = max(1, int((height * max_dim) / width))
                    new_width = max_dim
                else:
                    new_width = max(1, int((width * max_dim) / height))
                    new_height = max_dim
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            encoded_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded_str}"
        except Exception as e:
            logger.warning("Failed to optimize image with Pillow: %s", e)
            if isinstance(file_obj_or_bytes, str):
                return file_obj_or_bytes
            return ""

    @classmethod
    def upload_image(cls, file_obj_or_base64, folder: str = "blogs", max_dim: int = 1400) -> dict:
        """
        Uploads image to Cloudinary if available, otherwise returns optimized base64 data URI.
        Always returns a structured dict:
        {
            "url": "https://res.cloudinary.com/..." or "data:image/jpeg;base64,...",
            "storage_type": "cloudinary" | "base64" | "external_url",
            "is_cdn": bool,
            "format": "webp" | "jpg" | "jpeg"
        }
        """
        if not file_obj_or_base64:
            return {"url": "", "storage_type": "empty", "is_cdn": False}

        # If already an external HTTPS URL, return as-is
        if isinstance(file_obj_or_base64, str) and (file_obj_or_base64.startswith("http://") or file_obj_or_base64.startswith("https://")):
            return {"url": file_obj_or_base64, "storage_type": "external_url", "is_cdn": True}

        if cls.is_cloudinary_configured():
            try:
                import cloudinary
                import cloudinary.uploader

                c_url = getattr(settings, "CLOUDINARY_URL", "")
                if c_url:
                    cloudinary.config(cloudinary_url=c_url, secure=True)
                else:
                    cloudinary.config(
                        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                        api_key=settings.CLOUDINARY_API_KEY,
                        api_secret=settings.CLOUDINARY_API_SECRET,
                        secure=True,
                    )

                upload_folder = f"tossatale/{folder}"
                if hasattr(file_obj_or_base64, "seek"):
                    file_obj_or_base64.seek(0)

                result = cloudinary.uploader.upload(
                    file_obj_or_base64,
                    folder=upload_folder,
                    transformation=[
                        {"width": max_dim, "crop": "limit"},
                        {"quality": "auto", "fetch_format": "auto"},
                    ],
                    resource_type="image",
                )

                secure_url = result.get("secure_url") or result.get("url")
                if secure_url:
                    logger.info("Successfully uploaded image to Cloudinary: %s", secure_url)
                    return {
                        "url": secure_url,
                        "public_id": result.get("public_id"),
                        "storage_type": "cloudinary",
                        "is_cdn": True,
                        "format": result.get("format", "webp"),
                        "width": result.get("width"),
                        "height": result.get("height"),
                    }
            except Exception as exc:
                logger.error("Cloudinary upload failed, falling back to base64: %s", exc)

        # Graceful fallback: return optimized base64
        if hasattr(file_obj_or_base64, "seek"):
            file_obj_or_base64.seek(0)
        base64_data = cls.optimize_image_base64(file_obj_or_base64, max_dim=max_dim)
        return {
            "url": base64_data,
            "storage_type": "base64",
            "is_cdn": False,
            "format": "jpeg",
        }
