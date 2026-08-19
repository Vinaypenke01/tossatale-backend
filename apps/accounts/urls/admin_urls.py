"""Admin URL routes — /api/v1/admin/"""
from django.urls import path
from apps.accounts.views import (
    AdminUserListView,
    AdminUserDetailView,
    AdminUserActivateView,
    AdminUserDisableView,
)

urlpatterns = [
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("users/<uuid:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("users/<uuid:pk>/activate/", AdminUserActivateView.as_view(), name="admin-user-activate"),
    path("users/<uuid:pk>/disable/", AdminUserDisableView.as_view(), name="admin-user-disable"),
]
