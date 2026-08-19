"""apps/writers — URL Routes"""
from django.urls import path
from apps.writers.views import (
    PublicWriterListView,
    PublicWriterDetailView,
    WriterProfileView,
    AdminWriterListView,
    AdminWriterDetailView,
    AdminWriterVerifyView,
    AdminWriterUnverifyView,
    AdminWriterActivateView,
    AdminWriterDeactivateView,
    AdminWriterInviteView,
)

# Writer dashboard URLs — mounted at /api/v1/writer/
writer_urlpatterns = [
    path("profile/", WriterProfileView.as_view(), name="writer-profile"),
]

# Public URLs — mounted at /api/v1/public/writers/
public_urlpatterns = [
    path("", PublicWriterListView.as_view(), name="public-writer-list"),
    path("<slug:slug>/", PublicWriterDetailView.as_view(), name="public-writer-detail"),
]

# Admin URLs — mounted at /api/v1/admin/writers/
admin_urlpatterns = [
    path("", AdminWriterListView.as_view(), name="admin-writer-list"),
    path("invite/", AdminWriterInviteView.as_view(), name="admin-writer-invite"),
    path("<uuid:pk>/", AdminWriterDetailView.as_view(), name="admin-writer-detail"),
    path("<uuid:pk>/verify/", AdminWriterVerifyView.as_view(), name="admin-writer-verify"),
    path("<uuid:pk>/unverify/", AdminWriterUnverifyView.as_view(), name="admin-writer-unverify"),
    path("<uuid:pk>/activate/", AdminWriterActivateView.as_view(), name="admin-writer-activate"),
    path("<uuid:pk>/deactivate/", AdminWriterDeactivateView.as_view(), name="admin-writer-deactivate"),
]

# Default export is writer-dashboard patterns
urlpatterns = writer_urlpatterns
