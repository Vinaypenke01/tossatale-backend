"""
Tossatale — Root URL Configuration
URL Layer: §4.5 — grouped by module, versioned under /api/v1/
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.engagements.urls import public_urlpatterns as engagements_public, reader_urlpatterns as engagements_reader
from apps.series.urls import public_urlpatterns as series_public, admin_urlpatterns as series_admin
from apps.blogs.urls import public_urlpatterns as blogs_public, admin_urlpatterns as blogs_admin
from apps.videos.urls import public_urlpatterns as videos_public, admin_urlpatterns as videos_admin
from apps.search.urls import public_urlpatterns as search_public
from apps.homepage.urls import public_urlpatterns as homepage_public, admin_urlpatterns as homepage_admin
from apps.banners.urls import public_urlpatterns as banners_public, admin_urlpatterns as banners_admin
from apps.contacts.urls import public_urlpatterns as contacts_public, admin_urlpatterns as contacts_admin
from apps.newsletters.urls import public_urlpatterns as newsletters_public, admin_urlpatterns as newsletters_admin
from apps.settings_config.urls import public_urlpatterns as settings_public, admin_urlpatterns as settings_admin
from apps.analytics.urls import writer_urlpatterns as analytics_writer, admin_urlpatterns as analytics_admin
from apps.audit_logs.urls import admin_urlpatterns as audit_logs_admin
from apps.categories.views import public_urlpatterns as categories_public, admin_urlpatterns as categories_admin
from apps.writers.urls import public_urlpatterns as writers_public, admin_urlpatterns as writers_admin

urlpatterns = [
    # Django Admin
    path("django-admin/", admin.site.urls),

    # OpenAPI Schema & Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Versioned API routes
    # ── Auth & Account routes ──
    path("api/v1/auth/", include("apps.accounts.urls.auth")),
    path("api/v1/public/", include("apps.accounts.urls.public")),
    path("api/v1/user/", include("apps.accounts.urls.user")),
    path("api/v1/writer/", include("apps.writers.urls")),
    path("api/v1/admin/", include("apps.accounts.urls.admin_urls")),

    # ── Stories & Reviews ──
    path("api/v1/writer/stories/", include("apps.stories.urls.writer")),
    path("api/v1/admin/stories/", include("apps.stories.urls.admin_urls")),
    path("api/v1/admin/reviews/", include("apps.stories.urls.review")),

    # ── Public routes ──
    path("api/v1/public/", include(categories_public)),
    path("api/v1/public/writers/", include(writers_public)),
    path("api/v1/public/", include(engagements_public)),
    path("api/v1/public/", include(series_public)),
    path("api/v1/public/", include(blogs_public)),
    path("api/v1/public/", include(videos_public)),
    path("api/v1/public/", include(search_public)),
    path("api/v1/public/", include(homepage_public)),
    path("api/v1/public/", include(banners_public)),
    path("api/v1/public/", include(contacts_public)),
    path("api/v1/public/", include(newsletters_public)),
    path("api/v1/public/", include(settings_public)),

    # ── Reader Dashboard routes ──
    path("api/v1/user/", include(engagements_reader)),

    # ── Writer Analytics ──
    path("api/v1/writer/", include(analytics_writer)),

    # ── Admin Management routes ──
    path("api/v1/admin/", include(categories_admin)),
    path("api/v1/admin/writers/", include(writers_admin)),
    path("api/v1/admin/", include(series_admin)),
    path("api/v1/admin/", include(blogs_admin)),
    path("api/v1/admin/", include(videos_admin)),
    path("api/v1/admin/", include(homepage_admin)),
    path("api/v1/admin/", include(banners_admin)),
    path("api/v1/admin/", include(contacts_admin)),
    path("api/v1/admin/", include(newsletters_admin)),
    path("api/v1/admin/", include(settings_admin)),
    path("api/v1/admin/", include(analytics_admin)),
    path("api/v1/admin/", include(audit_logs_admin)),
]
