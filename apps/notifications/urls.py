"""
apps/notifications/urls.py — URL routing for Notifications API
"""
from django.urls import path
from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", views.NotificationUnreadCountView.as_view(), name="notification-unread-count"),
    path("mark-all-read/", views.NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),
    path("clear-all/", views.NotificationClearAllView.as_view(), name="notification-clear-all"),
    path("<uuid:pk>/read/", views.NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("<uuid:pk>/mark-read/", views.NotificationMarkReadView.as_view(), name="notification-mark-read-alt"),
    path("<uuid:pk>/", views.NotificationDeleteView.as_view(), name="notification-delete"),
]
