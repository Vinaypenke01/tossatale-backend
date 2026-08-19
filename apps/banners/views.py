"""
apps/banners/views.py — Public and Admin Banner Views
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from common.permissions import IsAdmin
from common.responses import success_response, created_response
from common.pagination import StandardResultsSetPagination
from apps.banners.models import Banner


class PublicBannerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        banner_type = request.query_params.get("type", "HERO").upper()
        now = timezone.now()

        queryset = Banner.objects.filter(
            banner_type=banner_type, is_active=True
        ).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now)
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        ).order_by("display_order")

        data = [
            {
                "id": str(b.id),
                "title": b.title,
                "subtitle": b.subtitle,
                "description": b.description,
                "banner_type": b.banner_type,
                "image": b.image,
                "mobile_image": b.mobile_image,
                "cta_text": b.cta_text,
                "cta_url": b.cta_url,
                "is_default": b.is_default,
            }
            for b in queryset
        ]
        return success_response(data=data)


class AdminBannerListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Banner.objects.all().order_by("display_order")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        data = [
            {
                "id": str(b.id),
                "title": b.title,
                "banner_type": b.banner_type,
                "image": b.image,
                "is_active": b.is_active,
                "is_default": b.is_default,
                "display_order": b.display_order,
                "created_at": b.created_at,
            }
            for b in page
        ]
        return paginator.get_paginated_response(data)

    def post(self, request):
        b = Banner.objects.create(
            created_by=request.user,
            title=request.data.get("title", ""),
            subtitle=request.data.get("subtitle", ""),
            description=request.data.get("description", ""),
            banner_type=request.data.get("banner_type", "HERO"),
            image=request.data.get("image", ""),
            mobile_image=request.data.get("mobile_image", ""),
            cta_text=request.data.get("cta_text", ""),
            cta_url=request.data.get("cta_url", ""),
            is_active=request.data.get("is_active", True),
            is_default=request.data.get("is_default", False),
            display_order=request.data.get("display_order", 0),
        )
        return created_response(data={"id": str(b.id), "title": b.title}, message="Banner created.")
