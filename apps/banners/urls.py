"""
apps/banners/urls.py — Banner URL patterns
"""
from django.urls import path
from apps.banners.views import PublicBannerListView, AdminBannerListCreateView

public_urlpatterns = [
    path("banners/", PublicBannerListView.as_view(), name="public-banner-list"),
]

admin_urlpatterns = [
    path("banners/", AdminBannerListCreateView.as_view(), name="admin-banner-list-create"),
]

urlpatterns = public_urlpatterns
