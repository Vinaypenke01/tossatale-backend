"""
apps/series/views.py — Views for Story Series (Public, Writer, Admin)
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404

from common.permissions import IsWriter, IsAdmin
from common.responses import success_response, created_response
from common.pagination import StandardResultsSetPagination
from apps.series.models import StorySeries
from apps.stories.models import Story
from apps.series.serializers import StorySeriesSerializer, SeriesReorderSerializer
from apps.series.services import StorySeriesService
from apps.writers.models import WriterProfile


class PublicSeriesListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = StorySeries.objects.filter(status="PUBLISHED").select_related("writer").prefetch_related("items__story")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StorySeriesSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PublicSeriesDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        series = get_object_or_404(
            StorySeries.objects.prefetch_related("items__story__writer", "items__story__category"),
            slug=slug,
            status="PUBLISHED"
        )
        return success_response(data=StorySeriesSerializer(series).data)


class AdminSeriesListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = StorySeries.objects.all().select_related("writer").prefetch_related("items__story")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StorySeriesSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        writer_id = request.data.get("writer_id")
        writer = get_object_or_404(WriterProfile, id=writer_id) if writer_id else None
        if not writer and hasattr(request.user, "writer_profile"):
            writer = request.user.writer_profile
        if not writer:
            writer = WriterProfile.objects.first()

        series = StorySeriesService.create_series(writer, request.user, request.data)
        return created_response(data=StorySeriesSerializer(series).data, message="Series created.")


class AdminSeriesReorderView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        series = get_object_or_404(StorySeries, pk=pk)
        serializer = SeriesReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Parse items_data: ensure sequence_number is int
        formatted_items = [
            {"story_id": item["story_id"], "sequence_number": int(item["sequence_number"])}
            for item in serializer.validated_data["items"]
        ]
        StorySeriesService.reorder_stories(series, formatted_items)
        series.refresh_from_db()
        return success_response(
            data=StorySeriesSerializer(series).data,
            message="Series story sequence reordered."
        )


class AdminSeriesAssignStoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        series = get_object_or_404(StorySeries, pk=pk)
        story_id = request.data.get("story_id")
        story = get_object_or_404(Story, pk=story_id)
        StorySeriesService.assign_story(series, story)
        series.refresh_from_db()
        return success_response(data=StorySeriesSerializer(series).data, message="Story assigned to series.")
