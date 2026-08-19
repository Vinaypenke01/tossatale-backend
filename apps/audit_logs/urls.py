"""
apps/audit_logs/urls.py — Audit Log URL patterns
"""
from django.urls import path
from apps.audit_logs.views import AdminAuditLogListView

admin_urlpatterns = [
    path("audit-logs/", AdminAuditLogListView.as_view(), name="admin-audit-log-list"),
]

urlpatterns = admin_urlpatterns
