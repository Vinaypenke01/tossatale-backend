"""
Common — Platform Constants
"""


class UserRole:
    ADMIN = "ADMIN"
    WRITER = "WRITER"
    USER = "USER"

    CHOICES = [
        (ADMIN, "Admin"),
        (WRITER, "Writer"),
        (USER, "User"),
    ]


class AuthProvider:
    EMAIL = "EMAIL"
    GOOGLE = "GOOGLE"

    CHOICES = [
        (EMAIL, "Email"),
        (GOOGLE, "Google"),
    ]


class StoryStatus:
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    SCHEDULED = "SCHEDULED"

    CHOICES = [
        (DRAFT, "Draft"),
        (PENDING_REVIEW, "Pending Review"),
        (APPROVED, "Approved"),
        (PUBLISHED, "Published"),
        (REJECTED, "Rejected"),
        (ARCHIVED, "Archived"),
        (SCHEDULED, "Scheduled"),
    ]

    # Valid source states for each transition
    SUBMIT_FROM = [DRAFT, REJECTED]
    APPROVE_FROM = [PENDING_REVIEW]
    REJECT_FROM = [PENDING_REVIEW]
    PUBLISH_FROM = [APPROVED]
    ARCHIVE_FROM = [PUBLISHED, APPROVED]


class ModerationStatus:
    NOT_REVIEWED = "NOT_REVIEWED"
    PASSED = "PASSED"
    FLAGGED = "FLAGGED"
    BLOCKED = "BLOCKED"

    CHOICES = [
        (NOT_REVIEWED, "Not Reviewed"),
        (PASSED, "Passed"),
        (FLAGGED, "Flagged"),
        (BLOCKED, "Blocked"),
    ]


class ReviewDecision:
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"

    CHOICES = [
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (CHANGES_REQUESTED, "Changes Requested"),
    ]


class SeriesStatus:
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    UNPUBLISHED = "UNPUBLISHED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

    CHOICES = [
        (DRAFT, "Draft"),
        (PUBLISHED, "Published"),
        (UNPUBLISHED, "Unpublished"),
        (COMPLETED, "Completed"),
        (ARCHIVED, "Archived"),
    ]


class SeriesItemStatus:
    UPCOMING = "UPCOMING"
    PUBLISHED = "PUBLISHED"
    COMPLETED = "COMPLETED"

    CHOICES = [
        (UPCOMING, "Upcoming"),
        (PUBLISHED, "Published"),
        (COMPLETED, "Completed"),
    ]


class CategoryType:
    STORY = "STORY"
    BLOG = "BLOG"
    VIDEO = "VIDEO"
    GENERAL = "GENERAL"

    CHOICES = [
        (STORY, "Story"),
        (BLOG, "Blog"),
        (VIDEO, "Video"),
        (GENERAL, "General"),
    ]


class BlogStatus:
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SCHEDULED = "SCHEDULED"
    ARCHIVED = "ARCHIVED"

    CHOICES = [
        (DRAFT, "Draft"),
        (PUBLISHED, "Published"),
        (SCHEDULED, "Scheduled"),
        (ARCHIVED, "Archived"),
    ]


class SharePlatform:
    WHATSAPP = "WHATSAPP"
    FACEBOOK = "FACEBOOK"
    X = "X"
    LINKEDIN = "LINKEDIN"
    COPY_LINK = "COPY_LINK"
    EMAIL = "EMAIL"
    OTHER = "OTHER"

    CHOICES = [
        (WHATSAPP, "WhatsApp"),
        (FACEBOOK, "Facebook"),
        (X, "X (Twitter)"),
        (LINKEDIN, "LinkedIn"),
        (COPY_LINK, "Copy Link"),
        (EMAIL, "Email"),
        (OTHER, "Other"),
    ]


class ContactStatus:
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    SPAM = "SPAM"

    CHOICES = [
        (NEW, "New"),
        (IN_PROGRESS, "In Progress"),
        (RESOLVED, "Resolved"),
        (SPAM, "Spam"),
    ]


class NotificationType:
    STORY_SUBMITTED = "STORY_SUBMITTED"
    STORY_APPROVED = "STORY_APPROVED"
    STORY_REJECTED = "STORY_REJECTED"
    STORY_FEEDBACK = "STORY_FEEDBACK"
    WRITER_REGISTERED = "WRITER_REGISTERED"
    WRITER_VERIFIED = "WRITER_VERIFIED"
    WRITER_UNVERIFIED = "WRITER_UNVERIFIED"
    CONTACT_MESSAGE_RECEIVED = "CONTACT_MESSAGE_RECEIVED"
    STORY_PUBLISHED = "STORY_PUBLISHED"
    SYSTEM_NOTIFICATION = "SYSTEM_NOTIFICATION"

    CHOICES = [
        (STORY_SUBMITTED, "Story Submitted"),
        (STORY_APPROVED, "Story Approved"),
        (STORY_REJECTED, "Story Rejected"),
        (STORY_FEEDBACK, "Story Feedback"),
        (WRITER_REGISTERED, "Writer Registered"),
        (WRITER_VERIFIED, "Writer Verified"),
        (WRITER_UNVERIFIED, "Writer Unverified"),
        (CONTACT_MESSAGE_RECEIVED, "Contact Message Received"),
        (STORY_PUBLISHED, "Story Published"),
        (SYSTEM_NOTIFICATION, "System Notification"),
    ]


class BannerType:
    HERO = "HERO"
    PROMOTIONAL = "PROMOTIONAL"
    NEWSLETTER = "NEWSLETTER"
    CATEGORY = "CATEGORY"

    CHOICES = [
        (HERO, "Hero"),
        (PROMOTIONAL, "Promotional"),
        (NEWSLETTER, "Newsletter"),
        (CATEGORY, "Category"),
    ]


class HomepageSectionKey:
    HERO_BANNER = "HERO_BANNER"
    FEATURED_STORY = "FEATURED_STORY"
    LATEST_STORIES = "LATEST_STORIES"
    TRENDING_STORIES = "TRENDING_STORIES"
    FEATURED_BLOGS = "FEATURED_BLOGS"
    FEATURED_WRITERS = "FEATURED_WRITERS"
    LATEST_VIDEOS = "LATEST_VIDEOS"
    CATEGORIES = "CATEGORIES"
    NEWSLETTER = "NEWSLETTER"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    FOOTER = "FOOTER"
    CONTACT = "CONTACT"
    STORY_SLOTS = "STORY_SLOTS"

    CHOICES = [
        (HERO_BANNER, "Hero Banner"),
        (FEATURED_STORY, "Featured Story"),
        (LATEST_STORIES, "Latest Stories"),
        (TRENDING_STORIES, "Trending Stories"),
        (FEATURED_BLOGS, "Featured Blogs"),
        (FEATURED_WRITERS, "Featured Writers"),
        (LATEST_VIDEOS, "Latest Videos"),
        (CATEGORIES, "Categories"),
        (NEWSLETTER, "Newsletter"),
        (ANNOUNCEMENT, "Announcement Bar"),
        (FOOTER, "Footer Settings"),
        (CONTACT, "Contact Settings"),
        (STORY_SLOTS, "Story Section Slots"),
    ]


class AuditAction:
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    PUBLISH = "PUBLISH"
    ARCHIVE = "ARCHIVE"
    ACTIVATE = "ACTIVATE"
    DEACTIVATE = "DEACTIVATE"
    VERIFY = "VERIFY"
    UNVERIFY = "UNVERIFY"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"

    CHOICES = [
        (CREATE, "Create"),
        (UPDATE, "Update"),
        (DELETE, "Delete"),
        (APPROVE, "Approve"),
        (REJECT, "Reject"),
        (PUBLISH, "Publish"),
        (ARCHIVE, "Archive"),
        (ACTIVATE, "Activate"),
        (DEACTIVATE, "Deactivate"),
        (VERIFY, "Verify"),
        (UNVERIFY, "Unverify"),
        (LOGIN, "Login"),
        (LOGOUT, "Logout"),
    ]
