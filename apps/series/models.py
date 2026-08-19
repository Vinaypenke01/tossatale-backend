"""
apps/series/models.py — Story Series Models per §12 & Phase 4 Spec
"""
import uuid
from django.conf import settings
from django.db import models
from common.constants import SeriesStatus, SeriesItemStatus
from apps.writers.models import WriterProfile
from apps.stories.models import Story


class StorySeries(models.Model):
    """
    Story Series model representing grouped stories in sequence per §12.1.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    writer = models.ForeignKey(
        WriterProfile, on_delete=models.CASCADE, related_name="series", db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_series"
    )
    status = models.CharField(
        max_length=20, choices=SeriesStatus.CHOICES, default=SeriesStatus.DRAFT, db_index=True
    )
    total_stories = models.PositiveIntegerField(default=0)
    completed_stories = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "story_series"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Series({self.title}, {self.writer.pen_name})"


class StorySeriesItem(models.Model):
    """
    Junction model mapping a Story to a Series with sequence order per §12.2.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    series = models.ForeignKey(StorySeries, on_delete=models.CASCADE, related_name="items")
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="series_items")
    sequence_number = models.PositiveIntegerField()
    item_status = models.CharField(
        max_length=20, choices=SeriesItemStatus.CHOICES, default=SeriesItemStatus.UPCOMING
    )
    expected_publish_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "story_series_items"
        ordering = ["sequence_number"]
        unique_together = (
            ("series", "story"),
            ("series", "sequence_number"),
        )

    def __str__(self):
        return f"#{self.sequence_number} {self.story.title} in {self.series.title}"
