"""The Post model and its like relation."""

from django.conf import settings
from django.db import models

TITLE_MAX_LENGTH = 255


class Post(models.Model):
    """A short post written by one account and likeable by any account."""

    class ModerationStatus(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    description = models.TextField()
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_posts",
        blank=True,
    )
    moderation_status = models.CharField(
        max_length=16,
        choices=ModerationStatus.choices,
        default=ModerationStatus.APPROVED,
    )
    moderation_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Newest first is what the feed endpoint returns, and a stable order is
        # what keeps pagination from repeating or skipping rows.
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["author", "-created_at"], name="post_author_recent_idx"),
            models.Index(fields=["-created_at"], name="post_recent_idx"),
        ]

    def __str__(self) -> str:
        return self.title
