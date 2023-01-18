"""Account creation, including the best-effort sign-up enrichment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from django.db import transaction
from django.utils import timezone

from tradecore_api.models import User
from tradecore_api.providers import (
    GeolocationProvider,
    HolidayProvider,
    get_geolocation_provider,
    get_holiday_provider,
)

logger = logging.getLogger(__name__)

LOCALHOST = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class Enrichment:
    """What the providers managed to work out about a new account."""

    geolocation: dict
    joined_on_holiday: bool


class AccountService:
    """Creates accounts and decorates them with location and holiday data.

    The providers are constructor arguments so a test can pass deterministic
    doubles without patching module globals or touching the network.
    """

    def __init__(
        self,
        geolocation_provider: GeolocationProvider | None = None,
        holiday_provider: HolidayProvider | None = None,
    ) -> None:
        self.geolocation_provider = geolocation_provider or get_geolocation_provider()
        self.holiday_provider = holiday_provider or get_holiday_provider()

    def enrich(self, ip_address: str, on: date | None = None) -> Enrichment:
        """Look up the location and holiday flag for a sign-up.

        Never raises: the providers already degrade to empty answers, and an
        account is worth more than the decoration around it.
        """
        located = self.geolocation_provider.locate(ip_address)
        on = on or timezone.now().date()
        joined_on_holiday = self.holiday_provider.is_holiday(located.country_code, on)
        return Enrichment(
            geolocation=located.as_json(),
            joined_on_holiday=joined_on_holiday,
        )

    @transaction.atomic
    def register(
        self, *, email: str, password: str, first_name: str, last_name: str, ip_address: str
    ) -> User:
        """Create an account and store its enrichment in one transaction."""
        enrichment = self.enrich(ip_address)
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            geolocation_data=enrichment.geolocation,
            joined_on_holiday=enrichment.joined_on_holiday,
        )


def client_ip(request) -> str:
    """Best-effort client address for the current request.

    ``X-Forwarded-For`` is only consulted for its first entry, which is what a
    trusted reverse proxy prepends.  Behind an untrusted proxy this header is
    attacker-controlled, so it is used for enrichment only and never for any
    authorisation decision.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or LOCALHOST
