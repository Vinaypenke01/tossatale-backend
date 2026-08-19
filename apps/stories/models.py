"""
apps/stories — Story, StoryTag, StoryRevision, StoryReview Models
Implements the core story engine per §11 and Phase 2 spec.
"""
import uuid
from django.conf import settings
from django.db import models
from common.constants import StoryStatus, ModerationStatus, ReviewDecision
from apps.writers.models import WriterProfile
from apps.categories.models import Category, Tag


class Story(models.Model):
    """
    Core Story model representing rich text prose stories written by writers.
    Follows §11.1 schema. Writers produce text-only stories.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    writer = models.ForeignKey(
        WriterProfile,
        on_delete=models.CASCADE,
        related_name="stories",
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_stories",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    subtitle = models.CharField(max_length=500, blank=True, null=True)

    # Content
    content = models.TextField(help_text="Rich text prose content (text-only for writers per §2)")
    plain_text_content = models.TextField(
        blank=True,
        help_text="Plain text content used for search indexing and reading time calculation",
    )

    # Categorization & SEO
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="stories",
        db_index=True,
    )
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)

    # Workflow & Moderation state
    status = models.CharField(
        max_length=20,
        choices=StoryStatus.CHOICES,
        default=StoryStatus.DRAFT,
        db_index=True,
    )
    moderation_status = models.CharField(
        max_length=20,
        choices=ModerationStatus.CHOICES,
        default=ModerationStatus.NOT_REVIEWED,
    )
    rejection_feedback = models.TextField(blank=True)

    # Timestamps & Reviewer
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_stories",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    scheduled_publish_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    # Flags & Metrics
    is_featured = models.BooleanField(default=False, db_index=True)
    allow_comments = models.BooleanField(default=True)
    estimated_reading_time = models.PositiveIntegerField(default=0, help_text="Reading time in minutes")
    word_count = models.PositiveIntegerField(default=0)

    # Engagement counters
    views_count = models.BigIntegerField(default=0)
    likes_count = models.BigIntegerField(default=0)
    shares_count = models.BigIntegerField(default=0)
    bookmarks_count = models.BigIntegerField(default=0)

    # Dynamic ranking
    trending_score = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stories"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["published_at"]),
            models.Index(fields=["writer"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["trending_score"]),
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["writer", "status"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.status}]"


class StoryTag(models.Model):
    """
    Junction table for Story <-> Tag relationship per §11.2.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="story_tags")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="tagged_stories")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_tags"
        unique_together = ("story", "tag")

    def __str__(self):
        return f"{self.story.title} - {self.tag.name}"


class StoryRevision(models.Model):
    """
    Stores snapshots of story versions for revision history and rollback per §11.3.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="revisions")
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=500, blank=True, null=True)
    content = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    change_summary = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_revisions"
        ordering = ["-version_number"]
        unique_together = ("story", "version_number")

    def __str__(self):
        return f"{self.story.title} v{self.version_number}"


class StoryReview(models.Model):
    """
    Tracks admin reviews, approvals, and rejection feedback history per §11.4.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conducted_reviews")
    decision = models.CharField(max_length=20, choices=ReviewDecision.CHOICES)
    feedback = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_reviews"
        ordering = ["-reviewed_at"]

    def __str__(self):
        return f"Review({self.story.title}, {self.decision})"
