"""
apps/homepage/views.py — Public Stitched Homepage and Admin Section Builder Views
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.cache import cache
from django.shortcuts import get_object_or_404

from common.permissions import IsAdmin
from common.responses import success_response
from apps.homepage.models import HomepageSection
from apps.homepage.serializers import HomepageStorySerializer, HomepageBlogSerializer
from apps.stories.models import Story
from apps.blogs.models import Blog
from apps.writers.models import WriterProfile
from apps.writers.serializers import WriterProfileSerializer
from apps.videos.models import Video
from apps.videos.serializers import VideoSerializer
from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer
from apps.engagements.models import StoryLike, StoryBookmark


class PublicHomepageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Stitches homepage data from enabled sections and caches in Redis for 15 minutes.
        Enriches user-specific engagement (likes/bookmarks) for authenticated readers.
        """
        cached_homepage = None
        try:
            cached_homepage = cache.get("homepage")
        except Exception:
            pass

        if cached_homepage:
            payload = dict(cached_homepage)
        else:
            all_sections = {sec.section_key: sec for sec in HomepageSection.objects.all()}
            payload = {}

            # Default fallback configs
            announcement_sec = all_sections.get("ANNOUNCEMENT")
            payload["announcement"] = announcement_sec.config if announcement_sec else {}

            footer_sec = all_sections.get("FOOTER")
            payload["footer"] = footer_sec.config if footer_sec else {}

            contact_sec = all_sections.get("CONTACT")
            payload["contact"] = contact_sec.config if contact_sec else {}

            # Check custom story section slot configs from Admin Builder
            story_section_config = all_sections.get("STORY_SLOTS")
            slot_config = story_section_config.config if story_section_config else {}
            payload["story_slots"] = slot_config

            # 1. Featured stories (2 stories) - defer heavy content/plain_text_content
            feat_ids = slot_config.get("featured_story_ids", [])
            if feat_ids and isinstance(feat_ids, list):
                feat_stories = list(
                    Story.objects.filter(id__in=feat_ids, status="PUBLISHED")
                    .defer("content", "plain_text_content")
                    .select_related("writer", "category")
                    .prefetch_related("story_tags__tag")
                )
                feat_dict = {str(s.id): s for s in feat_stories}
                ordered_feat = [feat_dict[str(sid)] for sid in feat_ids if str(sid) in feat_dict]
                if ordered_feat:
                    payload["featured_stories"] = HomepageStorySerializer(ordered_feat[:2], many=True).data

            if "featured_stories" not in payload or not payload["featured_stories"]:
                feat_stories = (
                    Story.objects.filter(status="PUBLISHED", is_featured=True)
                    .defer("content", "plain_text_content")
                    .select_related("writer", "category")
                    .prefetch_related("story_tags__tag")[:2]
                )
                if not feat_stories.exists():
                    feat_stories = (
                        Story.objects.filter(status="PUBLISHED")
                        .defer("content", "plain_text_content")
                        .select_related("writer", "category")
                        .prefetch_related("story_tags__tag")[:2]
                    )
                payload["featured_stories"] = HomepageStorySerializer(feat_stories, many=True).data

            # 2. Latest stories (3 stories) - defer heavy content/plain_text_content
            latest_ids = slot_config.get("latest_story_ids", [])
            if latest_ids and isinstance(latest_ids, list):
                latest_stories = list(
                    Story.objects.filter(id__in=latest_ids, status="PUBLISHED")
                    .defer("content", "plain_text_content")
                    .select_related("writer", "category")
                    .prefetch_related("story_tags__tag")
                )
                latest_dict = {str(s.id): s for s in latest_stories}
                ordered_latest = [latest_dict[str(sid)] for sid in latest_ids if str(sid) in latest_dict]
                if ordered_latest:
                    payload["latest_stories"] = HomepageStorySerializer(ordered_latest[:3], many=True).data

            if "latest_stories" not in payload or not payload["latest_stories"]:
                latest = (
                    Story.objects.filter(status="PUBLISHED")
                    .defer("content", "plain_text_content")
                    .select_related("writer", "category")
                    .prefetch_related("story_tags__tag")
                    .order_by("-published_at")[:3]
                )
                payload["latest_stories"] = HomepageStorySerializer(latest, many=True).data

            # 3. Trending stories (6 stories) - defer heavy content/plain_text_content
            trending_ids = slot_config.get("trending_story_ids", [])
            if trending_ids and isinstance(trending_ids, list):
                trending_stories = list(
                    Story.objects.filter(id__in=trending_ids, status="PUBLISHED")
                    .defer("content", "plain_text_content")
                    .select_related("writer", "category")
                    .prefetch_related("story_tags__tag")
                )
                trending_dict = {str(s.id): s for s in trending_stories}
                ordered_trending = [trending_dict[str(sid)] for sid in trending_ids if str(sid) in trending_dict]
                if ordered_trending:
                    payload["trending_stories"] = HomepageStorySerializer(ordered_trending[:6], many=True).data

            if "trending_stories" not in payload or not payload["trending_stories"]:
                trending = (
                    Story.objects.filter(status="PUBLISHED")
                    .defer("content", "plain_text_content")
                    .select_related("writer", "category")
                    .prefetch_related("story_tags__tag")
                    .order_by("-trending_score", "-views_count")[:6]
                )
                payload["trending_stories"] = HomepageStorySerializer(trending, many=True).data

            # Featured/Latest blogs (4 blogs) - lightweight serializer with deferred content
            blogs = (
                Blog.objects.filter(status="PUBLISHED")
                .defer("content", "plain_text_content", "featured_image")
                .select_related("category")
                .order_by("-published_at")[:4]
            )
            payload["featured_blogs"] = HomepageBlogSerializer(blogs, many=True).data

            # Featured writers
            writers = WriterProfile.objects.filter(is_verified=True).order_by("-total_published_stories")[:6]
            payload["featured_writers"] = WriterProfileSerializer(writers, many=True).data

            # Latest videos (4 short films)
            videos = Video.objects.filter(is_active=True).select_related("category").order_by("-created_at")[:4]
            payload["latest_videos"] = VideoSerializer(videos, many=True).data

            # Categories
            categories = Category.objects.filter(is_active=True)[:10]
            payload["categories"] = CategorySerializer(categories, many=True).data

            # Cache payload for 15 minutes (900 seconds)
            try:
                cache.set("homepage", payload, 900)
            except Exception:
                pass

        # Clone and enrich payload with user engagement state (likes & bookmarks)
        res_payload = {}
        for k, v in payload.items():
            if k in ["featured_stories", "latest_stories", "trending_stories"] and isinstance(v, list):
                res_payload[k] = [dict(item) for item in v]
            else:
                res_payload[k] = v

        if request.user and request.user.is_authenticated:
            user_liked_story_ids = {str(sid) for sid in StoryLike.objects.filter(user=request.user).values_list("story_id", flat=True)}
            user_bookmarked_story_ids = {str(sid) for sid in StoryBookmark.objects.filter(user=request.user).values_list("story_id", flat=True)}
            for key in ["featured_stories", "latest_stories", "trending_stories"]:
                if key in res_payload and isinstance(res_payload[key], list):
                    for st in res_payload[key]:
                        sid = str(st.get("id") or "")
                        st["is_liked"] = sid in user_liked_story_ids
                        st["is_bookmarked"] = sid in user_bookmarked_story_ids
        else:
            for key in ["featured_stories", "latest_stories", "trending_stories"]:
                if key in res_payload and isinstance(res_payload[key], list):
                    for st in res_payload[key]:
                        st["is_liked"] = False
                        st["is_bookmarked"] = False

        return success_response(data=res_payload, message="Homepage retrieved.")


class AdminHomepageSectionListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        sections = list(HomepageSection.objects.all().order_by("display_order"))
        sections_data = [
            {
                "id": str(sec.id),
                "section_key": sec.section_key,
                "title": sec.title,
                "is_enabled": sec.is_enabled,
                "display_order": sec.display_order,
                "config": sec.config,
            }
            for sec in sections
        ]

        sec_map = {sec.section_key: sec for sec in sections}
        announcement_sec = sec_map.get("ANNOUNCEMENT")
        featured_writers_sec = sec_map.get("FEATURED_WRITERS")
        footer_sec = sec_map.get("FOOTER")
        contact_sec = sec_map.get("CONTACT")
        story_slots_sec = sec_map.get("STORY_SLOTS")

        data = {
            "sections": sections_data,
            "announcement": announcement_sec.config if announcement_sec else {},
            "featured_writers": featured_writers_sec.config if featured_writers_sec else {},
            "footer": footer_sec.config if footer_sec else {},
            "contact": contact_sec.config if contact_sec else {},
            "story_slots": story_slots_sec.config if story_slots_sec else {},
        }
        return success_response(data=data)

    def patch(self, request, pk=None):
        if pk:
            sec = get_object_or_404(HomepageSection, pk=pk)
            if "is_enabled" in request.data:
                sec.is_enabled = request.data["is_enabled"]
            if "display_order" in request.data:
                sec.display_order = request.data["display_order"]
            if "config" in request.data:
                sec.config = request.data["config"]
            sec.updated_by = request.user
            sec.save()
        else:
            # Bulk update settings from builder
            if "announcement" in request.data:
                sec, _ = HomepageSection.objects.get_or_create(section_key="ANNOUNCEMENT")
                sec.config = request.data["announcement"]
                sec.updated_by = request.user
                sec.save()

            if "featured_writers" in request.data:
                sec, _ = HomepageSection.objects.get_or_create(section_key="FEATURED_WRITERS")
                sec.config = request.data["featured_writers"]
                sec.updated_by = request.user
                sec.save()

            if "footer" in request.data:
                sec, _ = HomepageSection.objects.get_or_create(section_key="FOOTER")
                sec.config = request.data["footer"]
                sec.updated_by = request.user
                sec.save()

            if "contact" in request.data:
                sec, _ = HomepageSection.objects.get_or_create(section_key="CONTACT")
                sec.config = request.data["contact"]
                sec.updated_by = request.user
                sec.save()

            if "story_slots" in request.data:
                sec, _ = HomepageSection.objects.get_or_create(section_key="STORY_SLOTS")
                sec.config = request.data["story_slots"]
                sec.updated_by = request.user
                sec.save()

        # Invalidate homepage cache
        cache.delete("homepage")
        return success_response(message="Homepage & Site Builder changes published live.")
