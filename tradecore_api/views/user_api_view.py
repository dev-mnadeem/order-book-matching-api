"""GET /api/user/<id> and GET /api/me -- account lookups."""

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from tradecore_api.models import User
from tradecore_api.serializers import PrivateUserSerializer, UserSerializer


class UserAPIView(APIView):
    """Returns one account.

    Authentication is required and the response omits the enrichment fields --
    an account's approximate location is not public data.
    """

    def get(self, request, user_id: int):
        user = get_object_or_404(User, id=user_id, is_active=True)
        serializer = (
            PrivateUserSerializer(user) if user == request.user else UserSerializer(user)
        )
        return Response({"user": serializer.data})


class CurrentUserAPIView(APIView):
    """Returns the account that owns the presented token."""

    def get(self, request):
        return Response({"user": PrivateUserSerializer(request.user).data})
