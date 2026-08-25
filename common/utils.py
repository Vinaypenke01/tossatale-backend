"""
Common — Utility Functions
"""
import re
import math
from django.utils.text import slugify as django_slugify


import uuid as _uuid


def generate_unique_slug(model_class, title: str, field: str = "slug", instance_id=None) -> str:
    """
    Generate a unique slug for a model instance in a single query.
    Appends a numeric suffix if a collision exists.
    """
    base_slug = django_slugify(title) or "item"
    qs = model_class.objects.filter(**{f"{field}__startswith": base_slug})
    if instance_id:
        qs = qs.exclude(id=instance_id)
    existing = set(qs.values_list(field, flat=True))
    if base_slug not in existing:
        return base_slug
    counter = 1
    while f"{base_slug}-{counter}" in existing:
        counter += 1
    return f"{base_slug}-{counter}"


def get_engagement_context(request) -> dict:
    """
    Returns liked_ids and bookmarked_ids sets for the current user.
    Enriches serializer context in list views to avoid N+1 queries.
    """
    if not request or not hasattr(request, "user") or not request.user.is_authenticated:
        return {"liked_ids": set(), "bookmarked_ids": set()}
    from apps.engagements.models import StoryLike, StoryBookmark
    liked_ids = set(
        StoryLike.objects.filter(user=request.user).values_list("story_id", flat=True)
    )
    bookmarked_ids = set(
        StoryBookmark.objects.filter(user=request.user).values_list("story_id", flat=True)
    )
    return {"liked_ids": liked_ids, "bookmarked_ids": bookmarked_ids}


def resolve_category(category_input: str):
    """
    Resolves a Category from a slug or UUID string without auto-activating or auto-creating.
    """
    from apps.categories.models import Category
    if not category_input:
        return None
    obj = Category.objects.filter(slug=category_input).first()
    if obj:
        return obj
    try:
        _uuid.UUID(str(category_input))
        return Category.objects.filter(id=category_input).first()
    except (ValueError, TypeError):
        return None


def calculate_reading_time(text: str, words_per_minute: int = 238) -> int:
    """
    Calculate estimated reading time in minutes.
    Average adult reading speed: 238 wpm.
    Returns minimum 1 minute.
    """
    word_count = len(re.findall(r"\w+", text or ""))
    minutes = math.ceil(word_count / words_per_minute)
    return max(1, minutes)


def calculate_word_count(text: str) -> int:
    """Count words in plain text."""
    return len(re.findall(r"\w+", text or ""))


def sanitize_html(content: str) -> str:
    """
    Sanitize HTML content using bleach.
    Used for blog posts (writer stories are text-only per §2).
    """
    import bleach
    from django.conf import settings

    return bleach.clean(
        content,
        tags=getattr(settings, "ALLOWED_HTML_TAGS", []),
        attributes=getattr(settings, "ALLOWED_HTML_ATTRS", {}),
        strip=True,
    )


def extract_youtube_id(url: str) -> str | None:
    """
    Extract YouTube video ID from various YouTube URL formats.
    e.g. https://www.youtube.com/watch?v=abc123 → abc123
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url or "")
        if match:
            return match.group(1)
    return None


def build_youtube_embed_url(video_id: str) -> str:
    """Build YouTube embed URL from video ID."""
    return f"https://www.youtube.com/embed/{video_id}"
