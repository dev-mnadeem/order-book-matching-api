"""A single shared ``requests`` session for every outbound provider call."""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

USER_AGENT = "tradecore-api/1.0 (+https://github.com/tradecore/order-book-matching-api)"

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
}

_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Return the process-wide session, building it on first use.

    Built lazily rather than at import time so that the retry count is read
    from the configured settings rather than from whatever was loaded first.
    """
    global _session
    if _session is None:
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=settings.PROVIDER_HTTP_MAX_RETRIES)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _session = session
    return _session


def get_json(url: str, params: dict[str, object]) -> dict | list | None:
    """GET a JSON document, returning None instead of raising on any failure.

    Enrichment is decoration on top of the real work of creating an account.  A
    provider that is slow, down or rate-limiting must never turn a valid
    sign-up into a 500, so every failure mode collapses to None here and the
    caller falls back.
    """
    try:
        response = get_session().get(
            url,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=settings.PROVIDER_HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("provider request to %s failed: %s", url, exc)
        return None

    if response.status_code != requests.codes.ok:
        logger.warning("provider %s returned HTTP %s", url, response.status_code)
        return None

    try:
        return response.json()
    except ValueError:
        logger.warning("provider %s returned a non-JSON body", url)
        return None
