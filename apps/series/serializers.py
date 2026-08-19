"""
apps/series/serializers.py — Serializers for StorySeries and items
"""
from rest_framework import serializers
from apps.series.models import StorySeries, StorySeriesItem
from apps.stories.serializers import StoryListSerializer
from apps.writers.serializers import WriterProfileSerializer


class StorySeriesItemSerializer(serializers.ModelSerializer):
    story = StoryListSerializer(read_only=True)

    class Meta:
        model = StorySeriesItem
        fields = ["id", "story", "sequence_number", "item_status", "expected_publish_date"]


class StorySeriesSerializer(serializers.ModelSerializer):
    writer = WriterProfileSerializer(read_only=True)
    items = StorySeriesItemSerializer(many=True, read_only=True)

    class Meta:
        model = StorySeries
        fields = [
            "id", "title", "slug", "description", "writer", "status",
            "total_stories", "completed_stories", "is_featured",
            "items", "published_at", "created_at"
        ]


class SeriesReorderSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        required=True
    )
