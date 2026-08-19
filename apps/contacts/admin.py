"""
apps/contacts/admin.py — Admin registration for ContactMessage model
"""
from django.contrib import admin
from apps.contacts.models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "email", "subject")
