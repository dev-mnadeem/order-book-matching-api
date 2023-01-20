"""Shared test helpers."""

from django.test import override_settings
from rest_framework.test import APITestCase

from tradecore_api.tests.factories import DEFAULT_PASSWORD, UserFactory
from tradecore_api.tokens import issue_tokens

# Pin both enrichment providers to their offline implementations for the whole
# suite.  Left on "auto" a developer with real keys in their environment would
# run a different -- and network-dependent -- test suite from CI.
offline_providers = override_settings(
    GEOLOCATION_PROVIDER="null",
    HOLIDAY_PROVIDER="null",
    MODERATION_PROVIDER="keyword",
    ABSTRACT_GEOLOCATION_API_KEY="",
    ABSTRACT_HOLIDAYS_API_KEY="",
    ANTHROPIC_API_KEY="",
)


@offline_providers
class APITestCaseWithAuth(APITestCase):
    """An APITestCase that can authenticate as a given user."""

    password = DEFAULT_PASSWORD

    def make_user(self, **kwargs):
        return UserFactory.create(**kwargs)

    def authenticate(self, user):
        """Send ``Authorization: JWT <access>`` on every later request."""
        token = issue_tokens(user)["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"JWT {token}")
        return user

    def auth_header(self, user) -> dict:
        return {"HTTP_AUTHORIZATION": f"JWT {issue_tokens(user)['token']}"}
