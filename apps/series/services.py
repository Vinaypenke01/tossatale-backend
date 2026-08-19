"""
apps/series/services.py — StorySeriesService
Service layer for story series management and atomic reordering per §23.
"""
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction

from common.constants import SeriesStatus
from common.exceptions import (
    ServiceValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from apps.series.models import StorySeries, StorySeriesItem
from apps.stories.models import Story


class StorySeriesService:

    @classmethod
    def generate_unique_slug(cls, title: str, instance_id=None) -> str:
        base_slug = slugify(title) or "series"
        slug = base_slug
        counter = 1
        qs = StorySeries.objects.filter(slug=slug)
        if instance_id:
            qs = qs.exclude(id=instance_id)

        while qs.exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
            qs = qs.exclude(id=instance_id)
        return slug

    @classmethod
    def create_series(cls, writer, user, data: dict) -> StorySeries:
        title = data.get("title", "").strip()
        if not title:
            raise ServiceValidationError("Series title is required.")

        slug = cls.generate_unique_slug(title)
        series = StorySeries.objects.create(
            writer=writer,
            created_by=user,
            title=title,
            slug=slug,
            description=data.get("description", "").strip(),
            status=SeriesStatus.DRAFT,
        )
        return series

    @classmethod
    def update_series(cls, series: StorySeries, data: dict) -> StorySeries:
        if "title" in data:
            title = data["title"].strip()
            if not title:
                raise ServiceValidationError("Series title cannot be empty.")
            series.title = title
            series.slug = cls.generate_unique_slug(title, instance_id=series.id)

        if "description" in data:
            series.description = data["description"].strip()

        if "is_featured" in data:
            series.is_featured = data["is_featured"]

        series.save()
        return series

    @classmethod
    def publish_series(cls, series: StorySeries) -> StorySeries:
        series.status = SeriesStatus.PUBLISHED
        series.published_at = timezone.now()
        series.save(update_fields=["status", "published_at", "updated_at"])
        return series

    @classmethod
    @transaction.atomic
    def assign_story(cls, series: StorySeries, story: Story, sequence_number: int = None) -> StorySeriesItem:
        """Assigns a story to a series, ensuring no duplicates."""
        if StorySeriesItem.objects.filter(series=series, story=story).exists():
            raise DuplicateResourceError("Story is already part of this series.")

        if sequence_number is None:
            max_seq = StorySeriesItem.objects.filter(series=series).count()
            sequence_number = max_seq + 1

        item = StorySeriesItem.objects.create(
            series=series, story=story, sequence_number=sequence_number
        )

        series.total_stories = StorySeriesItem.objects.filter(series=series).count()
        series.save(update_fields=["total_stories", "updated_at"])

        return item

    @classmethod
    @transaction.atomic
    def remove_story(cls, series: StorySeries, story: Story):
        """Removes a story from a series and fixes sequence gaps."""
        try:
            item = StorySeriesItem.objects.get(series=series, story=story)
        except StorySeriesItem.DoesNotExist:
            raise ResourceNotFoundError("Story is not in this series.")

        item.delete()

        # Re-sequence remaining items
        items = StorySeriesItem.objects.filter(series=series).order_by("sequence_number")
        for idx, item_obj in enumerate(items, start=1):
            if item_obj.sequence_number != idx:
                item_obj.sequence_number = idx
                item_obj.save(update_fields=["sequence_number"])

        series.total_stories = items.count()
        series.save(update_fields=["total_stories", "updated_at"])

    @classmethod
    @transaction.atomic
    def reorder_stories(cls, series: StorySeries, items_data: list):
        """
        Reorders story sequence numbers atomically per §23.
        items_data: [{"story_id": "uuid", "sequence_number": 1}, ...]
        """
        if not items_data:
            raise ServiceValidationError("No items provided for reordering.")

        sequences = [item["sequence_number"] for item in items_data]
        if len(sequences) != len(set(sequences)):
            raise ServiceValidationError("Duplicate sequence numbers detected.")

        # Temporarily offset sequence numbers to avoid unique constraint collisions during swap
        for item in items_data:
            StorySeriesItem.objects.filter(series=series, story_id=item["story_id"]).update(
                sequence_number=item["sequence_number"] + 100000
            )

        # Apply final sequence numbers
        for item in items_data:
            StorySeriesItem.objects.filter(series=series, story_id=item["story_id"]).update(
                sequence_number=item["sequence_number"]
            )
