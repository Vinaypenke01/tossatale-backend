"""
apps/analytics/models.py — Daily Analytics Aggregation Models per §16 & Phase 6 Spec
"""
import uuid
from django.db import models
from apps.stories.models import Story
from apps.writers.models import WriterProfile


class DailyStoryAnalytics(models.Model):
    """
    Daily aggregated metrics per story per §16.1.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="daily_analytics")
    date = models.DateField(db_index=True)

    views = models.IntegerField(default=0)
    unique_views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    unlikes = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    bookmarks = models.IntegerField(default=0)

    avg_reading_duration = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    country_breakdown = models.JSONField(default=dict, blank=True)
    device_breakdown = models.JSONField(default=dict, blank=True)
    traffic_source_breakdown = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "daily_story_analytics"
        unique_together = ("story", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"DailyStoryAnalytics({self.story.title}, date={self.date})"


class DailyWriterAnalytics(models.Model):
    """
    Daily aggregated metrics per writer per §16.2.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    writer = models.ForeignKey(WriterProfile, on_delete=models.CASCADE, related_name="daily_analytics")
    date = models.DateField(db_index=True)

    total_views = models.IntegerField(default=0)
    total_unique_views = models.IntegerField(default=0)
    total_likes = models.IntegerField(default=0)
    total_shares = models.IntegerField(default=0)

    stories_submitted = models.IntegerField(default=0)
    stories_published = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "daily_writer_analytics"
        unique_together = ("writer", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"DailyWriterAnalytics({self.writer.pen_name}, date={self.date})"


class DailyPlatformAnalytics(models.Model):
    """
    Daily aggregated platform-wide overview per §16.3.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(unique=True, db_index=True)

    total_page_views = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    new_writers = models.IntegerField(default=0)

    total_stories_published = models.IntegerField(default=0)
    total_likes = models.IntegerField(default=0)
    total_shares = models.IntegerField(default=0)
    newsletter_subscriptions = models.IntegerField(default=0)

    top_stories = models.JSONField(default=list, blank=True)
    top_categories = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "daily_platform_analytics"
        ordering = ["-date"]

    def __str__(self):
        return f"DailyPlatformAnalytics(date={self.date})"
