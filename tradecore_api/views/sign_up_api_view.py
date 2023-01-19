"""POST /api/signup -- create an account."""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tradecore_api.serializers import PrivateUserSerializer, SignUpSerializer
from tradecore_api.services import AccountService, client_ip
from tradecore_api.tokens import issue_tokens


class SignUpAPIView(APIView):
    """Registration is the one write endpoint open to anonymous callers."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AccountService().register(
            **serializer.validated_data,
            ip_address=client_ip(request),
        )
        return Response(
            {"user": PrivateUserSerializer(user).data, **issue_tokens(user)},
            status=status.HTTP_201_CREATED,
        )
