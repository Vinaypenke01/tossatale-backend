"""
apps/engagements/tests.py — Unit & Integration tests for Phase 3 Reader Engagements.
"""
from django.test import TestCase
from common.constants import StoryStatus
from common.exceptions import DuplicateResourceError, ServiceValidationError
from apps.accounts.models import User
from apps.writers.models import WriterProfile
from apps.categories.models import Category
from apps.stories.models import Story
from apps.engagements.models import StoryLike, StoryBookmark, StoryView, RecentlyRead
from apps.engagements.services import EngagementService


class ReaderEngagementTestCase(TestCase):
    def setUp(self):
        self.writer_user = User.objects.create_writer(
            email="writer@tossatale.com", password="Password123!"
        )
        self.writer = WriterProfile.objects.create(
            user=self.writer_user, pen_name="Jane Writer", slug="jane-writer"
        )
        self.reader_user = User.objects.create_user(
            email="reader@tossatale.com", password="Password123!"
        )
        self.category = Category.objects.create(
            name="Fiction", slug="fiction", is_active=True
        )

        self.published_story = Story.objects.create(
            writer=self.writer,
            created_by=self.writer_user,
            title="The Endless Voyage",
            slug="the-endless-voyage",
            content="A rich narrative content that spans over one hundred words to fulfill minimum length validation rules. " * 3,
            category=self.category,
            status=StoryStatus.PUBLISHED,
        )

    def test_like_and_unlike_story(self):
        """Test liking and unliking a published story."""
        like = EngagementService.like_story(self.reader_user, self.published_story)
        self.assertEqual(like.user, self.reader_user)

        self.published_story.refresh_from_db()
        self.writer.refresh_from_db()
        self.assertEqual(self.published_story.likes_count, 1)
        self.assertEqual(self.writer.total_likes, 1)

        # Attempting duplicate like raises DuplicateResourceError
        with self.assertRaises(DuplicateResourceError):
            EngagementService.like_story(self.reader_user, self.published_story)

        # Unlike story
        EngagementService.unlike_story(self.reader_user, self.published_story)
        self.published_story.refresh_from_db()
        self.writer.refresh_from_db()
        self.assertEqual(self.published_story.likes_count, 0)
        self.assertEqual(self.writer.total_likes, 0)

    def test_bookmark_and_remove_bookmark(self):
        """Test bookmarking a story."""
        bookmark = EngagementService.bookmark_story(self.reader_user, self.published_story)
        self.published_story.refresh_from_db()
        self.assertEqual(self.published_story.bookmarks_count, 1)

        # Remove bookmark
        EngagementService.remove_bookmark(self.reader_user, self.published_story)
        self.published_story.refresh_from_db()
        self.assertEqual(self.published_story.bookmarks_count, 0)

    def test_record_view_and_deduplication(self):
        """Test story view recording and 30-minute unique view window deduplication."""
        # First view -> is_unique_view True
        v1 = EngagementService.record_view(
            story=self.published_story,
            user=self.reader_user,
            reading_duration=120,
            completion_percentage=85.0,
        )
        self.assertTrue(v1.is_unique_view)

        # Second view within 30 minutes -> is_unique_view False
        v2 = EngagementService.record_view(
            story=self.published_story,
            user=self.reader_user,
            reading_duration=60,
            completion_percentage=100.0,
        )
        self.assertFalse(v2.is_unique_view)

        # Check recently read history updated automatically
        history = RecentlyRead.objects.filter(user=self.reader_user, story=self.published_story).first()
        self.assertIsNotNone(history)
        self.assertTrue(history.completed)
