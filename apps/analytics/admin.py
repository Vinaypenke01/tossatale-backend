"""
apps/analytics/admin.py — Admin registration for analytics models
"""
from django.contrib import admin
from apps.analytics.models import DailyStoryAnalytics, DailyWriterAnalytics, DailyPlatformAnalytics


@admin.register(DailyStoryAnalytics)
class DailyStoryAnalyticsAdmin(admin.ModelAdmin):
    list_display = ("story", "date", "views", "unique_views", "likes", "shares")
    ordering = ("-date",)


@admin.register(DailyPlatformAnalytics)
class DailyPlatformAnalyticsAdmin(admin.ModelAdmin):
    list_display = ("date", "total_page_views", "unique_visitors", "total_stories_published")
    ordering = ("-date",)
