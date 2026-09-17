"""
Writer story URL routes
"""
from django.urls import path
from apps.stories.views import (
    WriterStoryListCreateView,
    WriterStoryDetailView,
    WriterStorySubmitView,
    WriterStoryDuplicateView,
    WriterChapterListCreateView,
    WriterChapterDetailView,
    WriterChapterReorderView,
    WriterActiveSeriesView,
    WriterSeriesListView,
    WriterSeriesStatusToggleView,
    WriterChapterSubmitView,
)

urlpatterns = [
    path("", WriterStoryListCreateView.as_view(), name="writer-story-list-create"),
    path("active-series/", WriterActiveSeriesView.as_view(), name="writer-story-active-series"),
    path("series/", WriterSeriesListView.as_view(), name="writer-story-series-list"),
    path("<str:pk>/", WriterStoryDetailView.as_view(), name="writer-story-detail"),
    path("<str:pk>/submit/", WriterStorySubmitView.as_view(), name="writer-story-submit"),
    path("<str:pk>/duplicate/", WriterStoryDuplicateView.as_view(), name="writer-story-duplicate"),
    path("<str:pk>/series-status/", WriterSeriesStatusToggleView.as_view(), name="writer-story-series-status"),
    path("<str:pk>/chapters/", WriterChapterListCreateView.as_view(), name="writer-chapter-list-create"),
    path("<str:pk>/chapters/reorder/", WriterChapterReorderView.as_view(), name="writer-chapter-reorder"),
    path("<str:pk>/chapters/<str:chapter_pk>/", WriterChapterDetailView.as_view(), name="writer-chapter-detail"),
    path("<str:pk>/chapters/<str:chapter_pk>/submit/", WriterChapterSubmitView.as_view(), name="writer-chapter-submit"),
]


