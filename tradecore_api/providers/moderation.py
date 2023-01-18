"""Moderation providers for user-submitted post text.

Posts are public user-generated content, so every one is reviewed before it is
stored.  The default reviewer is a deterministic blocklist that needs no
network and no API key; ``MODERATION_PROVIDER=claude`` swaps in a model-backed
reviewer that catches phrasing a fixed word list cannot.  Both satisfy the same
port, and the Claude reviewer falls back to the deterministic one whenever the
API is unreachable, so moderation never fails open.
"""

from __future__ import annotations

import json
import logging
import re

from tradecore_api.providers.base import ModerationProvider, ModerationVerdict

logger = logging.getLogger(__name__)

# Deliberately small and boring.  This is a demonstration blocklist, not a
# content-policy engine -- its job is to make the seam testable offline.
BLOCKED_TERMS: tuple[str, ...] = (
    "spamword",
    "buy-followers",
    "get-rich-quick",
)

MAX_REVIEWABLE_CHARS = 4000

MODERATION_SYSTEM_PROMPT = """\
You review short social posts for a small API.
Reply with a single JSON object and nothing else, in this exact shape:
{"allowed": true or false, "reason": "short explanation", "categories": ["..."]}
Block only clear spam, harassment, or attempts to sell a scam.
Ordinary opinions, criticism and bad jokes are allowed."""


class KeywordModerationProvider(ModerationProvider):
    """Rejects text containing any blocked term.

    Deterministic, offline and instant.  This is the default so a fresh clone
    behaves identically on every machine and the test suite never needs a key.
    """

    name = "keyword"

    def __init__(self, blocked_terms: tuple[str, ...] = BLOCKED_TERMS) -> None:
        self.blocked_terms = blocked_terms

    def review(self, title: str, description: str) -> ModerationVerdict:
        haystack = f"{title}\n{description}".lower()
        hits = tuple(term for term in self.blocked_terms if term in haystack)
        if hits:
            return ModerationVerdict(
                allowed=False,
                reason="Post contains blocked terms.",
                categories=hits,
            )
        return ModerationVerdict(allowed=True)


class ClaudeModerationProvider(ModerationProvider):
    """Reviews post text with the Anthropic Messages API.

    The keyword provider is kept as an inner fallback rather than as a
    competing branch in the service: if the model call fails for any reason the
    post still gets reviewed, just more crudely.
    """

    name = "claude"

    def __init__(
        self,
        api_key: str,
        model: str,
        fallback: ModerationProvider | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.fallback = fallback or KeywordModerationProvider()

    def review(self, title: str, description: str) -> ModerationVerdict:
        try:
            import anthropic
        except ImportError:
            logger.warning("anthropic package is not installed, using %s", self.fallback.name)
            return self.fallback.review(title, description)

        text = f"Title: {title}\n\nBody: {description}"[:MAX_REVIEWABLE_CHARS]
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=512,
                system=MODERATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": text}],
            )
        except Exception as exc:  # any provider failure must fall back, not 500
            logger.warning("moderation call failed (%s), using %s", exc, self.fallback.name)
            return self.fallback.review(title, description)

        verdict = self.parse(
            "".join(block.text for block in response.content if block.type == "text")
        )
        if verdict is None:
            logger.warning("moderation reply was not usable, using %s", self.fallback.name)
            return self.fallback.review(title, description)
        return verdict

    @staticmethod
    def parse(reply: str) -> ModerationVerdict | None:
        """Turn the model's reply into a verdict, or None if it is unusable."""
        match = re.search(r"\{.*\}", reply, re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except ValueError:
            return None
        if not isinstance(payload, dict) or "allowed" not in payload:
            return None

        categories = payload.get("categories") or []
        if not isinstance(categories, list):
            categories = []
        return ModerationVerdict(
            allowed=bool(payload["allowed"]),
            reason=str(payload.get("reason") or ""),
            categories=tuple(str(item) for item in categories),
        )
