"""
apps/newsletters/models.py — Newsletter Subscription Model per §21 & Phase 5 Spec
"""
import uuid
from django.db import models


class NewsletterSubscription(models.Model):
    """
    NewsletterSubscription model supporting double opt-in verification and unsubscribes per §21.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)

    verification_token = models.UUIDField(default=uuid.uuid4, unique=True)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "newsletter_subscriptions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"NewsletterSubscription({self.email}, verified={self.is_verified})"
