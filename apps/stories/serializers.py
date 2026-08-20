"""
apps/stories/serializers.py — Serializers for Story Pipeline
Implements serializers for story creation, editing, detail views, admin management, and revisions per Phase 2 spec.
"""
from rest_framework import serializers
from apps.stories.models import Story, StoryTag, StoryRevision, StoryReview
from apps.categories.serializers import CategorySerializer, TagSerializer
from apps.categories.models import Category, Tag
from apps.writers.serializers import WriterProfileSerializer


class StoryTagSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)

    class Meta:
        model = StoryTag
        fields = ["id", "tag", "created_at"]


class StoryRevisionSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = StoryRevision
        fields = [
            "id", "version_number", "title", "subtitle", "content",
            "category", "seo_title", "seo_description", "edited_by",
            "change_summary", "created_at"
        ]
        read_only_fields = fields


class StoryReviewSerializer(serializers.ModelSerializer):
    reviewer_email = serializers.EmailField(source="reviewer.email", read_only=True)

    class Meta:
        model = StoryReview
        fields = [
            "id", "reviewer", "reviewer_email", "decision",
            "feedback", "internal_notes", "reviewed_at"
        ]
        read_only_fields = fields


class StoryCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    subtitle = serializers.CharField(max_length=500, required=False, allow_blank=True)
    content = serializers.CharField(min_length=100, help_text="Story content must be at least 100 characters long.")
    category_id = serializers.UUIDField()
    seo_title = serializers.CharField(max_length=70, required=False, allow_blank=True)
    seo_description = serializers.CharField(max_length=160, required=False, allow_blank=True)
    reading_time = serializers.IntegerField(required=False, allow_null=True)
    estimated_reading_time = serializers.IntegerField(required=False, allow_null=True)
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    allow_comments = serializers.BooleanField(default=True)

    def validate_category_id(self, value):
        try:
            category = Category.objects.get(id=value)
            if not category.is_active:
                raise serializers.ValidationError("Selected category is inactive.")
        except Category.DoesNotExist:
            raise serializers.ValidationError("Category does not exist.")
        return value

    def validate_tag_ids(self, value):
        valid_count = Tag.objects.filter(id__in=value).count()
        if valid_count != len(set(value)):
            raise serializers.ValidationError("One or more tag IDs are invalid.")
        return value


class StoryUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    subtitle = serializers.CharField(max_length=500, required=False, allow_blank=True)
    content = serializers.CharField(min_length=100, required=False)
    category_id = serializers.UUIDField(required=False)
    seo_title = serializers.CharField(max_length=70, required=False, allow_blank=True)
    seo_description = serializers.CharField(max_length=160, required=False, allow_blank=True)
    reading_time = serializers.IntegerField(required=False, allow_null=True)
    estimated_reading_time = serializers.IntegerField(required=False, allow_null=True)
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False
    )
    allow_comments = serializers.BooleanField(required=False)
    change_summary = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_category_id(self, value):
        try:
            category = Category.objects.get(id=value)
            if not category.is_active:
                raise serializers.ValidationError("Selected category is inactive.")
        except Category.DoesNotExist:
            raise serializers.ValidationError("Category does not exist.")
        return value


class StoryListSerializer(serializers.ModelSerializer):
    writer = WriterProfileSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id", "writer", "title", "slug", "subtitle", "category", "tags",
            "status", "is_featured", "estimated_reading_time", "word_count",
            "views_count", "likes_count", "bookmarks_count", "is_liked",
            "is_bookmarked", "published_at", "created_at"
        ]

    def get_tags(self, obj):
        tags = [st.tag for st in obj.story_tags.all()]
        return TagSerializer(tags, many=True).data

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            from apps.engagements.models import StoryLike
            return StoryLike.objects.filter(story=obj, user=request.user).exists()
        return False

    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            from apps.engagements.models import StoryBookmark
            return StoryBookmark.objects.filter(story=obj, user=request.user).exists()
        return False


class StoryDetailSerializer(serializers.ModelSerializer):
    writer = WriterProfileSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id", "writer", "title", "slug", "subtitle", "content", "plain_text_content",
            "category", "tags", "seo_title", "seo_description", "status",
            "moderation_status", "rejection_feedback", "is_featured",
            "allow_comments", "estimated_reading_time", "word_count",
            "views_count", "likes_count", "shares_count", "bookmarks_count",
            "is_liked", "is_bookmarked",
            "trending_score", "submitted_at", "reviewed_at", "approved_at",
            "published_at", "scheduled_publish_at", "created_at", "updated_at"
        ]

    def get_tags(self, obj):
        tags = [st.tag for st in obj.story_tags.all()]
        return TagSerializer(tags, many=True).data

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            from apps.engagements.models import StoryLike
            return StoryLike.objects.filter(story=obj, user=request.user).exists()
        return False

    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            from apps.engagements.models import StoryBookmark
            return StoryBookmark.objects.filter(story=obj, user=request.user).exists()
        return False


class AdminStorySerializer(serializers.ModelSerializer):
    writer = WriterProfileSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)
    reviews = StoryReviewSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id", "writer", "created_by", "title", "slug", "subtitle", "content",
            "plain_text_content", "category", "tags", "seo_title", "seo_description",
            "status", "moderation_status", "rejection_feedback", "submitted_at",
            "reviewed_at", "reviewed_by", "reviewed_by_email", "approved_at",
            "published_at", "scheduled_publish_at", "archived_at", "is_featured",
            "allow_comments", "estimated_reading_time", "word_count", "views_count",
            "likes_count", "unauthenticated_like_attempts", "shares_count", "bookmarks_count", "trending_score",
            "reviews", "created_at", "updated_at"
        ]

    def get_tags(self, obj):
        tags = [st.tag for st in obj.story_tags.all()]
        return TagSerializer(tags, many=True).data


class StorySubmitSerializer(serializers.Serializer):
    """Empty body serializer for submission action."""
    pass


class StoryRejectSerializer(serializers.Serializer):
    rejection_feedback = serializers.CharField(
        min_length=5,
        required=True,
        help_text="Reason for rejection must be provided to the writer."
    )
    internal_notes = serializers.CharField(required=False, allow_blank=True)


class StoryScheduleSerializer(serializers.Serializer):
    scheduled_publish_at = serializers.DateTimeField(required=True)
