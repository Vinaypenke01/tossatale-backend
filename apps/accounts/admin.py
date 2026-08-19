"""
apps/accounts — Django Admin Registration
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.accounts.models import User, UserSession, NotificationPreference


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "get_full_name", "role", "is_active", "is_email_verified", "created_at"]
    list_filter = ["role", "is_active", "is_email_verified", "auth_provider"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "display_name", "profile_photo")}),
        ("Role & Auth", {"fields": ("role", "auth_provider", "google_id")}),
        ("Status", {"fields": ("is_active", "is_email_verified", "is_staff", "is_superuser")}),
        ("Timestamps", {"fields": ("last_login", "last_activity_at", "created_at")}),
    )
    readonly_fields = ["last_login", "last_activity_at", "created_at"]
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "device_name", "browser", "ip_address", "is_revoked", "created_at"]
    list_filter = ["is_revoked"]
    search_fields = ["user__email"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "email_notifications", "story_approval_notifications"]
    search_fields = ["user__email"]
