"""Post endpoints: listing, creating, liking, updating and deleting."""

from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from tradecore_api.serializers import LikeActionSerializer, PostSerializer
from tradecore_api.services import PostService

SEARCH_QUERY_PARAM = "search"


class PostListCreateAPIView(ListCreateAPIView):
    """GET /api/post lists the caller's posts, POST /api/post writes one."""

    serializer_class = PostSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = PostService()

    def get_queryset(self):
        queryset = self.service.feed_for(self.request.user)
        return self.service.search(
            queryset, self.request.query_params.get(SEARCH_QUERY_PARAM, "")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = self.service.create(author=request.user, **serializer.validated_data)
        return Response(self.get_serializer(post).data, status=status.HTTP_201_CREATED)


class PostDetailAPIView(APIView):
    """GET, PATCH and DELETE for a single post the caller owns."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = PostService()

    def get(self, request, post_id: int):
        post = self.service.get_owned(request.user, post_id)
        return Response(PostSerializer(post).data)

    def patch(self, request, post_id: int):
        post = self.service.get_owned(request.user, post_id)
        serializer = PostSerializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = self.service.update(post, **serializer.validated_data)
        return Response(PostSerializer(updated).data)

    def delete(self, request, post_id: int):
        post = self.service.get_owned(request.user, post_id)
        self.service.delete(post)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostLikeAPIView(APIView):
    """PATCH /api/post/like -- like or unlike any post."""

    def patch(self, request):
        serializer = LikeActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        post, like_count = PostService().set_like(
            post_id=serializer.validated_data["post_id"],
            user=request.user,
            liked=serializer.liked,
        )
        return Response(
            {
                "post_id": post.id,
                "action": serializer.validated_data["action"],
                "like_count": like_count,
            }
        )
