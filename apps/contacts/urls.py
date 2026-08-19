"""
apps/contacts/urls.py — Contact URL patterns
"""
from django.urls import path
from apps.contacts.views import PublicContactFormView, AdminContactMessageListView, AdminContactMessageResolveView

public_urlpatterns = [
    path("contact/", PublicContactFormView.as_view(), name="public-contact-form"),
]

admin_urlpatterns = [
    path("contacts/", AdminContactMessageListView.as_view(), name="admin-contact-list"),
    path("contacts/<uuid:pk>/resolve/", AdminContactMessageResolveView.as_view(), name="admin-contact-resolve"),
]

urlpatterns = public_urlpatterns
