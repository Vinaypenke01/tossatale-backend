"""
apps/settings_config/admin.py — Admin registration for SiteSettings model
"""
from django.contrib import admin
from apps.settings_config.models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("site_name", "contact_email", "maintenance_mode", "updated_at")
