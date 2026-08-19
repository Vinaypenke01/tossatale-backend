"""
apps/notifications — Notification Model and Service stub
Full implementation in Phase 2.
"""
import uuid
from django.db import models
from django.conf import settings
from common.constants import NotificationType


class Notification(models.Model):
    """
    In-app notification model per §18.1.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_notifications",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.CHOICES,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=255, blank=True)
    action_url = models.URLField(blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"Notification({self.notification_type} → {self.recipient.email})"
