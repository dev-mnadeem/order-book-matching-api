"""Typed readers for environment variables.

Django settings modules tend to accumulate ``os.environ.get(...) == "true"``
comparisons that each parse values slightly differently.  Keeping the coercion
in one place means a malformed value fails loudly at start-up instead of
silently turning a security flag off.
"""

from __future__ import annotations

import os

TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def env_str(name: str, default: str) -> str:
    """Return the variable as a stripped string, or ``default`` if unset/blank."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def env_bool(name: str, *, default: bool) -> bool:
    """Parse a boolean flag, raising on a value that is neither true nor false."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    normalised = raw.strip().lower()
    if normalised in TRUE_VALUES:
        return True
    if normalised in FALSE_VALUES:
        return False
    raise ValueError(
        f"{name}={raw!r} is not a boolean. Use one of {sorted(TRUE_VALUES | FALSE_VALUES)}."
    )


def env_int(name: str, default: int) -> int:
    """Parse an integer setting, raising on a non-numeric value."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name}={raw!r} is not an integer.") from exc


def env_list(name: str, default: list[str]) -> list[str]:
    """Parse a comma-separated list, dropping blank entries."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]
