"""
apps/stories/serializers.py — Serializers for Story Pipeline
Implements serializers for story creation, editing, detail views, admin management, and revisions per Phase 2 spec.
"""
from rest_framework import serializers
from apps.stories.models import Story, StoryTag, StoryRevision, StoryReview, StoryChapter
from apps.categories.serializers import CategorySerializer, TagSerializer
from apps.categories.models import Category, Tag
from apps.writers.serializers import WriterProfileSerializer
from common.constants import StoryStatus, ReviewDecision, SeriesStatusType


class StoryChapterSerializer(serializers.ModelSerializer):
    story_id = serializers.UUIDField(source="story.id", read_only=True)

    class Meta:
        model = StoryChapter
        fields = [
            "id", "story_id", "order", "title", "content", "plain_text_content",
            "estimated_reading_time", "word_count", "status", "published_at",
            "rejection_feedback", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "story_id", "plain_text_content", "estimated_reading_time", "word_count", "created_at", "updated_at"]


class StoryChapterCreateUpdateSerializer(serializers.Serializer):
    order = serializers.IntegerField(required=False, min_value=1)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    content = serializers.CharField(required=False, allow_blank=True, default="")
    estimated_reading_time = serializers.IntegerField(required=False, min_value=0)
    status = serializers.ChoiceField(choices=StoryStatus.CHOICES, required=False)
    rejection_feedback = serializers.CharField(required=False, allow_blank=True)


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
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = StoryReview
        fields = [
            "id", "reviewer", "reviewer_email", "reviewer_name", "decision",
            "feedback", "internal_notes", "reviewed_at"
        ]
        read_only_fields = fields

    def get_reviewer_name(self, obj):
        if obj.reviewer:
            return (
                getattr(obj.reviewer, "display_name", "")
                or getattr(obj.reviewer, "first_name", "")
                or obj.reviewer.email.split("@")[0]
            )
        return "Editorial Team"


class StoryCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    subtitle = serializers.CharField(max_length=500, required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True, default="")
    is_multi_chapter = serializers.BooleanField(required=False, default=False)
    series_status = serializers.ChoiceField(choices=SeriesStatusType.CHOICES, required=False, default=SeriesStatusType.ONGOING)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    seo_title = serializers.CharField(max_length=70, required=False, allow_blank=True)
    seo_description = serializers.CharField(max_length=160, required=False, allow_blank=True)
    reading_time = serializers.IntegerField(required=False, allow_null=True)
    estimated_reading_time = serializers.IntegerField(required=False, allow_null=True)
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    allow_comments = serializers.BooleanField(default=True)

    def validate_category_id(self, value):
        if value:
            category = Category.objects.filter(id=value).first()
            if not category:
                raise serializers.ValidationError("Category does not exist.")
            if not category.is_active:
                raise serializers.ValidationError("Selected category is inactive.")
        return value

    def validate_tag_ids(self, value):
        valid_count = Tag.objects.filter(id__in=value).count()
        if valid_count != len(set(value)):
            raise serializers.ValidationError("One or more tag IDs are invalid.")
        return value


class StoryUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    subtitle = serializers.CharField(max_length=500, required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    is_multi_chapter = serializers.BooleanField(required=False)
    series_status = serializers.ChoiceField(choices=SeriesStatusType.CHOICES, required=False)
    category_id = serializers.UUIDField(required=False, allow_null=True)
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
        if value:
            category = Category.objects.filter(id=value).first()
            if not category:
                raise serializers.ValidationError("Category does not exist.")
            if not category.is_active:
                raise serializers.ValidationError("Selected category is inactive.")
        return value


class StoryListSerializer(serializers.ModelSerializer):
    writer = WriterProfileSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    rejection_count = serializers.SerializerMethodField()
    chapter_count = serializers.SerializerMethodField()
    reviews = StoryReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Story
        fields = [
            "id", "writer", "title", "slug", "subtitle", "content", "plain_text_content",
            "category", "tags", "status", "moderation_status", "rejection_feedback", "rejection_count",
            "is_multi_chapter", "series_status", "chapter_count", "reviews", "is_featured", "estimated_reading_time", "word_count",
            "views_count", "likes_count", "bookmarks_count", "is_liked",
            "is_bookmarked", "published_at", "submitted_at", "reviewed_at",
            "created_at", "updated_at"
        ]

    def get_chapter_count(self, obj):
        return obj.chapters.count() if obj.is_multi_chapter else 0

    def get_rejection_count(self, obj):
        cnt = sum(1 for r in obj.reviews.all() if r.decision == ReviewDecision.REJECTED)
        if cnt == 0 and obj.status == StoryStatus.REJECTED and obj.rejection_feedback:
            return 1
        return cnt

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


class StoryDetailSerializer(serializers.ModelSerializer):
    writer = WriterProfileSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    rejection_count = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()
    chapter_count = serializers.SerializerMethodField()
    reviews = StoryReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Story
        fields = [
            "id", "writer", "title", "slug", "subtitle", "content", "plain_text_content",
            "category", "tags", "seo_title", "seo_description", "status",
            "moderation_status", "rejection_feedback", "rejection_count",
            "is_multi_chapter", "series_status", "chapter_count", "chapters", "is_featured",
            "allow_comments", "estimated_reading_time", "word_count",
            "views_count", "likes_count", "shares_count", "bookmarks_count",
            "is_liked", "is_bookmarked", "trending_score", "submitted_at",
            "reviewed_at", "approved_at", "published_at", "scheduled_publish_at",
            "reviews", "created_at", "updated_at"
        ]

    def get_chapters(self, obj):
        if not obj.is_multi_chapter:
            return []
        from apps.stories.services import ChapterService
        ChapterService.normalize_chapter_orders(obj)
        request = self.context.get("request")
        is_privileged = (
            request and hasattr(request, "user") and request.user.is_authenticated
            and (
                getattr(request.user, "role", "") == "ADMIN"
                or getattr(request.user, "is_staff", False)
                or (getattr(obj, "writer", None) and getattr(obj.writer, "user", None) == request.user)
            )
        )
        if is_privileged:
            qs = obj.chapters.all().order_by("order", "created_at")
        else:
            published_qs = obj.chapters.filter(status=StoryStatus.PUBLISHED).order_by("order", "created_at")
            if published_qs.exists():
                qs = published_qs
            else:
                qs = obj.chapters.exclude(status=StoryStatus.REJECTED).order_by("order", "created_at")
        return StoryChapterSerializer(qs, many=True).data

    def get_chapter_count(self, obj):
        return obj.chapters.count() if obj.is_multi_chapter else 0

    def get_rejection_count(self, obj):
        cnt = sum(1 for r in obj.reviews.all() if r.decision == ReviewDecision.REJECTED)
        if cnt == 0 and obj.status == StoryStatus.REJECTED and obj.rejection_feedback:
            return 1
        return cnt

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


class AdminStorySerializer(serializers.ModelSerializer):
    writer = WriterProfileSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)
    reviews = StoryReviewSerializer(many=True, read_only=True)
    rejection_count = serializers.SerializerMethodField()
    chapters = StoryChapterSerializer(many=True, read_only=True)
    chapter_count = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id", "writer", "title", "slug", "subtitle", "content",
            "plain_text_content", "category", "tags", "seo_title", "seo_description",
            "status", "moderation_status", "rejection_feedback", "rejection_count",
            "is_multi_chapter", "series_status", "chapter_count", "chapters",
            "submitted_at", "reviewed_at", "reviewed_by", "reviewed_by_email",
            "approved_at", "published_at", "scheduled_publish_at", "archived_at",
            "is_featured", "allow_comments", "estimated_reading_time", "word_count",
            "views_count", "likes_count", "unauthenticated_like_attempts",
            "shares_count", "bookmarks_count", "trending_score", "reviews",
            "created_at", "updated_at"
        ]

    def get_chapter_count(self, obj):
        return obj.chapters.count() if obj.is_multi_chapter else 0

    def get_rejection_count(self, obj):
        cnt = sum(1 for r in obj.reviews.all() if r.decision == ReviewDecision.REJECTED)
        if cnt == 0 and obj.status == StoryStatus.REJECTED and obj.rejection_feedback:
            return 1
        return cnt

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
