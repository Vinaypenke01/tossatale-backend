"""
apps/videos/admin.py — Admin registration for Video model
"""
from django.contrib import admin
from apps.videos.models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "youtube_video_id", "category", "is_featured", "is_active", "published_at")
    list_filter = ("is_active", "is_featured", "category")
    search_fields = ("title", "youtube_video_id")
