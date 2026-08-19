"""
Writer story URL routes
"""
from django.urls import path
from apps.stories.views import (
    WriterStoryListCreateView,
    WriterStoryDetailView,
    WriterStorySubmitView,
    WriterStoryDuplicateView,
)

urlpatterns = [
    path("", WriterStoryListCreateView.as_view(), name="writer-story-list-create"),
    path("<str:pk>/", WriterStoryDetailView.as_view(), name="writer-story-detail"),
    path("<str:pk>/submit/", WriterStorySubmitView.as_view(), name="writer-story-submit"),
    path("<str:pk>/duplicate/", WriterStoryDuplicateView.as_view(), name="writer-story-duplicate"),
]
