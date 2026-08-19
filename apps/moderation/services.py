"""
apps/moderation/services.py — ModerationService
Handles content moderation checks, text sanitization, and spam detection per Phase 2 spec.
"""
import re
from common.exceptions import ModerationFailedError

PROHIBITED_KEYWORDS = [
    "malware", "phishing", "hate_speech_placeholder", "illegal_content"
]


class ModerationService:
    """
    ModerationService handles pre-submission content safety and text hygiene.
    """

    @staticmethod
    def check_content(text: str) -> bool:
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
                    f"Content moderation failed: restricted keyword '{kw}' detected."
                )
        return True

    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Strips dangerous script tags or inline event handlers from prose text.
        """
        if not text:
            return ""

        # Remove script tags
        sanitized = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Remove onerror, onload attributes
        sanitized = re.sub(r"\s*on\w+=\".*?\"", "", sanitized, flags=re.IGNORECASE)
        return sanitized.strip()

    @staticmethod
    def detect_spam(text: str) -> bool:
        """
        Detects excessive repetition or obvious spam patterns.
        """
        if not text:
            return False

        # Flag if same word is repeated continuously more than 20 times
        words = text.split()
        if len(words) > 50:
            max_repeat = 1
            curr_repeat = 1
            for i in range(1, len(words)):
                if words[i].lower() == words[i - 1].lower():
                    curr_repeat += 1
                    max_repeat = max(max_repeat, curr_repeat)
                else:
                    curr_repeat = 1

            if max_repeat > 20:
                raise ModerationFailedError("Content flagged as spam due to excessive word repetition.")

        return False
