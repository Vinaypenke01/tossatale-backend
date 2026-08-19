"""
apps/engagements/models.py — Reader Engagement Models
Implements StoryLike, StoryBookmark, StoryShare, StoryView, and RecentlyRead per §15 and Phase 3 spec.
"""
import uuid
from django.conf import settings
from django.db import models
from common.constants import SharePlatform
from apps.stories.models import Story


class StoryLike(models.Model):
    """
    Tracks user likes on stories per §15.1. Unique per user + story.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="liked_stories",
        db_index=True,
    )
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="likes",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_likes"
        unique_together = ("user", "story")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "story"]),
        ]

    def __str__(self):
        return f"{self.user.email} likes {self.story.title}"


class StoryBookmark(models.Model):
    """
    Tracks bookmarks saved by readers per §15.2. Unique per user + story.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
        db_index=True,
    )
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="bookmarked_by",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_bookmarks"
        unique_together = ("user", "story")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "story"]),
        ]

    def __str__(self):
        return f"{self.user.email} bookmarked {self.story.title}"


class StoryShare(models.Model):
    """
    Tracks social share events for stories per §15.3.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="shares")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="story_shares",
    )
    platform = models.CharField(max_length=20, choices=SharePlatform.CHOICES, default=SharePlatform.OTHER)
    session_id = models.CharField(max_length=255, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_shares"
        ordering = ["-shared_at"]

    def __str__(self):
        return f"Share({self.story.title}, {self.platform})"


class StoryView(models.Model):
    """
    Tracks story views, reading duration, and unique view deduplication per §15.4.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="views", db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="story_views",
    )
    session_id = models.CharField(max_length=255, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    traffic_source = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=10, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reading_duration = models.PositiveIntegerField(default=0, help_text="Reading duration in seconds")
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_unique_view = models.BooleanField(default=True)

    class Meta:
        db_table = "story_views"
        ordering = ["-viewed_at"]
        indexes = [
            models.Index(fields=["story", "viewed_at"]),
            models.Index(fields=["user", "story"]),
        ]

    def __str__(self):
        return f"View({self.story.title}, unique={self.is_unique_view})"


class RecentlyRead(models.Model):
    """
    Tracks reading history and reading progress per §15.5.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recently_read",
        db_index=True,
    )
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="read_history")
    last_read_at = models.DateTimeField(auto_now=True, db_index=True)
    reading_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    completed = models.BooleanField(default=False)

    class Meta:
        db_table = "recently_read"
        unique_together = ("user", "story")
        ordering = ["-last_read_at"]
        indexes = [
            models.Index(fields=["user", "last_read_at"]),
        ]

    def __str__(self):
        return f"RecentlyRead({self.user.email}, {self.story.title})"
