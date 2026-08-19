"""
apps/series/urls.py — URL patterns for StorySeries
"""
from django.urls import path
from apps.series.views import (
    PublicSeriesListView,
    PublicSeriesDetailView,
    AdminSeriesListCreateView,
    AdminSeriesReorderView,
    AdminSeriesAssignStoryView,
)

public_urlpatterns = [
    path("series/", PublicSeriesListView.as_view(), name="public-series-list"),
    path("series/<slug:slug>/", PublicSeriesDetailView.as_view(), name="public-series-detail"),
]

admin_urlpatterns = [
    path("series/", AdminSeriesListCreateView.as_view(), name="admin-series-list-create"),
    path("series/<uuid:pk>/reorder/", AdminSeriesReorderView.as_view(), name="admin-series-reorder"),
    path("series/<uuid:pk>/assign-story/", AdminSeriesAssignStoryView.as_view(), name="admin-series-assign-story"),
]

urlpatterns = public_urlpatterns
