"""
apps/categories — Serializers, Services, Views, URLs
"""
from rest_framework import serializers
from apps.categories.models import Category, Tag


class CategorySerializer(serializers.ModelSerializer):
    stories_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description", "category_type",
            "icon", "display_order", "is_featured", "is_active",
            "seo_title", "seo_description", "created_at", "stories_count",
        ]
        read_only_fields = ["id", "slug", "created_at"]

    def get_stories_count(self, obj):
        return obj.stories.filter(status="PUBLISHED").count()


class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "name", "description", "category_type",
            "icon", "display_order", "is_featured", "is_active",
            "seo_title", "seo_description",
        ]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "description", "usage_count", "is_active", "created_at"]
        read_only_fields = ["id", "slug", "usage_count", "created_at"]


class TagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["name", "description", "is_active"]
