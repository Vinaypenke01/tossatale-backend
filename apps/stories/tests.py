"""
apps/stories/tests.py — Comprehensive unit & integration test suite for Phase 2 Story Pipeline.
"""
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from common.constants import UserRole, StoryStatus, ReviewDecision
from common.exceptions import (
    ServiceValidationError,
    InvalidStateTransitionError,
    PermissionDeniedError,
)
from apps.accounts.models import User
from apps.writers.models import WriterProfile
from apps.categories.models import Category, Tag
from apps.stories.models import Story, StoryRevision, StoryReview
from apps.stories.services import StoryService


class StoryPipelineTestCase(TestCase):
    def setUp(self):
        # Create Users & Profiles
        self.writer_user = User.objects.create_writer(
            email="writer@tossatale.com",
            password="WriterPassword123!",
            first_name="Jane",
            last_name="Doe",
        )
        self.writer = WriterProfile.objects.create(
            user=self.writer_user,
            pen_name="Jane Writer",
            slug="jane-writer",
            bio="A passionate storyteller.",
        )

        self.admin_user = User.objects.create_superuser(
            email="admin@tossatale.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="User",
        )

        # Create Category
        self.category = Category.objects.create(
            name="Fiction",
            slug="fiction",
            description="Fictional stories",
            is_active=True,
        )

        # Base story payload
        self.sample_content = (
            "Once upon a time in a faraway realm, there lived a legendary writer who crafted tales "
            "that brought light to the dark corners of the kingdom. " * 3
        )

    @patch("apps.notifications.tasks.send_story_submission_email.delay")
    def test_create_draft_and_submit_workflow(self, mock_email_delay):
        """Test writer draft creation, revision snapshot, and submission to admin review."""
        data = {
            "title": "The Silent Kingdom",
            "content": self.sample_content,
            "category_id": self.category.id,
            "seo_title": "The Silent Kingdom - Fantasy Story",
            "seo_description": "Read the epic tale of the Silent Kingdom.",
        }

        # 1. Create Draft
        story = StoryService.create_story(self.writer, data)
        self.assertEqual(story.status, StoryStatus.DRAFT)
        self.assertEqual(story.writer, self.writer)
        self.assertGreater(story.word_count, 0)
        self.assertEqual(story.revisions.count(), 1)
        self.assertEqual(story.revisions.first().version_number, 1)

        # 2. Submit Story
        submitted_story = StoryService.submit_story(story, self.writer)
        self.assertEqual(submitted_story.status, StoryStatus.PENDING_REVIEW)
        self.assertIsNotNone(submitted_story.submitted_at)
        mock_email_delay.assert_called_once_with(str(submitted_story.id))

    @patch("apps.notifications.tasks.send_story_approval_email.delay")
    def test_admin_approve_and_publish(self, mock_email_delay):
        """Test admin approval and publishing workflow."""
        data = {
            "title": "Adventures in Code",
            "content": self.sample_content,
            "category_id": self.category.id,
        }
        story = StoryService.create_story(self.writer, data)
        StoryService.submit_story(story, self.writer)

        # Approve
        approved_story = StoryService.approve_story(story, self.admin_user)
        self.assertEqual(approved_story.status, StoryStatus.APPROVED)
        self.assertEqual(approved_story.reviewed_by, self.admin_user)
        self.assertEqual(StoryReview.objects.filter(story=story, decision=ReviewDecision.APPROVED).count(), 1)
        mock_email_delay.assert_called_once_with(str(story.id))

        # Publish
        published_story = StoryService.publish_story(approved_story, self.admin_user)
        self.assertEqual(published_story.status, StoryStatus.PUBLISHED)
        self.assertIsNotNone(published_story.published_at)

        # Verify writer stats updated
        self.writer.refresh_from_db()
        self.assertEqual(self.writer.total_published_stories, 1)

    @patch("apps.notifications.tasks.send_story_rejection_email.delay")
    def test_admin_reject_requires_feedback(self, mock_email_delay):
        """Test admin rejection requires mandatory feedback."""
        data = {
            "title": "Draft to Reject",
            "content": self.sample_content,
            "category_id": self.category.id,
        }
        story = StoryService.create_story(self.writer, data)
        StoryService.submit_story(story, self.writer)

        # Attempt rejection without feedback should raise ServiceValidationError
        with self.assertRaises(ServiceValidationError):
            StoryService.reject_story(story, self.admin_user, feedback="")

        # Reject with feedback
        feedback_msg = "Please expand on the second chapter and fix typos."
        rejected_story = StoryService.reject_story(story, self.admin_user, feedback=feedback_msg)
        self.assertEqual(rejected_story.status, StoryStatus.REJECTED)
        self.assertEqual(rejected_story.rejection_feedback, feedback_msg)
        mock_email_delay.assert_called_once_with(str(story.id))

        # Writer can re-submit rejected story
        resubmitted_story = StoryService.submit_story(rejected_story, self.writer)
        self.assertEqual(resubmitted_story.status, StoryStatus.PENDING_REVIEW)
        self.assertEqual(resubmitted_story.rejection_feedback, "")

    def test_invalid_state_transitions(self):
        """Test that illegal status transitions raise InvalidStateTransitionError."""
        data = {
            "title": "Invalid Transitions Test",
            "content": self.sample_content,
            "category_id": self.category.id,
        }
        story = StoryService.create_story(self.writer, data)

        # Cannot approve DRAFT directly
        with self.assertRaises(InvalidStateTransitionError):
            StoryService.approve_story(story, self.admin_user)

        # Cannot publish DRAFT directly
        with self.assertRaises(InvalidStateTransitionError):
            StoryService.publish_story(story, self.admin_user)

    def test_story_revision_tracking(self):
        """Test that updating a story draft logs new revision versions."""
        data = {
            "title": "Version 1 Title",
            "content": self.sample_content,
            "category_id": self.category.id,
        }
        story = StoryService.create_story(self.writer, data)
        self.assertEqual(story.revisions.count(), 1)

        # Update draft
        updated_data = {
            "title": "Version 2 Title",
            "content": self.sample_content + " Extra chapter added here.",
        }
        StoryService.update_story(story, updated_data, self.writer_user)
        self.assertEqual(story.revisions.count(), 2)
        latest_rev = story.revisions.first()
        self.assertEqual(latest_rev.version_number, 2)
        self.assertEqual(latest_rev.title, "Version 2 Title")

    def test_duplicate_story(self):
        """Test duplicating a story creates a new DRAFT with cloned content."""
        data = {
            "title": "Original Story",
            "content": self.sample_content,
            "category_id": self.category.id,
        }
        story = StoryService.create_story(self.writer, data)
        cloned = StoryService.duplicate_story(story, self.writer)

        self.assertNotEqual(story.id, cloned.id)
        self.assertEqual(cloned.title, "Original Story (Copy)")
        self.assertEqual(cloned.status, StoryStatus.DRAFT)
