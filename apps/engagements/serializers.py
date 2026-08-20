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
    reading_progress = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = StoryBookmark
        fields = ["id", "story", "reading_progress", "completed", "is_liked", "created_at"]

    def get_reading_progress(self, obj):
        recent = RecentlyRead.objects.filter(user=obj.user, story=obj.story).first()
        return float(recent.reading_progress) if recent else 0.0

    def get_completed(self, obj):
        recent = RecentlyRead.objects.filter(user=obj.user, story=obj.story).first()
        return bool(recent.completed) if recent else False

    def get_is_liked(self, obj):
        return StoryLike.objects.filter(user=obj.user, story=obj.story).exists()


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
