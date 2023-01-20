"""URL map for the posts API."""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from tradecore_api.views import (
    CurrentUserAPIView,
    HealthAPIView,
    LoginAPIView,
    PostDetailAPIView,
    PostLikeAPIView,
    PostListCreateAPIView,
    SignUpAPIView,
    UserAPIView,
)

urlpatterns = [
    path("health", HealthAPIView.as_view(), name="health"),
    path("signup", SignUpAPIView.as_view(), name="signup"),
    path("login", LoginAPIView.as_view(), name="login"),
    path("token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("me", CurrentUserAPIView.as_view(), name="me"),
    path("user/<int:user_id>", UserAPIView.as_view(), name="user"),
    # "post/like" is declared before "post/<int:post_id>" so the literal wins.
    path("post/like", PostLikeAPIView.as_view(), name="post-like"),
    path("post", PostListCreateAPIView.as_view(), name="post-list-create"),
    path("post/<int:post_id>", PostDetailAPIView.as_view(), name="post-detail"),
]
