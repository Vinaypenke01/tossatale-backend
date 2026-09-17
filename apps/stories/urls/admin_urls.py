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
    WriterChapterListCreateView,
    WriterChapterReorderView,
    WriterChapterDetailView,
    WriterActiveSeriesView,
    WriterSeriesListView,
    WriterSeriesStatusToggleView,
    AdminApproveChapterView,
    AdminPublishChapterView,
    AdminRejectChapterView,
)

urlpatterns = [
    path("", AdminStoryListView.as_view(), name="admin-story-list"),
    path("active-series/", WriterActiveSeriesView.as_view(), name="admin-story-active-series"),
    path("series/", WriterSeriesListView.as_view(), name="admin-story-series-list"),
    path("<str:pk>/", AdminStoryDetailView.as_view(), name="admin-story-detail"),
    path("<str:pk>/approve/", AdminApproveStoryView.as_view(), name="admin-story-approve"),
    path("<str:pk>/reject/", AdminRejectStoryView.as_view(), name="admin-story-reject"),
    path("<str:pk>/publish/", AdminPublishStoryView.as_view(), name="admin-story-publish"),
    path("<str:pk>/archive/", AdminArchiveStoryView.as_view(), name="admin-story-archive"),
    path("<str:pk>/feature/", AdminFeatureStoryView.as_view(), name="admin-story-feature"),
    path("<str:pk>/revisions/", AdminStoryRevisionsView.as_view(), name="admin-story-revisions"),
    path("<str:pk>/reviews/", AdminStoryReviewsView.as_view(), name="admin-story-reviews"),
    path("<str:pk>/series-status/", WriterSeriesStatusToggleView.as_view(), name="admin-story-series-status"),
    path("<str:pk>/chapters/", WriterChapterListCreateView.as_view(), name="admin-chapter-list-create"),
    path("<str:pk>/chapters/reorder/", WriterChapterReorderView.as_view(), name="admin-chapter-reorder"),
    path("<str:pk>/chapters/<str:chapter_pk>/", WriterChapterDetailView.as_view(), name="admin-chapter-detail"),
    path("<str:pk>/chapters/<str:chapter_pk>/approve/", AdminApproveChapterView.as_view(), name="admin-chapter-approve"),
    path("<str:pk>/chapters/<str:chapter_pk>/publish/", AdminPublishChapterView.as_view(), name="admin-chapter-publish"),
    path("<str:pk>/chapters/<str:chapter_pk>/reject/", AdminRejectChapterView.as_view(), name="admin-chapter-reject"),
]

