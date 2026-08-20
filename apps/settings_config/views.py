from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from common.permissions import IsAdmin
from common.responses import success_response, created_response, error_response
from apps.settings_config.models import SiteSettings, FAQItem


class FAQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQItem
        fields = [
            "id",
            "category",
            "question",
            "answer",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]


class PublicSettingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        s = SiteSettings.get_solo()
        return success_response(data={
            "site_name": s.site_name,
            "tagline": s.tagline,
            "logo_url": s.logo_url,
            "favicon_url": s.favicon_url,
            "footer_description": s.footer_description,
            "copyright_text": s.copyright_text,
            "contact_email": s.contact_email,
            "socials": {
                "facebook": s.social_facebook,
                "instagram": s.social_instagram,
                "x": s.social_x,
                "linkedin": s.social_linkedin,
                "youtube": s.social_youtube,
            },
            "maintenance_mode": s.maintenance_mode,
            "maintenance_message": s.maintenance_message if s.maintenance_mode else "",
        })


class AdminSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        s = SiteSettings.get_solo()
        return success_response(data={
            "site_name": s.site_name,
            "tagline": s.tagline,
            "logo_url": s.logo_url,
            "favicon_url": s.favicon_url,
            "default_from_email": s.default_from_email,
            "contact_email": s.contact_email,
            "footer_description": s.footer_description,
            "copyright_text": s.copyright_text,
            "social_facebook": s.social_facebook,
            "social_instagram": s.social_instagram,
            "social_x": s.social_x,
            "social_linkedin": s.social_linkedin,
            "social_youtube": s.social_youtube,
            "maintenance_mode": s.maintenance_mode,
            "maintenance_message": s.maintenance_message,
            "analytics_google_id": s.analytics_google_id,
            "analytics_meta_pixel": s.analytics_meta_pixel,
        })

    def patch(self, request, *args, **kwargs):
        s = SiteSettings.get_solo()
        data = request.data

        for field in [
            "site_name", "tagline", "logo_url", "favicon_url", "default_from_email",
            "contact_email", "footer_description", "copyright_text", "social_facebook",
            "social_instagram", "social_x", "social_linkedin", "social_youtube",
            "maintenance_mode", "maintenance_message", "analytics_google_id", "analytics_meta_pixel"
        ]:
            if field in data:
                setattr(s, field, data[field])

        s.updated_by = request.user
        s.save()
        return success_response(message="Site settings updated successfully.")


# ──────────────────────────────────────────────────────────────────────────────
# FAQ Views (Public & Admin)
# ──────────────────────────────────────────────────────────────────────────────

class PublicFAQListView(APIView):
    """
    GET /api/v1/public/faqs/ — Returns active FAQs grouped by category.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        category = request.query_params.get("category")
        search = request.query_params.get("search")

        qs = FAQItem.objects.filter(is_active=True)
        if category and category.lower() != "all":
            qs = qs.filter(category__iexact=category)
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(question__icontains=search) | Q(answer__icontains=search))

        serializer = FAQItemSerializer(qs, many=True)
        return success_response(data=serializer.data)


class AdminFAQListCreateView(APIView):
    """
    GET /api/v1/admin/faqs/ — List all FAQs.
    POST /api/v1/admin/faqs/ — Create new FAQ.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        category = request.query_params.get("category")
        qs = FAQItem.objects.all()
        if category and category.lower() != "all":
            qs = qs.filter(category__iexact=category)
        serializer = FAQItemSerializer(qs, many=True)
        return success_response(data=serializer.data)

    def post(self, request):
        serializer = FAQItemSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        faq = serializer.save()
        return created_response(
            data=FAQItemSerializer(faq).data,
            message="FAQ question created successfully.",
        )


class AdminFAQDetailView(APIView):
    """
    GET, PATCH, DELETE /api/v1/admin/faqs/<pk>/
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_object(self, pk):
        try:
            return FAQItem.objects.get(pk=pk)
        except FAQItem.DoesNotExist:
            return None

    def get(self, request, pk):
        faq = self.get_object(pk)
        if not faq:
            return error_response(message="FAQ item not found", status_code=status.HTTP_404_NOT_FOUND)
        return success_response(data=FAQItemSerializer(faq).data)

    def patch(self, request, pk):
        faq = self.get_object(pk)
        if not faq:
            return error_response(message="FAQ item not found", status_code=status.HTTP_404_NOT_FOUND)
        serializer = FAQItemSerializer(faq, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        faq = serializer.save()
        return success_response(
            data=FAQItemSerializer(faq).data,
            message="FAQ item updated successfully.",
        )

    def delete(self, request, pk):
        faq = self.get_object(pk)
        if not faq:
            return error_response(message="FAQ item not found", status_code=status.HTTP_404_NOT_FOUND)
        faq.delete()
        return success_response(message="FAQ item deleted successfully.")

