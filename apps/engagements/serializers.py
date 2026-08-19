"""
apps/engagements/serializers.py — Serializers for engagements and Reader Dashboard
"""
from rest_framework import serializers
from apps.engagements.models import StoryLike, StoryBookmark, StoryShare, StoryView, RecentlyRead
from apps.stories.serializers import StoryListSerializer


class StoryLikeSerializer(serializers.ModelSerializer):
    story = StoryListSerializer(read_only=True)

    class Meta:
        model = StoryLike
        fields = ["id", "story", "created_at"]


class StoryBookmarkSerializer(serializers.ModelSerializer):
    story = StoryListSerializer(read_only=True)

    class Meta:
        model = StoryBookmark
        fields = ["id", "story", "created_at"]


class StoryShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryShare
        fields = ["id", "platform", "session_id", "shared_at"]


class RecentlyReadSerializer(serializers.ModelSerializer):
    story = StoryListSerializer(read_only=True)

    class Meta:
        model = RecentlyRead
        fields = ["id", "story", "last_read_at", "reading_progress", "completed"]


class RecordViewSerializer(serializers.Serializer):
    reading_duration = serializers.IntegerField(required=False, default=0)
    completion_percentage = serializers.FloatField(required=False, default=0.0)
    referrer = serializers.CharField(required=False, allow_blank=True, default="")
    session_id = serializers.CharField(required=False, allow_blank=True, default="")


class RecordShareSerializer(serializers.Serializer):
    platform = serializers.CharField(required=True)
    session_id = serializers.CharField(required=False, allow_blank=True, default="")
