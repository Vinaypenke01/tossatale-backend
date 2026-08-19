"""
apps/homepage/admin.py — Admin registration for HomepageSection model
"""
from django.contrib import admin
from apps.homepage.models import HomepageSection


@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = ("section_key", "is_enabled", "display_order", "updated_at")
    list_filter = ("is_enabled",)
    ordering = ("display_order",)
