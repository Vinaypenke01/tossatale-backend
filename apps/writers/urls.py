"""apps/writers — URL Routes"""
from django.urls import path
from apps.writers.views import (
    PublicWriterListView,
    PublicWriterDetailView,
    PublicWriterSupportView,
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
    path("<slug:slug>/support/", PublicWriterSupportView.as_view(), name="public-writer-support"),
    path("<slug:slug>/follow/", PublicWriterSupportView.as_view(), name="public-writer-follow"),
]

# Admin URLs — mounted at /api/v1/admin/writers/
admin_urlpatterns = [
    path("", AdminWriterListView.as_view(), name="admin-writer-list"),
    path("invite/", AdminWriterInviteView.as_view(), name="admin-writer-invite"),
    path("<str:lookup>/", AdminWriterDetailView.as_view(), name="admin-writer-detail"),
    path("<str:lookup>/verify/", AdminWriterVerifyView.as_view(), name="admin-writer-verify"),
    path("<str:lookup>/unverify/", AdminWriterUnverifyView.as_view(), name="admin-writer-unverify"),
    path("<str:lookup>/activate/", AdminWriterActivateView.as_view(), name="admin-writer-activate"),
    path("<str:lookup>/deactivate/", AdminWriterDeactivateView.as_view(), name="admin-writer-deactivate"),
]

# Default export is writer-dashboard patterns
urlpatterns = writer_urlpatterns
