"""
apps/search/urls.py — Search URL patterns
"""
from django.urls import path
from apps.search.views import UnifiedSearchView

public_urlpatterns = [
    path("search/", UnifiedSearchView.as_view(), name="public-search"),
]

urlpatterns = public_urlpatterns
