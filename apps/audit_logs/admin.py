"""
apps/audit_logs/admin.py — Admin registration for AuditLog model
"""
from django.contrib import admin
from apps.audit_logs.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "object_type", "object_id", "created_at")
    list_filter = ("action", "object_type")
    search_fields = ("actor__email", "object_repr", "object_id")
    readonly_fields = ("id", "created_at")
