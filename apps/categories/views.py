"""
apps/categories — Service, Views, and URLs combined for Phase 1 brevity.
"""
from django.db import transaction
from rest_framework import filters, generics
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.categories.models import Category, Tag
from apps.categories.serializers import (
    CategorySerializer, CategoryWriteSerializer,
    TagSerializer, TagWriteSerializer,
)
from common.exceptions import ResourceNotFoundError
from common.pagination import StandardPagination
from common.permissions import IsAdmin
from common.responses import created_response, success_response, no_content_response
from common.utils import generate_unique_slug


# ──────────────────────────────────────────────────────────────────────────────
# Category Service
# ──────────────────────────────────────────────────────────────────────────────

class CategoryService:

    @staticmethod
    def create(data: dict, created_by=None) -> Category:
        slug = generate_unique_slug(Category, data["name"])
        with transaction.atomic():
            return Category.objects.create(slug=slug, created_by=created_by, **data)

    @staticmethod
    def update(category: Category, data: dict) -> Category:
        for field, value in data.items():
            setattr(category, field, value)
        category.save()
        return category


class TagService:

    @staticmethod
    def create(data: dict) -> Tag:
        slug = generate_unique_slug(Tag, data["name"])
        return Tag.objects.create(slug=slug, **data)

    @staticmethod
    def update(tag: Tag, data: dict) -> Tag:
        for field, value in data.items():
            setattr(tag, field, value)
        tag.save()
        return tag


# ──────────────────────────────────────────────────────────────────────────────
# Category Views
# ──────────────────────────────────────────────────────────────────────────────

class PublicCategoryListView(generics.ListAPIView):
    """GET /api/v1/public/categories/"""
    serializer_class = CategorySerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["category_type", "is_featured"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("display_order", "name")


class AdminCategoryListView(generics.ListAPIView):
    """GET /api/v1/admin/categories/"""
    permission_classes = [IsAdmin]
    serializer_class = CategorySerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["category_type", "is_featured", "is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        return Category.all_objects.all()

    def post(self, request):
        serializer = CategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = CategoryService.create(serializer.validated_data, created_by=request.user)
        return created_response(
            data=CategorySerializer(category).data,
            message="Category created.",
        )


class AdminCategoryDetailView(APIView):
    """GET/PATCH/DELETE /api/v1/admin/categories/{id}/"""
    permission_classes = [IsAdmin]

    def _get(self, pk):
        try:
            return Category.all_objects.get(pk=pk)
        except Category.DoesNotExist:
            raise ResourceNotFoundError("Category not found.")

    def get(self, request, pk):
        return success_response(data=CategorySerializer(self._get(pk)).data)

    def patch(self, request, pk):
        cat = self._get(pk)
        serializer = CategoryWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        cat = CategoryService.update(cat, serializer.validated_data)
        return success_response(data=CategorySerializer(cat).data, message="Category updated.")

    def delete(self, request, pk):
        self._get(pk).soft_delete()
        return no_content_response()


# ──────────────────────────────────────────────────────────────────────────────
# Tag Views
# ──────────────────────────────────────────────────────────────────────────────

class AdminTagListView(generics.ListAPIView):
    """GET /api/v1/admin/tags/"""
    permission_classes = [IsAdmin]
    serializer_class = TagSerializer
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        return Tag.all_objects.all()

    def post(self, request):
        serializer = TagWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = TagService.create(serializer.validated_data)
        return created_response(data=TagSerializer(tag).data, message="Tag created.")


class AdminTagDetailView(APIView):
    """PATCH/DELETE /api/v1/admin/tags/{id}/"""
    permission_classes = [IsAdmin]

    def _get(self, pk):
        try:
            return Tag.all_objects.get(pk=pk)
        except Tag.DoesNotExist:
            raise ResourceNotFoundError("Tag not found.")

    def get(self, request, pk):
        return success_response(data=TagSerializer(self._get(pk)).data)

    def patch(self, request, pk):
        tag = self._get(pk)
        serializer = TagWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        tag = TagService.update(tag, serializer.validated_data)
        return success_response(data=TagSerializer(tag).data, message="Tag updated.")

    def delete(self, request, pk):
        self._get(pk).soft_delete()
        return no_content_response()


# ──────────────────────────────────────────────────────────────────────────────
# URL Patterns
# ──────────────────────────────────────────────────────────────────────────────

from django.urls import path

public_urlpatterns = [
    path("categories/", PublicCategoryListView.as_view(), name="public-category-list"),
]

admin_urlpatterns = [
    path("categories/", AdminCategoryListView.as_view(), name="admin-category-list"),
    path("categories/<uuid:pk>/", AdminCategoryDetailView.as_view(), name="admin-category-detail"),
    path("tags/", AdminTagListView.as_view(), name="admin-tag-list"),
    path("tags/<uuid:pk>/", AdminTagDetailView.as_view(), name="admin-tag-detail"),
]
