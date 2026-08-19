"""
apps/blogs/urls.py — Blog URL patterns
"""
from django.urls import path
from apps.blogs.views import (
    PublicBlogListView,
    PublicBlogDetailView,
    AdminBlogListCreateView,
    AdminBlogDetailView,
)

public_urlpatterns = [
    path("blogs/", PublicBlogListView.as_view(), name="public-blog-list"),
    path("blogs/<slug:slug>/", PublicBlogDetailView.as_view(), name="public-blog-detail"),
]

admin_urlpatterns = [
    path("blogs/", AdminBlogListCreateView.as_view(), name="admin-blog-list-create"),
    path("blogs/<str:slug>/", AdminBlogDetailView.as_view(), name="admin-blog-detail"),
]

urlpatterns = public_urlpatterns
