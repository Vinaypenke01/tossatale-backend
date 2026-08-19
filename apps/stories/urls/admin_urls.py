"""
Admin story URL routes
"""
from django.urls import path
from apps.stories.views import (
    AdminStoryListView,
    AdminStoryDetailView,
    AdminApproveStoryView,
    AdminRejectStoryView,
    AdminPublishStoryView,
    AdminArchiveStoryView,
    AdminFeatureStoryView,
    AdminStoryRevisionsView,
    AdminStoryReviewsView,
)

urlpatterns = [
    path("", AdminStoryListView.as_view(), name="admin-story-list"),
    path("<str:pk>/", AdminStoryDetailView.as_view(), name="admin-story-detail"),
    path("<str:pk>/approve/", AdminApproveStoryView.as_view(), name="admin-story-approve"),
    path("<str:pk>/reject/", AdminRejectStoryView.as_view(), name="admin-story-reject"),
    path("<str:pk>/publish/", AdminPublishStoryView.as_view(), name="admin-story-publish"),
    path("<str:pk>/archive/", AdminArchiveStoryView.as_view(), name="admin-story-archive"),
    path("<str:pk>/feature/", AdminFeatureStoryView.as_view(), name="admin-story-feature"),
    path("<str:pk>/revisions/", AdminStoryRevisionsView.as_view(), name="admin-story-revisions"),
    path("<str:pk>/reviews/", AdminStoryReviewsView.as_view(), name="admin-story-reviews"),
]
