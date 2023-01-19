"""POST /api/login -- exchange credentials for a token pair."""

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tradecore_api.serializers import LoginSerializer, PrivateUserSerializer
from tradecore_api.tokens import issue_tokens


class LoginAPIView(APIView):
    """Authenticates an account and returns access and refresh tokens."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            # One message for "no such account" and "wrong password" alike, so
            # login cannot be used to enumerate which e-mails are registered.
            return Response(
                {
                    "error": {
                        "code": "invalid_credentials",
                        "message": "Invalid email or password.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {"user": PrivateUserSerializer(user).data, **issue_tokens(user)},
            status=status.HTTP_200_OK,
        )
