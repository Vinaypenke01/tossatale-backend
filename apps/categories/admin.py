from django.contrib import admin
from apps.categories.models import Category, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "category_type", "display_order", "is_featured", "is_active", "created_at"]
    list_filter = ["category_type", "is_featured", "is_active"]
    search_fields = ["name", "slug", "description"]
    ordering = ["display_order", "name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "usage_count", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug", "description"]
    ordering = ["-usage_count", "name"]
    prepopulated_fields = {"slug": ("name",)}
