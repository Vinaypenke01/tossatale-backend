"""
apps/audit_logs/models.py — Audit Log Model per §47 & Phase 6 Spec
"""
import uuid
from django.conf import settings
from django.db import models
from common.constants import AuditAction


class AuditLog(models.Model):
    """
    AuditLog model storing administrative actions and field diffs per §47.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
        db_index=True,
    )
    action = models.CharField(max_length=20, choices=AuditAction.CHOICES, db_index=True)
    object_type = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=255, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)

    changes = models.JSONField(default=dict, blank=True, help_text="Diff of changed fields e.g. {'before': {}, 'after': {}}")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "action"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        actor_email = self.actor.email if self.actor else "System"
        return f"AuditLog({actor_email}, action={self.action}, obj={self.object_type}:{self.object_id})"
