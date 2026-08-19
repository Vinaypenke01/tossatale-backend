"""
apps/newsletters/urls.py — Newsletter URL patterns
"""
from django.urls import path
from apps.newsletters.views import (
    SubscribeNewsletterView,
    VerifyNewsletterView,
    UnsubscribeNewsletterView,
    AdminExportNewsletterCSVView,
)

public_urlpatterns = [
    path("newsletter/subscribe/", SubscribeNewsletterView.as_view(), name="public-newsletter-subscribe"),
    path("newsletter/verify/", VerifyNewsletterView.as_view(), name="public-newsletter-verify"),
    path("newsletter/unsubscribe/", UnsubscribeNewsletterView.as_view(), name="public-newsletter-unsubscribe"),
]

admin_urlpatterns = [
    path("newsletter/export/", AdminExportNewsletterCSVView.as_view(), name="admin-newsletter-export"),
]

urlpatterns = public_urlpatterns
