"""
apps/newsletters/admin.py — Admin registration for NewsletterSubscription model
"""
from django.contrib import admin
from apps.newsletters.models import NewsletterSubscription


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "is_verified", "verified_at", "unsubscribed_at", "created_at")
    list_filter = ("is_verified",)
    search_fields = ("email",)
