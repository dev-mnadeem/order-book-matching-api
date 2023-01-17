"""Holiday providers: Abstract API, plus an offline fallback."""

from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.cache import cache

from tradecore_api.providers.base import HolidayProvider
from tradecore_api.providers.http import get_json

ABSTRACT_HOLIDAYS_URL = "https://holidays.abstractapi.com/v1/"
CACHE_PREFIX = "holiday"


class NullHolidayProvider(HolidayProvider):
    """Reports every day as an ordinary working day."""

    name = "null"

    def is_holiday(self, country_code: str, on: date) -> bool:
        return False


class AbstractApiHolidayProvider(HolidayProvider):
    """Checks holidays.abstractapi.com for one country and date."""

    name = "abstractapi"

    def __init__(self, api_key: str, cache_seconds: int | None = None) -> None:
        self.api_key = api_key
        self.cache_seconds = (
            settings.HOLIDAY_CACHE_SECONDS if cache_seconds is None else cache_seconds
        )

    def is_holiday(self, country_code: str, on: date) -> bool:
        if not country_code:
            return False

        cache_key = f"{CACHE_PREFIX}:{country_code}:{on.isoformat()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return bool(cached)

        payload = get_json(
            ABSTRACT_HOLIDAYS_URL,
            {
                "api_key": self.api_key,
                "country": country_code,
                "year": on.year,
                "month": on.month,
                "day": on.day,
            },
        )
        # The endpoint answers with a list of holidays; an empty list means the
        # date is an ordinary day, and None means the call did not succeed.
        if payload is None:
            return False

        holiday = bool(payload)
        cache.set(cache_key, holiday, self.cache_seconds)
        return holiday
