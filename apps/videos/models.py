"""
apps/videos/models.py — Video & Upcoming Projects Model
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from common.utils import extract_youtube_id, build_youtube_embed_url
from apps.categories.models import Category


class Video(models.Model):
    """
    Video model representing YouTube videos and Upcoming Projects per §14 & Phase 4.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    youtube_url = models.TextField(blank=True, help_text="Full YouTube video URL")
    youtube_video_id = models.CharField(max_length=50, blank=True)
    embed_url = models.TextField(blank=True)
    thumbnail_url = models.TextField(blank=True, help_text="Thumbnail URL or Base64 data URI")
    cover_image = models.TextField(blank=True, help_text="Cover poster URL or Base64 data URI")

    description = models.TextField(blank=True)
    editorial_note = models.TextField(blank=True)
    director = models.CharField(max_length=255, blank=True, default="Tossatale Studio")
    expected_release = models.CharField(max_length=100, blank=True, default="Coming Soon")
    status = models.CharField(max_length=100, default="In Production")

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="videos", db_index=True
    )
    category_name = models.CharField(max_length=100, blank=True, default="Film")
    duration = models.PositiveIntegerField(default=0, help_text="Video duration in seconds")

    is_upcoming = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_videos", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "videos"
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return f"Video({self.title})"

    def save(self, *args, **kwargs):
        if not self.slug:
            slug_base = slugify(self.title) or "video"
            slug = slug_base
            count = 1
            while Video.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{slug_base}-{count}"
                count += 1
            self.slug = slug

        # Auto extract YouTube ID and embed URL
        if self.youtube_url:
            v_id = extract_youtube_id(self.youtube_url)
            if v_id:
                self.youtube_video_id = v_id
                self.embed_url = build_youtube_embed_url(v_id)
                if not self.thumbnail_url:
                    self.thumbnail_url = f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg"

        super().save(*args, **kwargs)
