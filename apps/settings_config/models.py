"""
apps/settings_config/models.py — Site Settings Singleton Model per §19 & Phase 5 Spec
"""
from django.conf import settings
from django.db import models


class SiteSettings(models.Model):
    """
    Singleton SiteSettings model (pk=1) per §19 storing global platform configurations.
    """
    id = models.IntegerField(primary_key=True, default=1, editable=False)
    site_name = models.CharField(max_length=150, default="Tossatale")
    tagline = models.CharField(max_length=255, default="Where Stories Live and Breathes")
    logo_url = models.URLField(blank=True)
    favicon_url = models.URLField(blank=True)

    default_from_email = models.EmailField(default="hello@tossatale.com")
    contact_email = models.EmailField(default="support@tossatale.com")

    footer_description = models.TextField(blank=True)
    copyright_text = models.CharField(max_length=255, default="© Tossatale. All rights reserved.")

    # Social links
    social_facebook = models.URLField(blank=True)
    social_instagram = models.URLField(blank=True)
    social_x = models.URLField(blank=True)
    social_linkedin = models.URLField(blank=True)
    social_youtube = models.URLField(blank=True)

    # System state
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(default="Tossatale is currently undergo scheduled maintenance. We'll be back shortly.")

    # Analytics IDs
    analytics_google_id = models.CharField(max_length=50, blank=True)
    analytics_meta_pixel = models.CharField(max_length=50, blank=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "site_settings"

    def __str__(self):
        return f"SiteSettings({self.site_name}, maintenance={self.maintenance_mode})"

    def save(self, *args, **kwargs):
        self.pk = 1  # Force singleton ID
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
