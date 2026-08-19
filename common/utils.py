"""
Common — Utility Functions
"""
import re
import math
from django.utils.text import slugify as django_slugify


def generate_unique_slug(model_class, title: str, field: str = "slug") -> str:
    """
    Generate a unique slug for a model instance.
    Appends a numeric suffix if a collision exists.
    """
    base_slug = django_slugify(title)
    slug = base_slug
    counter = 1
    while model_class.objects.filter(**{field: slug}).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


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
