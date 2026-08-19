"""
apps/videos/urls.py — Video & Upcoming Projects URL patterns
"""
from django.urls import path
from apps.videos.views import (
    PublicVideoListView,
    PublicVideoDetailView,
    AdminVideoListCreateView,
    AdminVideoDetailView,
)

public_urlpatterns = [
    path("videos/", PublicVideoListView.as_view(), name="public-video-list"),
    path("videos/<slug:slug>/", PublicVideoDetailView.as_view(), name="public-video-detail"),
]

admin_urlpatterns = [
    path("videos/", AdminVideoListCreateView.as_view(), name="admin-video-list-create"),
    path("videos/<slug:slug>/", AdminVideoDetailView.as_view(), name="admin-video-detail"),
]

urlpatterns = public_urlpatterns
