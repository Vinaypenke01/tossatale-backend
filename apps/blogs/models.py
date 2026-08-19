"""
apps/blogs/models.py — Editorial Blog Models per §13 & Phase 4 Spec
"""
import uuid
from django.conf import settings
from django.db import models
from common.constants import BlogStatus
from apps.categories.models import Category, Tag


class Blog(models.Model):
    """
    Blog model representing rich editorial posts with image support via Cloudinary per §13.
    Note contrast: Writer stories are text-only; Editorial blogs support images.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blogs"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    subtitle = models.CharField(max_length=500, blank=True, null=True)

    content = models.TextField(help_text="Rich HTML content with image support via Cloudinary")
    plain_text_content = models.TextField(blank=True)

    cover_image = models.TextField(blank=True, help_text="Cloudinary cover image URL or Base64 data URI")
    featured_image = models.TextField(blank=True, help_text="Cloudinary featured image URL or Base64 data URI")

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="blogs", db_index=True
    )
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)

    status = models.CharField(
        max_length=20, choices=BlogStatus.CHOICES, default=BlogStatus.DRAFT, db_index=True
    )
    is_featured = models.BooleanField(default=False)

    reading_time = models.PositiveIntegerField(default=0)
    word_count = models.PositiveIntegerField(default=0)
    views_count = models.BigIntegerField(default=0)
    likes_count = models.BigIntegerField(default=0)
    shares_count = models.BigIntegerField(default=0)

    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    scheduled_publish_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blogs"
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return f"Blog({self.title}, {self.status})"


class BlogTag(models.Model):
    """
    Junction model mapping Blog to Tag.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="blog_tags")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="tagged_blogs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "blog_tags"
        unique_together = ("blog", "tag")

    def __str__(self):
        return f"{self.blog.title} - {self.tag.name}"
