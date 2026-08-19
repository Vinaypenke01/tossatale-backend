"""
apps/blogs/views.py — Public and Admin Blog Views
"""
import re
import uuid
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify

from common.permissions import IsAdmin
from common.responses import success_response, created_response, no_content_response
from common.pagination import StandardResultsSetPagination
from apps.blogs.models import Blog
from apps.categories.models import Category
from apps.blogs.serializers import BlogSerializer, BlogCreateUpdateSerializer


class PublicBlogListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Blog.objects.filter(status="PUBLISHED").select_related("category")
        category_param = request.query_params.get("category")
        search_param = request.query_params.get("search")

        if category_param:
            queryset = queryset.filter(category__slug=category_param)
        if search_param:
            queryset = queryset.filter(title__icontains=search_param)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = BlogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PublicBlogDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        blog = get_object_or_404(Blog.objects.select_related("category"), slug=slug, status="PUBLISHED")
        return success_response(data=BlogSerializer(blog).data)


class AdminBlogListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Blog.objects.all().select_related("category")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = BlogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = BlogCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        category_id = data.get("category_id")
        category = None

        if category_id:
            category = Category.objects.filter(slug=category_id).first()
            if not category:
                try:
                    uuid.UUID(str(category_id))
                    category = Category.objects.filter(id=category_id).first()
                except (ValueError, TypeError):
                    pass

        if not category:
            category = Category.objects.first()
            if not category:
                category = Category.objects.create(
                    name="General",
                    slug="general",
                    description="General blog category",
                    category_type="BLOG",
                    is_active=True
                )

        slug_base = slugify(data["title"]) or "blog"
        slug = slug_base
        count = 1
        while Blog.objects.filter(slug=slug).exists():
            slug = f"{slug_base}-{count}"
            count += 1

        plain = re.sub(r"<[^>]+>", " ", data["content"]).strip()
        words = len(plain.split()) if plain else 0
        subtitle_val = data.get("subtitle") or data.get("excerpt") or ""

        seo_t = data.get("seo_title") or data["title"][:70]
        seo_d = data.get("seo_description") or subtitle_val[:160]

        user_rt = data.get("reading_time")
        final_rt = user_rt if user_rt is not None and user_rt > 0 else (max(1, words // 200) if words > 0 else 1)

        blog = Blog.objects.create(
            author=request.user,
            title=data["title"],
            slug=slug,
            subtitle=subtitle_val,
            content=data["content"],
            plain_text_content=plain,
            cover_image=data.get("cover_image", ""),
            featured_image=data.get("featured_image", ""),
            category=category,
            seo_title=seo_t,
            seo_description=seo_d,
            is_featured=data.get("is_featured", False),
            status="PUBLISHED",
            published_at=timezone.now(),
            word_count=words,
            reading_time=final_rt,
        )
        return created_response(data=BlogSerializer(blog).data, message="Blog post created successfully.")


class AdminBlogDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_blog(self, slug):
        blog = Blog.objects.filter(slug=slug).first()
        if not blog:
            try:
                uuid.UUID(str(slug))
                blog = Blog.objects.filter(id=slug).first()
            except (ValueError, TypeError):
                pass
        return blog

    def get(self, request, slug):
        blog = self._get_blog(slug)
        if not blog:
            return success_response(data=None, message="Blog not found", status_code=status.HTTP_404_NOT_FOUND)
        return success_response(data=BlogSerializer(blog).data)

    def patch(self, request, slug):
        blog = self._get_blog(slug)
        if not blog:
            return success_response(data=None, message="Blog not found", status_code=status.HTTP_404_NOT_FOUND)

        serializer = BlogCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "category_id" in data and data["category_id"]:
            category_id = data["category_id"]
            cat = Category.objects.filter(slug=category_id).first()
            if not cat:
                try:
                    uuid.UUID(str(category_id))
                    cat = Category.objects.filter(id=category_id).first()
                except (ValueError, TypeError):
                    pass
            if cat:
                blog.category = cat

        if "title" in data:
            blog.title = data["title"]
            if "seo_title" not in data:
                blog.seo_title = data["title"][:70]
        if "subtitle" in data or "excerpt" in data:
            blog.subtitle = data.get("subtitle") or data.get("excerpt", blog.subtitle)
            if "seo_description" not in data:
                blog.seo_description = blog.subtitle[:160]
        if "content" in data:
            blog.content = data["content"]
            plain = re.sub(r"<[^>]+>", " ", data["content"]).strip()
            blog.plain_text_content = plain
            words = len(plain.split()) if plain else 0
            blog.word_count = words
        if "reading_time" in data and data["reading_time"] is not None and data["reading_time"] > 0:
            blog.reading_time = data["reading_time"]
        if "cover_image" in data:
            blog.cover_image = data["cover_image"]

        blog.save()
        return success_response(data=BlogSerializer(blog).data, message="Blog post updated successfully.")

    def delete(self, request, slug):
        blog = self._get_blog(slug)
        if blog:
            blog.delete()
        return no_content_response()
