"""Ports and DTOs for the outbound integrations.

Sign-up enriches an account from two third-party services and posts are passed
through a moderator.  All three are expressed as small abstract ports with at
least one offline implementation, so the API runs end to end with no API keys
and a test never reaches the network.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class Geolocation:
    """Where an IP address appears to be.

    ``raw`` keeps the provider's untouched response so the stored JSON stays
    useful if a future provider returns richer fields.
    """

    country_code: str = ""
    country: str = ""
    city: str = ""
    latitude: float | None = None
    longitude: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        """Serialise for the ``User.geolocation_data`` column."""
        return {
            "country_code": self.country_code,
            "country": self.country,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "raw": self.raw,
        }


@dataclass(frozen=True, slots=True)
class ModerationVerdict:
    """The outcome of checking a post's text."""

    allowed: bool
    reason: str = ""
    categories: tuple[str, ...] = ()


class GeolocationProvider(abc.ABC):
    """Resolves a client IP address to a coarse location."""

    name: str = "geolocation"

    @abc.abstractmethod
    def locate(self, ip_address: str) -> Geolocation:
        """Return a :class:`Geolocation`; never raise for an unknown address."""


class HolidayProvider(abc.ABC):
    """Answers whether a given day is a public holiday in a country."""

    name: str = "holiday"

    @abc.abstractmethod
    def is_holiday(self, country_code: str, on: date) -> bool:
        """Return True only on a confirmed holiday; unknown means False."""


class ModerationProvider(abc.ABC):
    """Decides whether user-submitted post text may be published."""

    name: str = "moderation"

    @abc.abstractmethod
    def review(self, title: str, description: str) -> ModerationVerdict:
        """Return a verdict; never raise for awkward input."""
