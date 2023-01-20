"""GET /api/health -- readiness probe."""

from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tradecore_api.providers import (
    get_geolocation_provider,
    get_holiday_provider,
    get_moderation_provider,
)


class HealthAPIView(APIView):
    """Reports whether the database answers and which providers are wired in.

    Naming the providers makes a misconfigured deployment visible immediately:
    seeing "null" in production is the signal that a key never made it into
    the environment.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            database_ok = True
        except Exception:  # the probe reports a failure, it does not raise one
            database_ok = False

        return Response(
            {
                "status": "ok" if database_ok else "degraded",
                "database": "ok" if database_ok else "unavailable",
                "providers": {
                    "geolocation": get_geolocation_provider().name,
                    "holiday": get_holiday_provider().name,
                    "moderation": get_moderation_provider().name,
                },
            },
            status=status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
