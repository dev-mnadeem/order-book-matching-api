"""Chooses a concrete provider for each port from settings.

Every port defaults to ``auto``: use the real integration when a key is
present, otherwise the offline implementation.  That is what lets ``git clone
&& manage.py runserver`` work with no configuration while a deployment only has
to supply keys, not rewire anything.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from tradecore_api.providers.base import (
    GeolocationProvider,
    HolidayProvider,
    ModerationProvider,
)
from tradecore_api.providers.geolocation import (
    AbstractApiGeolocationProvider,
    NullGeolocationProvider,
)
from tradecore_api.providers.holidays import (
    AbstractApiHolidayProvider,
    NullHolidayProvider,
)
from tradecore_api.providers.moderation import (
    ClaudeModerationProvider,
    KeywordModerationProvider,
)

AUTO = "auto"


def get_geolocation_provider() -> GeolocationProvider:
    """Return the configured geolocation provider."""
    choice = settings.GEOLOCATION_PROVIDER
    key = settings.ABSTRACT_GEOLOCATION_API_KEY
    if choice == AUTO:
        choice = "abstractapi" if key else "null"
    if choice == "null":
        return NullGeolocationProvider()
    if choice == "abstractapi":
        _require(key, "ABSTRACT_GEOLOCATION_API_KEY", "GEOLOCATION_PROVIDER=abstractapi")
        return AbstractApiGeolocationProvider(key)
    raise ImproperlyConfigured(f"Unknown GEOLOCATION_PROVIDER: {choice!r}")


def get_holiday_provider() -> HolidayProvider:
    """Return the configured holiday provider."""
    choice = settings.HOLIDAY_PROVIDER
    key = settings.ABSTRACT_HOLIDAYS_API_KEY
    if choice == AUTO:
        choice = "abstractapi" if key else "null"
    if choice == "null":
        return NullHolidayProvider()
    if choice == "abstractapi":
        _require(key, "ABSTRACT_HOLIDAYS_API_KEY", "HOLIDAY_PROVIDER=abstractapi")
        return AbstractApiHolidayProvider(key)
    raise ImproperlyConfigured(f"Unknown HOLIDAY_PROVIDER: {choice!r}")


def get_moderation_provider() -> ModerationProvider:
    """Return the configured moderation provider."""
    choice = settings.MODERATION_PROVIDER
    key = settings.ANTHROPIC_API_KEY
    if choice == AUTO:
        choice = "claude" if key else "keyword"
    if choice == "keyword":
        return KeywordModerationProvider()
    if choice == "claude":
        _require(key, "ANTHROPIC_API_KEY", "MODERATION_PROVIDER=claude")
        return ClaudeModerationProvider(key, settings.MODERATION_MODEL)
    raise ImproperlyConfigured(f"Unknown MODERATION_PROVIDER: {choice!r}")


def _require(value: str, name: str, because: str) -> None:
    if not value:
        raise ImproperlyConfigured(f"{name} must be set when {because}.")
