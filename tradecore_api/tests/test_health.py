"""The readiness probe."""

from django.urls import reverse
from rest_framework import status

from tradecore_api.tests.base import APITestCaseWithAuth


class HealthTests(APITestCaseWithAuth):
    """GET /api/health."""

    def test_health_is_public(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_reports_the_database(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["database"], "ok")

    def test_health_names_the_active_providers(self):
        """A deployment missing its keys is visible from the probe alone."""
        response = self.client.get(reverse("health"))
        self.assertEqual(
            response.data["providers"],
            {"geolocation": "null", "holiday": "null", "moderation": "keyword"},
        )
