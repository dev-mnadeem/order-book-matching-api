"""Providers, the registry and the enrichment service."""

import datetime

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings

from tradecore_api.providers import (
    get_geolocation_provider,
    get_holiday_provider,
    get_moderation_provider,
)
from tradecore_api.providers.base import Geolocation
from tradecore_api.providers.geolocation import (
    AbstractApiGeolocationProvider,
    NullGeolocationProvider,
    is_routable,
)
from tradecore_api.providers.holidays import AbstractApiHolidayProvider, NullHolidayProvider
from tradecore_api.providers.moderation import (
    ClaudeModerationProvider,
    KeywordModerationProvider,
)
from tradecore_api.services import AccountService


class RegistrySelectionTests(SimpleTestCase):
    """ "auto" picks the real provider only when a key is present."""

    @override_settings(GEOLOCATION_PROVIDER="auto", ABSTRACT_GEOLOCATION_API_KEY="")
    def test_geolocation_falls_back_without_a_key(self):
        self.assertEqual(get_geolocation_provider().name, "null")

    @override_settings(GEOLOCATION_PROVIDER="auto", ABSTRACT_GEOLOCATION_API_KEY="k")
    def test_geolocation_uses_the_service_with_a_key(self):
        self.assertEqual(get_geolocation_provider().name, "abstractapi")

    @override_settings(HOLIDAY_PROVIDER="auto", ABSTRACT_HOLIDAYS_API_KEY="")
    def test_holiday_falls_back_without_a_key(self):
        self.assertEqual(get_holiday_provider().name, "null")

    @override_settings(MODERATION_PROVIDER="auto", ANTHROPIC_API_KEY="")
    def test_moderation_falls_back_without_a_key(self):
        self.assertEqual(get_moderation_provider().name, "keyword")

    @override_settings(MODERATION_PROVIDER="auto", ANTHROPIC_API_KEY="k")
    def test_moderation_uses_claude_with_a_key(self):
        self.assertEqual(get_moderation_provider().name, "claude")

    @override_settings(GEOLOCATION_PROVIDER="abstractapi", ABSTRACT_GEOLOCATION_API_KEY="")
    def test_pinning_a_provider_without_its_key_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            get_geolocation_provider()

    @override_settings(MODERATION_PROVIDER="nonsense")
    def test_an_unknown_provider_name_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            get_moderation_provider()


class RoutableAddressTests(SimpleTestCase):
    """Private addresses are never sent to a paid lookup."""

    def test_loopback_is_not_routable(self):
        self.assertFalse(is_routable("127.0.0.1"))

    def test_private_range_is_not_routable(self):
        self.assertFalse(is_routable("192.168.1.10"))

    def test_garbage_is_not_routable(self):
        self.assertFalse(is_routable("not-an-ip"))

    def test_a_public_address_is_routable(self):
        self.assertTrue(is_routable("81.2.69.142"))


class NullProviderTests(SimpleTestCase):
    """The offline implementations answer without touching the network."""

    def test_null_geolocation_is_empty(self):
        located = NullGeolocationProvider().locate("81.2.69.142")
        self.assertEqual(located.country_code, "")
        self.assertEqual(located.as_json()["city"], "")

    def test_null_holiday_is_always_false(self):
        self.assertFalse(NullHolidayProvider().is_holiday("GB", datetime.date(2024, 12, 25)))


class GeolocationParsingTests(SimpleTestCase):
    """Mapping an Abstract API body onto the DTO."""

    def test_fields_are_mapped(self):
        located = AbstractApiGeolocationProvider.parse(
            {
                "country_code": "NO",
                "country": "Norway",
                "city": "Oslo",
                "latitude": 59.91,
                "longitude": 10.75,
            }
        )
        self.assertEqual(located.country_code, "NO")
        self.assertEqual(located.city, "Oslo")
        self.assertAlmostEqual(located.latitude, 59.91)

    def test_missing_fields_become_blanks_not_errors(self):
        located = AbstractApiGeolocationProvider.parse({})
        self.assertEqual(located.country_code, "")
        self.assertIsNone(located.latitude)

    def test_an_unparseable_latitude_becomes_none(self):
        located = AbstractApiGeolocationProvider.parse({"latitude": "north-ish"})
        self.assertIsNone(located.latitude)


class GeolocationCacheTests(TestCase):
    """A repeated address must not be looked up twice."""

    def setUp(self):
        cache.clear()

    def test_a_private_address_never_calls_out(self):
        provider = AbstractApiGeolocationProvider("key")
        calls = []
        provider_module_get_json = "tradecore_api.providers.geolocation.get_json"
        with self.settings():
            import unittest.mock

            with unittest.mock.patch(provider_module_get_json) as mocked:
                mocked.side_effect = lambda *a, **k: calls.append(a)
                provider.locate("127.0.0.1")
        self.assertEqual(calls, [])

    def test_the_second_lookup_is_served_from_cache(self):
        import unittest.mock

        provider = AbstractApiGeolocationProvider("key")
        payload = {"country_code": "NO", "city": "Oslo"}
        with unittest.mock.patch(
            "tradecore_api.providers.geolocation.get_json", return_value=payload
        ) as mocked:
            first = provider.locate("81.2.69.142")
            second = provider.locate("81.2.69.142")
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(first.city, "Oslo")
        self.assertEqual(second.city, "Oslo")

    def test_a_failed_lookup_yields_an_empty_location(self):
        import unittest.mock

        provider = AbstractApiGeolocationProvider("key")
        with unittest.mock.patch(
            "tradecore_api.providers.geolocation.get_json", return_value=None
        ):
            located = provider.locate("81.2.69.142")
        self.assertEqual(located, Geolocation())


class HolidayProviderTests(TestCase):
    """The holiday lookup and its caching."""

    def setUp(self):
        cache.clear()

    def test_no_country_means_no_call(self):
        import unittest.mock

        with unittest.mock.patch("tradecore_api.providers.holidays.get_json") as mocked:
            result = AbstractApiHolidayProvider("key").is_holiday("", datetime.date.today())
        self.assertFalse(result)
        mocked.assert_not_called()

    def test_a_non_empty_list_means_holiday(self):
        import unittest.mock

        with unittest.mock.patch(
            "tradecore_api.providers.holidays.get_json",
            return_value=[{"name": "Christmas Day"}],
        ):
            self.assertTrue(
                AbstractApiHolidayProvider("key").is_holiday("GB", datetime.date(2024, 12, 25))
            )

    def test_an_empty_list_means_an_ordinary_day(self):
        import unittest.mock

        with unittest.mock.patch("tradecore_api.providers.holidays.get_json", return_value=[]):
            self.assertFalse(
                AbstractApiHolidayProvider("key").is_holiday("GB", datetime.date(2024, 3, 5))
            )

    def test_a_failed_call_means_an_ordinary_day(self):
        import unittest.mock

        with unittest.mock.patch(
            "tradecore_api.providers.holidays.get_json", return_value=None
        ):
            self.assertFalse(
                AbstractApiHolidayProvider("key").is_holiday("GB", datetime.date(2024, 3, 5))
            )


class KeywordModerationTests(SimpleTestCase):
    """The deterministic moderator."""

    def test_ordinary_text_is_allowed(self):
        verdict = KeywordModerationProvider().review("A title", "Some thoughts.")
        self.assertTrue(verdict.allowed)

    def test_a_blocked_term_is_rejected(self):
        verdict = KeywordModerationProvider().review("spamword", "body")
        self.assertFalse(verdict.allowed)
        self.assertIn("spamword", verdict.categories)

    def test_matching_is_case_insensitive(self):
        self.assertFalse(KeywordModerationProvider().review("SPAMWORD", "b").allowed)

    def test_the_description_is_checked_too(self):
        self.assertFalse(KeywordModerationProvider().review("fine", "get-rich-quick").allowed)


class ClaudeModerationParsingTests(SimpleTestCase):
    """Turning a model reply into a verdict."""

    def test_a_clean_json_reply_is_parsed(self):
        verdict = ClaudeModerationProvider.parse(
            '{"allowed": false, "reason": "spam", "categories": ["spam"]}'
        )
        self.assertFalse(verdict.allowed)
        self.assertEqual(verdict.reason, "spam")
        self.assertEqual(verdict.categories, ("spam",))

    def test_json_wrapped_in_prose_is_still_parsed(self):
        verdict = ClaudeModerationProvider.parse('Sure: {"allowed": true} -- done')
        self.assertTrue(verdict.allowed)

    def test_an_unparseable_reply_returns_none(self):
        self.assertIsNone(ClaudeModerationProvider.parse("I cannot help with that."))

    def test_a_reply_missing_the_verdict_returns_none(self):
        self.assertIsNone(ClaudeModerationProvider.parse('{"reason": "hmm"}'))

    def test_an_unreachable_api_falls_back_to_the_keyword_moderator(self):
        """Moderation must never fail open when the model is unavailable."""
        provider = ClaudeModerationProvider("key", "claude-opus-5")
        provider.api_key = ""  # forces the SDK call to raise
        verdict = provider.review("spamword offer", "body")
        self.assertFalse(verdict.allowed)


class AccountServiceTests(TestCase):
    """Enrichment is best-effort and injectable."""

    class BoomGeolocation(NullGeolocationProvider):
        def locate(self, ip_address):
            raise RuntimeError("provider exploded")

    def test_enrichment_uses_the_injected_providers(self):
        service = AccountService(NullGeolocationProvider(), NullHolidayProvider())
        enrichment = service.enrich("81.2.69.142")
        self.assertFalse(enrichment.joined_on_holiday)
        self.assertEqual(enrichment.geolocation["city"], "")

    def test_register_stores_the_enrichment(self):
        service = AccountService(NullGeolocationProvider(), NullHolidayProvider())
        user = service.register(
            email="enriched@example.com",
            password="a-decent-password-9",
            first_name="En",
            last_name="Riched",
            ip_address="81.2.69.142",
        )
        self.assertEqual(user.geolocation_data["country_code"], "")
        self.assertFalse(user.joined_on_holiday)
        self.assertTrue(user.check_password("a-decent-password-9"))
