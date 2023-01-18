"""Everything the API does to a post, kept out of the views."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, QuerySet
from django.shortcuts import get_object_or_404

from tradecore_api.exceptions import PostRejected
from tradecore_api.models import Post, User
from tradecore_api.providers import ModerationProvider, get_moderation_provider


class PostService:
    """Create, read, update, delete and like posts.

    Ownership is enforced here rather than in each view, so there is one place
    to read when answering "can this account touch that post".
    """

    def __init__(self, moderation_provider: ModerationProvider | None = None) -> None:
        self._moderation_provider = moderation_provider

    @property
    def moderation_provider(self) -> ModerationProvider:
        # Resolved lazily so that constructing a service never builds an API
        # client for a request that turns out not to need moderation.
        if self._moderation_provider is None:
            self._moderation_provider = get_moderation_provider()
        return self._moderation_provider

    def feed_for(self, user: User) -> QuerySet[Post]:
        """Posts written by ``user``, newest first, ready to serialise.

        ``annotate`` computes the like count and the viewer's own like in the
        same query as the page itself, so rendering N posts stays at a fixed
        number of queries rather than two more per row.  The ordering is
        repeated explicitly because the GROUP BY that ``annotate`` introduces
        makes Django drop ``Meta.ordering``, and an unordered queryset makes
        pagination repeat and skip rows.
        """
        liked_by_viewer = User.objects.filter(pk=user.pk, liked_posts=OuterRef("pk"))
        return (
            Post.objects.filter(author=user)
            .select_related("author")
            .annotate(
                like_count=Count("likes", distinct=True),
                liked_by_me=Exists(liked_by_viewer),
            )
            .order_by("-created_at", "-id")
        )

    def search(self, queryset: QuerySet[Post], term: str) -> QuerySet[Post]:
        """Narrow a post queryset to rows matching ``term``."""
        term = (term or "").strip()
        if not term:
            return queryset
        return queryset.filter(title__icontains=term) | queryset.filter(
            description__icontains=term
        )

    def get_owned(self, user: User, post_id: int) -> Post:
        """Fetch a post that ``user`` is allowed to modify, or raise Http404.

        Deliberately a 404 and not a 403: telling a stranger that post 7 exists
        but belongs to someone else is itself a small leak.
        """
        return get_object_or_404(Post, id=post_id, author=user)

    def create(self, *, author: User, title: str, description: str) -> Post:
        """Moderate and store a new post."""
        verdict = self.moderation_provider.review(title, description)
        if not verdict.allowed:
            raise PostRejected(verdict.reason or "Post rejected by moderation.")
        return Post.objects.create(
            author=author,
            title=title,
            description=description,
            moderation_status=Post.ModerationStatus.APPROVED,
        )

    def update(self, post: Post, **fields) -> Post:
        """Re-moderate and apply a partial update."""
        title = fields.get("title", post.title)
        description = fields.get("description", post.description)
        verdict = self.moderation_provider.review(title, description)
        if not verdict.allowed:
            raise PostRejected(verdict.reason or "Post rejected by moderation.")

        for name, value in fields.items():
            setattr(post, name, value)
        post.save(update_fields=[*fields.keys(), "updated_at"])
        return post

    def delete(self, post: Post) -> None:
        """Remove a post."""
        post.delete()

    @transaction.atomic
    def set_like(self, *, post_id: int, user: User, liked: bool) -> tuple[Post, int]:
        """Like or unlike a post, returning it with its new like count.

        ``select_for_update`` serialises concurrent likes on the same row so a
        burst of requests cannot interleave into a wrong count.
        """
        post = get_object_or_404(Post.objects.select_for_update(), id=post_id)
        if liked:
            post.likes.add(user)
        else:
            post.likes.remove(user)
        return post, post.likes.count()
