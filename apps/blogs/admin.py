"""
apps/blogs/admin.py — Admin registration for Blog models
"""
from django.contrib import admin
from apps.blogs.models import Blog, BlogTag


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "status", "is_featured", "published_at")
    list_filter = ("status", "is_featured", "category")
    search_fields = ("title", "author__email")
