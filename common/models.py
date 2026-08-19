"""
Common — Base Model
All major models inherit from this. Provides:
- UUID primary key (§7)
- created_at / updated_at timestamps
- Soft deletion (is_deleted, deleted_at)
"""
import uuid
from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model for all Tossatale models.
    Provides UUID PK, timestamps, and soft deletion per §7.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def soft_delete(self):
        """Soft delete this record instead of destroying it."""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class ActiveManager(models.Manager):
    """Default manager that excludes soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
