"""
apps/videos/views.py — Public and Admin Video & Upcoming Project Views
"""
import uuid
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone

from common.permissions import IsAdmin
from common.responses import success_response, created_response, no_content_response
from common.pagination import StandardResultsSetPagination
from apps.videos.models import Video
from apps.categories.models import Category
from apps.videos.serializers import VideoSerializer, VideoCreateUpdateSerializer


class PublicVideoListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Video.objects.filter(is_active=True).select_related("category")
        upcoming_param = request.query_params.get("upcoming")
        category_param = request.query_params.get("category")
        search_param = request.query_params.get("search")

        if upcoming_param is not None and upcoming_param.lower() in ["true", "1"]:
            queryset = queryset.filter(is_upcoming=True)
        elif upcoming_param is not None and upcoming_param.lower() in ["false", "0"]:
            queryset = queryset.filter(is_upcoming=False)

        if category_param:
            queryset = queryset.filter(category__slug=category_param)
        if search_param:
            queryset = queryset.filter(title__icontains=search_param)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = VideoSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PublicVideoDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        video = Video.objects.filter(slug=slug, is_active=True).first()
        if not video:
            try:
                uuid.UUID(str(slug))
                video = Video.objects.filter(id=slug, is_active=True).first()
            except (ValueError, TypeError):
                pass

        if not video:
            return success_response(data=None, message="Video not found", status_code=status.HTTP_404_NOT_FOUND)
        return success_response(data=VideoSerializer(video).data)


class AdminVideoListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Video.objects.all().select_related("category")
        upcoming_param = request.query_params.get("upcoming")
        if upcoming_param is not None and upcoming_param.lower() in ["true", "1"]:
            queryset = queryset.filter(is_upcoming=True)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = VideoSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = VideoCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        category = None
        cat_id = data.get("category_id")
        if cat_id:
            category = Category.objects.filter(slug=cat_id).first()
            if not category:
                try:
                    uuid.UUID(str(cat_id))
                    category = Category.objects.filter(id=cat_id).first()
                except (ValueError, TypeError):
                    pass

        video = Video.objects.create(
            created_by=request.user,
            title=data["title"],
            youtube_url=data.get("youtube_url", ""),
            description=data.get("description", ""),
            editorial_note=data.get("editorial_note", ""),
            director=data.get("director", "Tossatale Studio"),
            expected_release=data.get("expected_release", "Coming Soon"),
            status=data.get("status", "In Production"),
            category=category,
            category_name=data.get("category_name", "Film"),
            duration=data.get("duration", 0),
            thumbnail_url=data.get("thumbnail_url", ""),
            cover_image=data.get("cover_image", ""),
            is_upcoming=data.get("is_upcoming", False),
            is_featured=data.get("is_featured", False),
            is_active=True,
            published_at=timezone.now(),
        )
        return created_response(data=VideoSerializer(video).data, message="Video post created successfully.")


class AdminVideoDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_video(self, slug):
        video = Video.objects.filter(slug=slug).first()
        if not video:
            try:
                uuid.UUID(str(slug))
                video = Video.objects.filter(id=slug).first()
            except (ValueError, TypeError):
                pass
        return video

    def get(self, request, slug):
        video = self._get_video(slug)
        if not video:
            return success_response(data=None, message="Video not found", status_code=status.HTTP_404_NOT_FOUND)
        return success_response(data=VideoSerializer(video).data)

    def patch(self, request, slug):
        video = self._get_video(slug)
        if not video:
            return success_response(data=None, message="Video not found", status_code=status.HTTP_404_NOT_FOUND)

        serializer = VideoCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        for field in ["title", "youtube_url", "description", "editorial_note", "director",
                      "expected_release", "status", "category_name", "duration",
                      "thumbnail_url", "cover_image", "is_upcoming", "is_featured"]:
            if field in data:
                setattr(video, field, data[field])

        if "category_id" in data and data["category_id"]:
            cat_id = data["category_id"]
            cat = Category.objects.filter(slug=cat_id).first()
            if not cat:
                try:
                    uuid.UUID(str(cat_id))
                    cat = Category.objects.filter(id=cat_id).first()
                except (ValueError, TypeError):
                    pass
            if cat:
                video.category = cat

        video.save()
        return success_response(data=VideoSerializer(video).data, message="Video post updated successfully.")

    def delete(self, request, slug):
        video = self._get_video(slug)
        if video:
            video.delete()
        return no_content_response()
