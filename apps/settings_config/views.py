"""
apps/settings_config/views.py — Site Settings Public and Admin Views per §30
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from common.permissions import IsAdmin
from common.responses import success_response
from apps.settings_config.models import SiteSettings


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
