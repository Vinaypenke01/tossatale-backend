"""
apps/banners/models.py — Banner Model per §20 & Phase 5 Spec
"""
import uuid
from django.conf import settings
from django.db import models
from common.constants import BannerType
from apps.stories.models import Story
from apps.categories.models import Category


class Banner(models.Model):
    """
    Banner model representing dynamic homepage and promotional banners per §20.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)

    banner_type = models.CharField(
        max_length=20, choices=BannerType.CHOICES, default=BannerType.HERO, db_index=True
    )
    image = models.URLField(help_text="Cloudinary banner image URL")
    mobile_image = models.URLField(blank=True, help_text="Cloudinary mobile banner image URL")

    cta_text = models.CharField(max_length=100, blank=True, help_text="Call to action button text")
    cta_url = models.CharField(max_length=500, blank=True, help_text="Call to action link URL")

    linked_story = models.ForeignKey(
        Story, on_delete=models.SET_NULL, null=True, blank=True, related_name="banners"
    )
    linked_category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="banners"
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_banners"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "banners"
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return f"Banner({self.title}, type={self.banner_type})"
