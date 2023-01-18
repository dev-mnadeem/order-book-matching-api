"""Serializers for posts."""

from rest_framework import serializers

from tradecore_api.models import Post


class PostSerializer(serializers.ModelSerializer):
    """A post as returned to clients."""

    author_id = serializers.IntegerField(source="author.id", read_only=True)
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    # Supplied by PostService.feed_for's annotations; the defaults keep the
    # serializer usable for a freshly created instance that has none.
    like_count = serializers.IntegerField(read_only=True, default=0)
    liked_by_me = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "description",
            "author_id",
            "author_name",
            "like_count",
            "liked_by_me",
            "moderation_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "author_id",
            "author_name",
            "like_count",
            "liked_by_me",
            "moderation_status",
            "created_at",
            "updated_at",
        )


class LikeActionSerializer(serializers.Serializer):
    """Validates a like/unlike instruction."""

    LIKE = "like"
    UNLIKE = "unlike"

    post_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=[LIKE, UNLIKE])

    @property
    def liked(self) -> bool:
        return self.validated_data["action"] == self.LIKE
