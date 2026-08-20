"""
apps/engagements/urls.py — URL routing for Public Story endpoints and Reader Dashboard
"""
from django.urls import path
from apps.engagements.views import (
    PublicStoryListView,
    PublicStoryDetailView,
    PublicRelatedStoriesView,
    RecordStoryView,
    RecordStoryShareView,
    ReaderDashboardView,
    StoryLikeToggleView,
    StoryBookmarkToggleView,
    ReaderLikedStoriesView,
    ReaderBookmarksView,
    ReaderRecentlyReadView,
    StoryLikeDismissView,
)

public_urlpatterns = [
    path("stories/", PublicStoryListView.as_view(), name="public-story-list"),
    path("stories/<slug:slug>/", PublicStoryDetailView.as_view(), name="public-story-detail"),
    path("stories/<slug:slug>/related/", PublicRelatedStoriesView.as_view(), name="public-related-stories"),
    path("stories/<uuid:pk>/like/", StoryLikeToggleView.as_view(), name="public-story-like-toggle"),
    path("stories/<uuid:pk>/like-dismiss/", StoryLikeDismissView.as_view(), name="story-like-dismiss"),
    path("stories/<uuid:pk>/view/", RecordStoryView.as_view(), name="record-story-view"),
    path("stories/<uuid:pk>/share/", RecordStoryShareView.as_view(), name="record-story-share"),
]

reader_urlpatterns = [
    path("dashboard/", ReaderDashboardView.as_view(), name="reader-dashboard"),
    path("stories/<uuid:pk>/like/", StoryLikeToggleView.as_view(), name="story-like-toggle"),
    path("stories/<uuid:pk>/bookmark/", StoryBookmarkToggleView.as_view(), name="story-bookmark-toggle"),
    path("liked-stories/", ReaderLikedStoriesView.as_view(), name="reader-liked-stories"),
    path("bookmarks/", ReaderBookmarksView.as_view(), name="reader-bookmarks"),
    path("recently-read/", ReaderRecentlyReadView.as_view(), name="reader-recently-read"),
]

urlpatterns = public_urlpatterns
