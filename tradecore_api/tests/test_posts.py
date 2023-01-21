"""Post creation, listing, ownership, likes and search."""

from django.urls import reverse
from rest_framework import status

from tradecore_api.models import Post
from tradecore_api.tests.base import APITestCaseWithAuth
from tradecore_api.tests.factories import PostFactory


class PostAuthTests(APITestCaseWithAuth):
    """Every post endpoint is closed to anonymous callers."""

    def test_list_requires_authentication(self):
        response = self.client.get(reverse("post-list-create"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        response = self.client.post(
            reverse("post-list-create"), {"title": "t", "description": "d"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_requires_authentication(self):
        post = PostFactory.create()
        response = self.client.get(reverse("post-detail", args=[post.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_like_requires_authentication(self):
        post = PostFactory.create()
        response = self.client.patch(
            reverse("post-like"), {"post_id": post.id, "action": "like"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PostCreateTests(APITestCaseWithAuth):
    """POST /api/post."""

    def test_create_assigns_the_authenticated_author(self):
        user = self.authenticate(self.make_user())
        response = self.client.post(
            reverse("post-list-create"),
            {"title": "Hello", "description": "World"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.get().author, user)

    def test_author_cannot_be_spoofed_in_the_body(self):
        """An author_id in the payload must be ignored, not honoured."""
        user = self.authenticate(self.make_user())
        victim = self.make_user()
        self.client.post(
            reverse("post-list-create"),
            {"title": "Hello", "description": "World", "author_id": victim.id},
            format="json",
        )
        self.assertEqual(Post.objects.get().author, user)

    def test_create_rejects_a_missing_title(self):
        self.authenticate(self.make_user())
        response = self.client.post(
            reverse("post-list-create"), {"description": "d"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_moderation_blocks_a_post(self):
        self.authenticate(self.make_user())
        response = self.client.post(
            reverse("post-list-create"),
            {"title": "spamword deal", "description": "buy now"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(Post.objects.count(), 0)


class PostListTests(APITestCaseWithAuth):
    """GET /api/post."""

    def test_list_returns_only_the_callers_posts(self):
        user = self.authenticate(self.make_user())
        PostFactory.create_batch(3, author=user)
        PostFactory.create_batch(2)
        response = self.client.get(reverse("post-list-create"))
        self.assertEqual(response.data["count"], 3)

    def test_list_is_paginated(self):
        user = self.authenticate(self.make_user())
        PostFactory.create_batch(25, author=user)
        response = self.client.get(reverse("post-list-create"))
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])

    def test_page_size_is_capped(self):
        user = self.authenticate(self.make_user())
        PostFactory.create_batch(30, author=user)
        response = self.client.get(reverse("post-list-create"), {"page_size": 100000})
        self.assertLessEqual(len(response.data["results"]), 100)

    def test_list_is_newest_first(self):
        user = self.authenticate(self.make_user())
        PostFactory.create(author=user, title="older")
        PostFactory.create(author=user, title="newer")
        response = self.client.get(reverse("post-list-create"))
        self.assertEqual(response.data["results"][0]["title"], "newer")

    def test_list_query_count_does_not_grow_with_rows(self):
        """Guards the annotate-based like counts against an N+1 regression."""
        user = self.authenticate(self.make_user())
        PostFactory.create_batch(2, author=user)
        with self.assertNumQueries(3):
            self.client.get(reverse("post-list-create"))
        PostFactory.create_batch(8, author=user)
        with self.assertNumQueries(3):
            self.client.get(reverse("post-list-create"))

    def test_search_filters_by_title(self):
        user = self.authenticate(self.make_user())
        PostFactory.create(author=user, title="Django tips")
        PostFactory.create(author=user, title="Cooking notes")
        response = self.client.get(reverse("post-list-create"), {"search": "django"})
        self.assertEqual(response.data["count"], 1)

    def test_search_also_matches_the_description(self):
        user = self.authenticate(self.make_user())
        PostFactory.create(author=user, title="Untitled", description="about postgres")
        response = self.client.get(reverse("post-list-create"), {"search": "postgres"})
        self.assertEqual(response.data["count"], 1)


class PostOwnershipTests(APITestCaseWithAuth):
    """One account must not be able to change another's posts."""

    def setUp(self):
        self.owner = self.make_user()
        self.stranger = self.make_user()
        self.post = PostFactory.create(author=self.owner)

    def test_stranger_cannot_read_the_post(self):
        self.authenticate(self.stranger)
        response = self.client.get(reverse("post-detail", args=[self.post.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stranger_cannot_update_the_post(self):
        self.authenticate(self.stranger)
        response = self.client.patch(
            reverse("post-detail", args=[self.post.id]),
            {"title": "hijacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.post.refresh_from_db()
        self.assertNotEqual(self.post.title, "hijacked")

    def test_stranger_cannot_delete_the_post(self):
        self.authenticate(self.stranger)
        response = self.client.delete(reverse("post-detail", args=[self.post.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Post.objects.filter(id=self.post.id).exists())

    def test_owner_can_update_the_post(self):
        self.authenticate(self.owner)
        response = self.client.patch(
            reverse("post-detail", args=[self.post.id]),
            {"title": "revised"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "revised")

    def test_owner_can_delete_the_post(self):
        self.authenticate(self.owner)
        response = self.client.delete(reverse("post-detail", args=[self.post.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(id=self.post.id).exists())

    def test_update_with_invalid_data_is_a_400(self):
        """An oversized title is a validation error, not a swallowed 404."""
        self.authenticate(self.owner)
        response = self.client.patch(
            reverse("post-detail", args=[self.post.id]),
            {"title": "x" * 400},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data["error"]["fields"])

    def test_updating_a_missing_post_is_a_404(self):
        self.authenticate(self.owner)
        response = self.client.patch(
            reverse("post-detail", args=[999999]), {"title": "x"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PostLikeTests(APITestCaseWithAuth):
    """PATCH /api/post/like."""

    def setUp(self):
        self.author = self.make_user()
        self.reader = self.make_user()
        self.post = PostFactory.create(author=self.author)

    def like(self, action="like"):
        return self.client.patch(
            reverse("post-like"),
            {"post_id": self.post.id, "action": action},
            format="json",
        )

    def test_a_reader_can_like_someone_elses_post(self):
        self.authenticate(self.reader)
        response = self.like()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["like_count"], 1)

    def test_liking_twice_counts_once(self):
        self.authenticate(self.reader)
        self.like()
        response = self.like()
        self.assertEqual(response.data["like_count"], 1)

    def test_unlike_removes_the_like(self):
        self.authenticate(self.reader)
        self.like()
        response = self.like("unlike")
        self.assertEqual(response.data["like_count"], 0)

    def test_unliking_a_post_never_liked_is_harmless(self):
        self.authenticate(self.reader)
        response = self.like("unlike")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["like_count"], 0)

    def test_an_unknown_action_is_rejected(self):
        self.authenticate(self.reader)
        response = self.like("smash")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_liking_a_missing_post_is_a_404(self):
        self.authenticate(self.reader)
        response = self.client.patch(
            reverse("post-like"), {"post_id": 999999, "action": "like"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_liked_by_me_is_reported_in_the_listing(self):
        self.authenticate(self.author)
        own = PostFactory.create(author=self.author)
        self.client.patch(
            reverse("post-like"), {"post_id": own.id, "action": "like"}, format="json"
        )
        response = self.client.get(reverse("post-list-create"))
        flags = {row["id"]: row["liked_by_me"] for row in response.data["results"]}
        self.assertTrue(flags[own.id])
        self.assertFalse(flags.get(self.post.id, False))
