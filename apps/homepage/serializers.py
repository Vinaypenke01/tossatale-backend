"""
apps/homepage/serializers.py — Lightweight serializers for public homepage cards
Oromits heavy 'content', 'plain_text_content', and 'reviews' history to keep the stitched
homepage payload lean (< 50 KB) and fast to transfer on production (PythonAnywhere / Railway).
"""
from rest_framework import serializers
from apps.stories.models import Story
from apps.blogs.models import Blog
from apps.writers.serializers import WriterProfileSerializer
from apps.categories.serializers import CategorySerializer, TagSerializer


class HomepageStorySerializer(serializers.ModelSerializer):
    writer = WriterProfileSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id",
            "writer",
            "title",
            "slug",
            "subtitle",
            "category",
            "tags",
            "status",
            "is_featured",
            "estimated_reading_time",
            "views_count",
            "likes_count",
            "bookmarks_count",
            "is_liked",
            "is_bookmarked",
            "published_at",
            "created_at",
        ]

    def get_tags(self, obj):
        tags = [st.tag for st in obj.story_tags.all()]
        return TagSerializer(tags, many=True).data

    def get_is_liked(self, obj):
        liked_ids = self.context.get("liked_ids")
        if liked_ids is not None:
            return obj.id in liked_ids
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_is_bookmarked(self, obj):
        bookmarked_ids = self.context.get("bookmarked_ids")
        if bookmarked_ids is not None:
            return obj.id in bookmarked_ids
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            return obj.bookmarked_by.filter(user=request.user).exists()
        return False


class HomepageBlogSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = [
            "id",
            "title",
            "slug",
            "subtitle",
            "cover_image",
            "category",
            "is_featured",
            "reading_time",
            "views_count",
            "likes_count",
            "published_at",
        ]

    def get_cover_image(self, obj):
        raw = obj.cover_image or ""
        # If it's a URL or reasonable data URI, return it directly.
        # If it's a gigantic uncompressed base64 string (> 150KB), return empty or fallback
        # so it doesn't inflate the entire homepage API into multiple megabytes.
        if len(raw) > 150000 and raw.startswith("data:image"):
            return ""
        return raw
