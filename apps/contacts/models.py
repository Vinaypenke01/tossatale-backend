"""
apps/contacts/models.py — Contact Message Model per §21 & Phase 5 Spec
"""
import uuid
from django.conf import settings
from django.db import models
from common.constants import ContactStatus


class ContactMessage(models.Model):
    """
    ContactMessage model storing contact form submissions per §21.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()

    status = models.CharField(
        max_length=20, choices=ContactStatus.CHOICES, default=ContactStatus.NEW, db_index=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contact_messages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ContactMessage({self.name}, <{self.email}>, status={self.status})"
