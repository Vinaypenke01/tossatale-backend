"""
apps/banners/admin.py — Admin registration for Banner model
"""
from django.contrib import admin
from apps.banners.models import Banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "banner_type", "is_active", "is_default", "display_order", "start_date", "end_date")
    list_filter = ("banner_type", "is_active", "is_default")
    search_fields = ("title", "subtitle")
