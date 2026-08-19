"""
apps/settings_config/urls.py — Settings URL patterns
"""
from django.urls import path
from apps.settings_config.views import PublicSettingsView, AdminSettingsView

public_urlpatterns = [
    path("settings/", PublicSettingsView.as_view(), name="public-settings"),
]

admin_urlpatterns = [
    path("settings/", AdminSettingsView.as_view(), name="admin-settings"),
]

urlpatterns = public_urlpatterns
