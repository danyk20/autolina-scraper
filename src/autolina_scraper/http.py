"""HTTP session handling: identification, pacing, and retries.

Ground rules baked into this module, not just documented:

* We only ever request autolina.ch's open, canonical routes (the make/model
  landing pages, their pagination, and individual listing pages) — never the
  bare internal ``/carList`` route, which sits behind an interactive Cloudflare
  Turnstile challenge. If a challenge page is ever received from a route this
  library does use, :func:`get` raises :class:`ChallengeDetectedError` instead
  of retrying — a WAF rule change should fail loudly, not loop forever or try
  to solve the challenge.
* The User-Agent identifies this project honestly, by name and with a link back
  to the repository — never a browser UA, never a named search-engine bot.
* Every request goes through the same configurable delay. There is no
  concurrency knob; be a reasonable citizen.
"""

from __future__ import annotations

import logging
import random
import time
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import requests

logger = logging.getLogger("autolina_scraper")

try:
    _VERSION = version("autolina-scraper")
except PackageNotFoundError:  # pragma: no cover - only hit from an uninstalled checkout
    _VERSION = "0.0.0"

USER_AGENT = f"autolina-scraper/{_VERSION} (+https://github.com/danyk20/autolina-scraper)"

_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
_CHALLENGE_MARKERS = ("Just a moment", "cf-mitigated", "Verify you are human")


class ChallengeDetectedError(RuntimeError):
    """Raised when a response looks like a Cloudflare bot-detection challenge.

    This library never attempts to solve or bypass such a challenge. Seeing one
    on a route this scraper is supposed to be able to reach unauthenticated means
    autolina.ch changed its bot-protection rules — that needs a human to look at,
    not a retry loop.
    """


def new_session() -> requests.Session:
    """Build a :class:`requests.Session` with this project's identifying headers."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
        }
    )
    return session


def get(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    delay: float = 1.0,
    max_retries: int = 5,
    timeout: float = 15.0,
) -> requests.Response:
    """GET *url*, pacing requests by *delay* seconds and retrying transient errors.

    Retries (with exponential backoff + jitter) on 429/5xx and on connection-level
    errors. Any other 4xx is raised immediately — it won't get better on retry.
    """
    if delay > 0:
        time.sleep(delay)

    attempt = 0
    while True:
        try:
            response = session.get(url, params=params, timeout=timeout)
        except requests.exceptions.RequestException:
            attempt += 1
            if attempt > max_retries:
                raise
            _sleep_backoff(attempt)
            continue

        if _looks_like_challenge(response):
            raise ChallengeDetectedError(
                f"{url} returned what looks like a Cloudflare bot-detection "
                "challenge — refusing to proceed"
            )

        if response.status_code in _RETRYABLE_STATUSES:
            attempt += 1
            if attempt > max_retries:
                response.raise_for_status()
            logger.warning(
                "retryable status %s from %s (attempt %d/%d)",
                response.status_code,
                url,
                attempt,
                max_retries,
            )
            _sleep_backoff(attempt)
            continue

        response.raise_for_status()
        return response


def _looks_like_challenge(response: requests.Response) -> bool:
    if response.status_code == 403 and any(
        marker in response.text for marker in _CHALLENGE_MARKERS
    ):
        return True
    return response.headers.get("cf-mitigated") is not None


def _sleep_backoff(attempt: int) -> None:
    base = min(2**attempt, 30)
    time.sleep(base + random.uniform(0, 1))
