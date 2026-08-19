"""User (Reader) URL routes — /api/v1/user/"""
from django.urls import path
from apps.accounts.views import (
    UserProfileView,
    NotificationPreferenceView,
)

urlpatterns = [
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("notification-preferences/", NotificationPreferenceView.as_view(), name="user-notification-prefs"),
]
