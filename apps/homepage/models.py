"""
apps/homepage/models.py — Homepage Section Model per §19 & Phase 5 Spec
"""
import uuid
from django.conf import settings
from django.db import models
from common.constants import HomepageSectionKey


class HomepageSection(models.Model):
    """
    HomepageSection model allowing admins to toggle, reorder, and configure homepage modules per §19.
    Enforces unique constraint on section_key.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section_key = models.CharField(
        max_length=50, choices=HomepageSectionKey.CHOICES, unique=True, db_index=True
    )
    title = models.CharField(max_length=255, blank=True, help_text="Display title override")
    is_enabled = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)
    config = models.JSONField(
        default=dict, blank=True, help_text="Per-section layout config e.g. {'count': 6, 'layout': 'grid'}"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "homepage_sections"
        ordering = ["display_order"]

    def __str__(self):
        return f"HomepageSection({self.section_key}, enabled={self.is_enabled})"
