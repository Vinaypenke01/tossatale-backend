"""
apps/moderation/services.py — ModerationService
Handles content moderation checks, text sanitization, and spam detection per Phase 2 spec.
"""
import re
from common.constants import ModerationStatus
from common.exceptions import ModerationFailedError

# Category-based prohibited patterns
MALICIOUS_PATTERNS = [
    r"<script[\s\S]*?>[\s\S]*?<\/script>",
    r"javascript\s*:",
    r"data:text\/html",
    r"onerror\s*=",
    r"onload\s*=",
    r"eval\s*\(",
]

PROHIBITED_KEYWORDS = [
    "malware", "ransomware", "trojan", "keylogger",
    "phishing", "credit card dump", "exploit payload",
    "hack tool", "ddos attack", "botnet",
]

SUSPICIOUS_SPAM_PATTERNS = [
    r"buy\s+viagra",
    r"casino\s+online",
    r"free\s+crypto\s+giveaway",
    r"guaranteed\s+profit",
    r"whatsapp\s+\+\d{10,}",
    r"telegram\s+@\w+",
]


class ModerationService:
    """
    ModerationService handles pre-submission content safety, spam detection,
    and text hygiene across the Tossatale platform.
    """

    @classmethod
    def check_content(cls, text: str) -> bool:
        """
        Scans text for prohibited keywords or malicious tokens.
        Raises ModerationFailedError if severe violations are found.
        """
        if not text:
            return True

        lower_text = text.lower()
        for kw in PROHIBITED_KEYWORDS:
            if kw in lower_text:
                raise ModerationFailedError(
                    f"Content moderation rejected: prohibited term '{kw}' detected."
                )

        for pat in MALICIOUS_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                raise ModerationFailedError("Content moderation rejected: malicious script or payload detected.")

        return True

    @classmethod
    def evaluate_moderation_status(cls, title: str, content: str) -> dict:
        """
        Evaluates title and content and returns moderation results without necessarily blocking.
        Returns: { 'passed': bool, 'status': ModerationStatus, 'flags': list[str] }
        """
        flags = []
        combined = f"{title}\n{content}"

        # 1. Check severe malicious payloads (hard block)
        for pat in MALICIOUS_PATTERNS:
            if re.search(pat, combined, re.IGNORECASE):
                return {
                    "passed": False,
                    "status": ModerationStatus.BLOCKED,
                    "flags": ["Malicious script or payload pattern detected"],
                }

        for kw in PROHIBITED_KEYWORDS:
            if kw in combined.lower():
                return {
                    "passed": False,
                    "status": ModerationStatus.BLOCKED,
                    "flags": [f"Prohibited keyword detected: {kw}"],
                }

        # 2. Check suspicious spam patterns (flag for admin review)
        for pat in SUSPICIOUS_SPAM_PATTERNS:
            if re.search(pat, combined, re.IGNORECASE):
                flags.append(f"Spam pattern matched: {pat}")

        # 3. Check link density (flag if > 5 external URLs in text)
        url_count = len(re.findall(r"https?:\/\/[^\s]+", combined))
        if url_count > 5:
            flags.append(f"High external link density ({url_count} links)")

        # 4. Check excessive repetition
        if cls.detect_spam(content):
            flags.append("Excessive word repetition")

        if flags:
            return {
                "passed": True,
                "status": ModerationStatus.FLAGGED,
                "flags": flags,
            }

        return {
            "passed": True,
            "status": ModerationStatus.PASSED,
            "flags": [],
        }

    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Strips dangerous script tags, event handlers, and unauthorized HTML.
        Uses nh3 / bleach allowlist from settings if installed, with regex fallback.
        """
        if not text:
            return ""

        from django.conf import settings
        allowed_tags = getattr(settings, "ALLOWED_HTML_TAGS", [
            "p", "br", "strong", "em", "u", "s", "blockquote",
            "h2", "h3", "h4", "ul", "ol", "li", "a", "img",
        ])
        allowed_attrs = getattr(settings, "ALLOWED_HTML_ATTRS", {
            "a": ["href", "title", "target"],
            "img": ["src", "alt", "width", "height"],
        })

        try:
            import nh3
            return nh3.clean(
                text,
                tags=set(allowed_tags),
                attributes={k: set(v) for k, v in allowed_attrs.items()} if isinstance(allowed_attrs, dict) else {},
            ).strip()
        except ImportError:
            pass

        try:
            import bleach
            return bleach.clean(
                text,
                tags=allowed_tags,
                attributes=allowed_attrs,
                strip=True,
            ).strip()
        except ImportError:
            # Fallback regex sanitization
            sanitized = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
            sanitized = re.sub(r"\s*on\w+=\S+", "", sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
            return sanitized.strip()

    @staticmethod
    def detect_spam(text: str) -> bool:
        """
        Detects excessive repetition or obvious spam patterns.
        """
        if not text:
            return False

        words = text.split()
        if len(words) > 30:
            max_repeat = 1
            curr_repeat = 1
            for i in range(1, len(words)):
                if words[i].lower() == words[i - 1].lower():
                    curr_repeat += 1
                    max_repeat = max(max_repeat, curr_repeat)
                else:
                    curr_repeat = 1

            if max_repeat > 15:
                return True

        return False
