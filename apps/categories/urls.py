"""
apps/categories/urls.py — URL Routing for Public and Admin Category/Tag endpoints
"""
from django.urls import path
from apps.categories.views import (
    PublicCategoryListView,
    AdminCategoryListView,
    AdminCategoryDetailView,
    AdminTagListView,
    AdminTagDetailView,
)

public_urlpatterns = [
    path("categories/", PublicCategoryListView.as_view(), name="public-category-list"),
]

admin_urlpatterns = [
    path("categories/", AdminCategoryListView.as_view(), name="admin-category-list"),
    path("categories/<uuid:pk>/", AdminCategoryDetailView.as_view(), name="admin-category-detail"),
    path("tags/", AdminTagListView.as_view(), name="admin-tag-list"),
    path("tags/<uuid:pk>/", AdminTagDetailView.as_view(), name="admin-tag-detail"),
]
