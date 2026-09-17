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

    @patch("apps.notifications.tasks.send_story_submission_email")
    def test_create_draft_and_submit_workflow(self, mock_email):
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
        mock_email.assert_called_once_with(str(submitted_story.id))

    @patch("apps.notifications.tasks.send_story_approval_email")
    def test_admin_approve_and_publish(self, mock_email):
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
        mock_email.assert_called_once_with(str(story.id))

        # Publish
        published_story = StoryService.publish_story(approved_story, self.admin_user)
        self.assertEqual(published_story.status, StoryStatus.PUBLISHED)
        self.assertIsNotNone(published_story.published_at)

        # Verify writer stats updated
        self.writer.refresh_from_db()
        self.assertEqual(self.writer.total_published_stories, 1)

    @patch("apps.notifications.tasks.send_story_rejection_email")
    def test_admin_reject_requires_feedback(self, mock_email):
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
        mock_email.assert_called_once_with(str(story.id))

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

    def test_content_moderation_blocked_on_malicious_script(self):
        """Test that malicious scripts in stories are blocked by moderation."""
        data = {
            "title": "Clean Title",
            "content": "<script>alert('malicious hack payload')</script>" + ("A normal story body. " * 10),
            "category_id": self.category.id,
        }
        story = StoryService.create_story(self.writer, data)
        with self.assertRaises(ServiceValidationError):
            StoryService.submit_story(story, self.writer)

    def test_content_moderation_flagged_on_spam_links(self):
        """Test that stories with high link density are marked FLAGGED on submission."""
        spam_links = " ".join([f"https://example{i}.com/promo" for i in range(7)])
        data = {
            "title": "Story with Multiple Links",
            "content": f"{spam_links} " + ("An exciting journey through the digital woods. " * 5),
            "category_id": self.category.id,
        }
        story = StoryService.create_story(self.writer, data)
        submitted = StoryService.submit_story(story, self.writer)
        self.assertEqual(submitted.moderation_status, "FLAGGED")

    def test_multi_chapter_creation_and_metrics_recalculation(self):
        """Test creating multiple chapters updates story metrics and ordering."""
        from apps.stories.services import ChapterService
        story = StoryService.create_story(self.writer, {
            "title": "Multi-Chapter Tale",
            "is_multi_chapter": True,
            "category_id": self.category.id,
        })
        self.assertTrue(story.is_multi_chapter)

        # Add Chapter 1
        ch1 = ChapterService.create_chapter(story, {
            "title": "Chapter 1: The Beginning",
            "content": "Word " * 200,
        }, self.writer_user)
        self.assertEqual(ch1.order, 1)
        self.assertEqual(ch1.word_count, 200)
        self.assertEqual(ch1.estimated_reading_time, 1)

        # Add Chapter 2
        ch2 = ChapterService.create_chapter(story, {
            "title": "Chapter 2: The Journey",
            "content": "Word " * 400,
        }, self.writer_user)
        self.assertEqual(ch2.order, 2)
        self.assertEqual(ch2.word_count, 400)
        self.assertEqual(ch2.estimated_reading_time, 2)

        story.refresh_from_db()
        self.assertEqual(story.word_count, 600)
        self.assertEqual(story.estimated_reading_time, 3)
        self.assertEqual(story.chapters.count(), 2)

    def test_delete_chapter_recompacts_ordering(self):
        """Test deleting a middle chapter shifts subsequent chapters down."""
        from apps.stories.services import ChapterService
        story = StoryService.create_story(self.writer, {
            "title": "Episodic Novella",
            "is_multi_chapter": True,
            "category_id": self.category.id,
        })
        ch1 = ChapterService.create_chapter(story, {"title": "Part 1", "content": "Text one"}, self.writer_user)
        ch2 = ChapterService.create_chapter(story, {"title": "Part 2", "content": "Text two"}, self.writer_user)
        ch3 = ChapterService.create_chapter(story, {"title": "Part 3", "content": "Text three"}, self.writer_user)

        self.assertEqual(list(story.chapters.values_list("order", flat=True)), [1, 2, 3])

        # Delete Chapter 2
        ChapterService.delete_chapter(ch2, self.writer_user)
        self.assertEqual(story.chapters.count(), 2)

        remaining_orders = list(story.chapters.order_by("order").values_list("order", flat=True))
        self.assertEqual(remaining_orders, [1, 2])

        ch3.refresh_from_db()
        self.assertEqual(ch3.order, 2)

    def test_reorder_chapters(self):
        """Test bulk reordering chapters."""
        from apps.stories.services import ChapterService
        story = StoryService.create_story(self.writer, {
            "title": "Reorderable Story",
            "is_multi_chapter": True,
            "category_id": self.category.id,
        })
        ch1 = ChapterService.create_chapter(story, {"title": "Ch 1"}, self.writer_user)
        ch2 = ChapterService.create_chapter(story, {"title": "Ch 2"}, self.writer_user)
        ch3 = ChapterService.create_chapter(story, {"title": "Ch 3"}, self.writer_user)

        # Reverse order: [ch3, ch2, ch1]
        ordered = ChapterService.reorder_chapters(story, [ch3.id, ch2.id, ch1.id], self.writer_user)
        self.assertEqual(ordered[0].id, ch3.id)
        self.assertEqual(ordered[0].order, 1)
        self.assertEqual(ordered[1].id, ch2.id)
        self.assertEqual(ordered[1].order, 2)
        self.assertEqual(ordered[2].id, ch1.id)
        self.assertEqual(ordered[2].order, 3)

    def test_unauthorized_chapter_access_forbidden(self):
        """Test other writers cannot modify another writer's story chapters."""
        from apps.stories.services import ChapterService
        other_user = User.objects.create_writer(
            email="other@tossatale.com", password="OtherPassword123!", first_name="Other"
        )
        story = StoryService.create_story(self.writer, {
            "title": "Protected Story",
            "category_id": self.category.id,
        })
        with self.assertRaises(PermissionDeniedError):
            ChapterService.create_chapter(story, {"title": "Hack Chapter"}, other_user)

    def test_writer_cannot_create_two_active_ongoing_series(self):
        """Test that a writer can only have one active ONGOING series at a time."""
        from common.constants import SeriesStatusType
        # 1st active ongoing series
        series1 = StoryService.create_story(self.writer, {
            "title": "Series One Ongoing",
            "is_multi_chapter": True,
            "series_status": SeriesStatusType.ONGOING,
            "category_id": self.category.id,
        })
        self.assertTrue(series1.is_multi_chapter)
        self.assertEqual(series1.series_status, SeriesStatusType.ONGOING)

        # Attempting 2nd active series must raise ServiceValidationError
        with self.assertRaises(ServiceValidationError):
            StoryService.create_story(self.writer, {
                "title": "Series Two Ongoing Attempt",
                "is_multi_chapter": True,
                "series_status": SeriesStatusType.ONGOING,
                "category_id": self.category.id,
            })

    def test_writer_can_create_series_after_completing_previous(self):
        """Test that completing the current series unlocks creating a new ongoing series."""
        from common.constants import SeriesStatusType
        # 1st series
        series1 = StoryService.create_story(self.writer, {
            "title": "First Complete Series",
            "is_multi_chapter": True,
            "series_status": SeriesStatusType.ONGOING,
            "category_id": self.category.id,
        })
        # Mark as Completed
        StoryService.toggle_series_status(series1, self.writer_user, new_status=SeriesStatusType.COMPLETED)
        series1.refresh_from_db()
        self.assertEqual(series1.series_status, SeriesStatusType.COMPLETED)

        # 2nd series is now allowed
        series2 = StoryService.create_story(self.writer, {
            "title": "Second Ongoing Series",
            "is_multi_chapter": True,
            "series_status": SeriesStatusType.ONGOING,
            "category_id": self.category.id,
        })
        self.assertTrue(series2.is_multi_chapter)
        self.assertEqual(series2.series_status, SeriesStatusType.ONGOING)

    def test_submit_and_approve_multi_chapter_series(self):
        """Test submitting a multi-chapter series for review and admin approval."""
        from apps.stories.services import ChapterService
        from common.constants import SeriesStatusType
        series = StoryService.create_story(self.writer, {
            "title": "A Multi Chapter Series Saga",
            "subtitle": "An epic serialized prose tale across five chapters.",
            "is_multi_chapter": True,
            "series_status": SeriesStatusType.ONGOING,
            "category_id": self.category.id,
        })
        ChapterService.create_chapter(
            series,
            {"title": "Chapter 1: The Beginning", "content": "Once upon a time in a bustling mountain valley, an adventurer began their great voyage through unexplored lands."},
            self.writer_user
        )

        submitted = StoryService.submit_story(series, self.writer)
        self.assertEqual(submitted.status, StoryStatus.PENDING_REVIEW)

        approved = StoryService.approve_story(submitted, self.admin_user)
        self.assertEqual(approved.status, StoryStatus.APPROVED)

        published = StoryService.publish_story(approved, self.admin_user)
        self.assertEqual(published.status, StoryStatus.PUBLISHED)
        self.assertEqual(published.chapters.count(), 1)
        self.assertEqual(published.chapters.first().status, StoryStatus.PUBLISHED)

    def test_chapter_by_chapter_submission_and_individual_publishing(self):
        """Test submitting, reviewing, and publishing individual chapters in an ongoing series."""
        from apps.stories.services import ChapterService
        from common.constants import SeriesStatusType

        series = StoryService.create_story(self.writer, {
            "title": "Epic Ongoing Chronicles",
            "subtitle": "A serial chronicle where chapters publish incrementally.",
            "is_multi_chapter": True,
            "series_status": SeriesStatusType.ONGOING,
            "category_id": self.category.id,
        })

        # Chapter 1: Created and Submitted
        ch1 = ChapterService.create_chapter(
            series,
            {"title": "Chapter 1", "content": "The hero enters the dark enchanted forest and discovers ancient secrets.", "status": StoryStatus.PENDING_REVIEW},
            self.writer_user
        )
        self.assertEqual(ch1.status, StoryStatus.PENDING_REVIEW)
        series.refresh_from_db()
        self.assertEqual(series.status, StoryStatus.PENDING_REVIEW)

        # Admin approves & publishes Chapter 1
        ChapterService.publish_chapter(ch1, self.admin_user)
        ch1.refresh_from_db()
        series.refresh_from_db()
        self.assertEqual(ch1.status, StoryStatus.PUBLISHED)
        self.assertEqual(series.status, StoryStatus.PUBLISHED)

        # Chapter 2: Added later in draft, then submitted
        ch2 = ChapterService.create_chapter(
            series,
            {"title": "Chapter 2", "content": "The party reaches the castle gates and prepares for an intense battle.", "status": StoryStatus.DRAFT},
            self.writer_user
        )
        self.assertEqual(ch2.status, StoryStatus.DRAFT)

        # Writer submits Chapter 2 for review
        ChapterService.submit_chapter(ch2, self.writer_user)
        ch2.refresh_from_db()
        self.assertEqual(ch2.status, StoryStatus.PENDING_REVIEW)

        # Admin rejects Chapter 2 with revision feedback
        ChapterService.reject_chapter(ch2, self.admin_user, feedback="Please polish dialogue in the final scene.")
        ch2.refresh_from_db()
        self.assertEqual(ch2.status, StoryStatus.REJECTED)
        self.assertEqual(ch2.rejection_feedback, "Please polish dialogue in the final scene.")
        # Series remains published because Chapter 1 is live
        series.refresh_from_db()
        self.assertEqual(series.status, StoryStatus.PUBLISHED)

        # Writer updates and resubmits Chapter 2
        ChapterService.update_chapter(ch2, {"content": "The party reaches the castle gates and talks with the guard commander peacefully.", "status": StoryStatus.PENDING_REVIEW}, self.writer_user)
        ch2.refresh_from_db()
        self.assertEqual(ch2.status, StoryStatus.PENDING_REVIEW)

        # Admin publishes Chapter 2
        ChapterService.publish_chapter(ch2, self.admin_user)
        ch2.refresh_from_db()
        self.assertEqual(ch2.status, StoryStatus.PUBLISHED)

