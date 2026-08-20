from django.urls import path
from apps.settings_config.views import (
    PublicSettingsView,
    AdminSettingsView,
    PublicFAQListView,
    AdminFAQListCreateView,
    AdminFAQDetailView,
)

public_urlpatterns = [
    path("settings/", PublicSettingsView.as_view(), name="public-settings"),
    path("faqs/", PublicFAQListView.as_view(), name="public-faqs"),
]

admin_urlpatterns = [
    path("settings/", AdminSettingsView.as_view(), name="admin-settings"),
    path("faqs/", AdminFAQListCreateView.as_view(), name="admin-faqs-list"),
    path("faqs/<int:pk>/", AdminFAQDetailView.as_view(), name="admin-faqs-detail"),
]

urlpatterns = public_urlpatterns
