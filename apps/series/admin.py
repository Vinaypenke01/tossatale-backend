"""
apps/series/admin.py — Admin registration for Series models
"""
from django.contrib import admin
from apps.series.models import StorySeries, StorySeriesItem


class StorySeriesItemInline(admin.TabularInline):
    model = StorySeriesItem
    extra = 1
    ordering = ("sequence_number",)


@admin.register(StorySeries)
class StorySeriesAdmin(admin.ModelAdmin):
    list_display = ("title", "writer", "status", "total_stories", "is_featured", "created_at")
    list_filter = ("status", "is_featured")
    search_fields = ("title", "writer__pen_name")
    inlines = [StorySeriesItemInline]
