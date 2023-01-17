"""Geolocation providers: Abstract API, plus an offline fallback."""

from __future__ import annotations

import ipaddress

from django.conf import settings
from django.core.cache import cache

from tradecore_api.providers.base import Geolocation, GeolocationProvider
from tradecore_api.providers.http import get_json

ABSTRACT_GEOLOCATION_URL = "https://ipgeolocation.abstractapi.com/v1/"
CACHE_PREFIX = "geo"


def is_routable(ip_address: str) -> bool:
    """True when an address could plausibly be looked up by a geo service.

    Loopback and RFC1918 addresses are what a local ``runserver`` sees, and
    paying a provider to tell us that 127.0.0.1 is nowhere is pure waste.
    """
    try:
        parsed = ipaddress.ip_address(ip_address)
    except ValueError:
        return False
    return parsed.is_global


class NullGeolocationProvider(GeolocationProvider):
    """Returns an empty location for every address.

    This is the default when no API key is configured.  It keeps sign-up fully
    functional offline — the account is simply created with no location.
    """

    name = "null"

    def locate(self, ip_address: str) -> Geolocation:
        return Geolocation()


class AbstractApiGeolocationProvider(GeolocationProvider):
    """Looks an address up via ipgeolocation.abstractapi.com."""

    name = "abstractapi"

    def __init__(self, api_key: str, cache_seconds: int | None = None) -> None:
        self.api_key = api_key
        self.cache_seconds = (
            settings.GEOLOCATION_CACHE_SECONDS if cache_seconds is None else cache_seconds
        )

    def locate(self, ip_address: str) -> Geolocation:
        if not is_routable(ip_address):
            return Geolocation()

        cache_key = f"{CACHE_PREFIX}:{ip_address}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Geolocation(**cached)

        payload = get_json(
            ABSTRACT_GEOLOCATION_URL,
            {"api_key": self.api_key, "ip_address": ip_address},
        )
        if not isinstance(payload, dict):
            return Geolocation()

        located = self.parse(payload)
        cache.set(cache_key, located.as_json(), self.cache_seconds)
        return located

    @staticmethod
    def parse(payload: dict) -> Geolocation:
        """Map an Abstract API body onto the provider-neutral DTO."""
        return Geolocation(
            country_code=str(payload.get("country_code") or ""),
            country=str(payload.get("country") or ""),
            city=str(payload.get("city") or ""),
            latitude=_as_float(payload.get("latitude")),
            longitude=_as_float(payload.get("longitude")),
            raw=payload,
        )


def _as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
