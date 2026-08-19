"""
apps/analytics/urls.py — Analytics URL patterns
"""
from django.urls import path
from apps.analytics.views import (
    WriterAnalyticsOverviewView,
    AdminAnalyticsOverviewView,
    AdminAnalyticsExportCSVView,
)

writer_urlpatterns = [
    path("analytics/overview/", WriterAnalyticsOverviewView.as_view(), name="writer-analytics-overview"),
]

admin_urlpatterns = [
    path("analytics/overview/", AdminAnalyticsOverviewView.as_view(), name="admin-analytics-overview"),
    path("analytics/platform/export/", AdminAnalyticsExportCSVView.as_view(), name="admin-analytics-export"),
]

urlpatterns = writer_urlpatterns
