"""
apps/homepage/urls.py — Homepage URL routing
"""
from django.urls import path
from apps.homepage.views import PublicHomepageView, AdminHomepageSectionListView

public_urlpatterns = [
    path("homepage/", PublicHomepageView.as_view(), name="public-homepage"),
]

admin_urlpatterns = [
    path("homepage/sections/", AdminHomepageSectionListView.as_view(), name="admin-homepage-sections"),
    path("homepage/sections/<uuid:pk>/", AdminHomepageSectionListView.as_view(), name="admin-homepage-section-detail"),
]

urlpatterns = public_urlpatterns
