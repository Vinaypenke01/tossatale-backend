from .base import *  # noqa

DEBUG = True

# Database is controlled by base.py via USE_POSTGRES env var toggle.
# If USE_POSTGRES=False (default), it uses local SQLite (db.sqlite3).

# In development, Redis is optional. If USE_REDIS env var is not set to 'True', use in-memory cache.
USE_REDIS = env.bool("USE_REDIS", default=False)

if not USE_REDIS:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "tossatale-dev-cache",
        }
    }

# Make Celery optional in development: execute tasks inline synchronously
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
CELERY_TASK_EAGER_PROPAGATES = True

# Disable Cloudinary locally — use local file storage
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Emails go to console in development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow all CORS in development
CORS_ALLOW_ALL_ORIGINS = True

# Django Debug Toolbar (optional)
INSTALLED_APPS += ["django_extensions"]  # noqa
