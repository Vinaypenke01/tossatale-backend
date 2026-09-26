"""
apps/blogs/urls.py — Blog URL patterns
"""
from django.urls import path
from apps.blogs.views import (
    PublicBlogListView,
    PublicBlogDetailView,
    PublicBlogLikeView,
    PublicBlogViewView,
    AdminBlogListCreateView,
    AdminBlogDetailView,
    MediaUploadView,
)

public_urlpatterns = [
    path("blogs/", PublicBlogListView.as_view(), name="public-blog-list"),
    path("blogs/<slug:slug>/", PublicBlogDetailView.as_view(), name="public-blog-detail"),
    path("blogs/<slug:slug>/like/", PublicBlogLikeView.as_view(), name="public-blog-like"),
    path("blogs/<slug:slug>/view/", PublicBlogViewView.as_view(), name="public-blog-view"),
]

admin_urlpatterns = [
    path("blogs/", AdminBlogListCreateView.as_view(), name="admin-blog-list-create"),
    path("blogs/<str:slug>/", AdminBlogDetailView.as_view(), name="admin-blog-detail"),
    path("media/upload/", MediaUploadView.as_view(), name="admin-media-upload"),
]

urlpatterns = public_urlpatterns
