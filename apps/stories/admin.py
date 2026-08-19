"""
apps/stories/admin.py — Django Admin registration for Story models
"""
from django.contrib import admin
from apps.stories.models import Story, StoryTag, StoryRevision, StoryReview


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("title", "writer", "category", "status", "moderation_status", "is_featured", "published_at", "created_at")
    list_filter = ("status", "moderation_status", "is_featured", "category")
    search_fields = ("title", "writer__pen_name", "writer__user__email")
    readonly_fields = ("id", "slug", "word_count", "estimated_reading_time", "created_at", "updated_at")


@admin.register(StoryRevision)
class StoryRevisionAdmin(admin.ModelAdmin):
    list_display = ("story", "version_number", "edited_by", "created_at")
    readonly_fields = ("id", "created_at")


@admin.register(StoryReview)
class StoryReviewAdmin(admin.ModelAdmin):
    list_display = ("story", "reviewer", "decision", "reviewed_at")
    list_filter = ("decision",)
    readonly_fields = ("id", "reviewed_at")
