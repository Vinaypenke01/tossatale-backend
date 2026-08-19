"""
Admin review queue URL routes
"""
from django.urls import path
from apps.stories.views import (
    AdminReviewQueueView,
    AdminApproveStoryView,
    AdminRejectStoryView,
)

urlpatterns = [
    path("", AdminReviewQueueView.as_view(), name="admin-review-queue"),
    path("queue/", AdminReviewQueueView.as_view(), name="admin-review-queue-alias"),
    path("<str:pk>/approve/", AdminApproveStoryView.as_view(), name="admin-review-approve"),
    path("<str:pk>/reject/", AdminRejectStoryView.as_view(), name="admin-review-reject"),
]

