"""
apps/categories — Category and Tag Models
Implements §10 schema.
"""
from django.db import models
from django.conf import settings
from common.models import BaseModel, ActiveManager
from common.constants import CategoryType


class Category(BaseModel):
    """
    Content category supporting story, blog, and video categorization per §10.1.
    """
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    category_type = models.CharField(
        max_length=20,
        choices=CategoryType.CHOICES,
        default=CategoryType.GENERAL,
        db_index=True,
    )
    icon = models.CharField(max_length=100, blank=True, help_text="Icon name or emoji")
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    # SEO
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.TextField(max_length=160, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="created_categories",
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "categories"
        ordering = ["display_order", "name"]
        # Name must be unique within category type per §10.1
        unique_together = [["name", "category_type"]]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["category_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.category_type})"


class Tag(BaseModel):
    """
    Flat tag model that can be applied to stories and blogs per §10.2.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    description = models.TextField(blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "tags"
        ordering = ["-usage_count", "name"]
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name
