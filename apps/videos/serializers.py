"""
apps/videos/serializers.py — Video & Upcoming Projects Serializers
"""
from rest_framework import serializers
from apps.videos.models import Video
from apps.categories.serializers import CategorySerializer


class VideoSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Video
        fields = [
            "id", "title", "slug", "youtube_url", "youtube_video_id", "embed_url",
            "thumbnail_url", "cover_image", "description", "editorial_note",
            "director", "expected_release", "status", "category", "category_name",
            "duration", "is_upcoming", "is_featured", "is_active", "published_at", "created_at"
        ]


class VideoCreateUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    youtube_url = serializers.CharField(required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    editorial_note = serializers.CharField(required=False, allow_blank=True, default="")
    director = serializers.CharField(required=False, allow_blank=True, default="Tossatale Studio")
    expected_release = serializers.CharField(required=False, allow_blank=True, default="Coming Soon")
    status = serializers.CharField(required=False, allow_blank=True, default="In Production")
    category_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    category_name = serializers.CharField(required=False, allow_blank=True, default="Film")
    duration = serializers.IntegerField(required=False, default=0)
    thumbnail_url = serializers.CharField(required=False, allow_blank=True, default="")
    cover_image = serializers.CharField(required=False, allow_blank=True, default="")
    is_upcoming = serializers.BooleanField(required=False, default=False)
    is_featured = serializers.BooleanField(required=False, default=False)
