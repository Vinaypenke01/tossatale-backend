"""
apps/engagements/admin.py — Admin registration for engagement models
"""
from django.contrib import admin
from apps.engagements.models import StoryLike, StoryBookmark, StoryShare, StoryView, RecentlyRead


@admin.register(StoryLike)
class StoryLikeAdmin(admin.ModelAdmin):
    list_display = ("user", "story", "created_at")
    search_fields = ("user__email", "story__title")


@admin.register(StoryBookmark)
class StoryBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "story", "created_at")
    search_fields = ("user__email", "story__title")


@admin.register(StoryShare)
class StoryShareAdmin(admin.ModelAdmin):
    list_display = ("story", "platform", "user", "shared_at")
    list_filter = ("platform",)


@admin.register(StoryView)
class StoryViewAdmin(admin.ModelAdmin):
    list_display = ("story", "user", "is_unique_view", "reading_duration", "completion_percentage", "viewed_at")
    list_filter = ("is_unique_view",)


@admin.register(RecentlyRead)
class RecentlyReadAdmin(admin.ModelAdmin):
    list_display = ("user", "story", "reading_progress", "completed", "last_read_at")
    list_filter = ("completed",)
