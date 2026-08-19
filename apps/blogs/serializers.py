"""
apps/blogs/serializers.py — Blog serializers
"""
from rest_framework import serializers
from apps.blogs.models import Blog, BlogTag
from apps.categories.serializers import CategorySerializer, TagSerializer


class BlogSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Blog
        fields = [
            "id", "author", "title", "slug", "subtitle", "content", "plain_text_content",
            "cover_image", "featured_image", "category", "seo_title", "seo_description",
            "status", "is_featured", "reading_time", "word_count", "views_count",
            "likes_count", "published_at", "created_at", "updated_at"
        ]


class BlogCreateUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    subtitle = serializers.CharField(max_length=500, required=False, allow_blank=True)
    excerpt = serializers.CharField(max_length=500, required=False, allow_blank=True)
    content = serializers.CharField()
    cover_image = serializers.CharField(required=False, allow_blank=True)
    featured_image = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    tags = serializers.CharField(required=False, allow_blank=True)
    tag = serializers.CharField(max_length=100, required=False, allow_blank=True)
    reading_time = serializers.IntegerField(required=False, allow_null=True)
    seo_title = serializers.CharField(max_length=70, required=False, allow_blank=True)
    seo_description = serializers.CharField(max_length=160, required=False, allow_blank=True)
    is_featured = serializers.BooleanField(default=False)
