"""Thin HTTP client for exporters and the Prometheus query API.

Uses only the standard library. Every request has a timeout and a bounded
number of retries so a hung or flapping endpoint cannot stall the CLI. The
fetch function is injectable so checks can be tested without a network.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

# A fetcher takes (url, timeout_seconds) and returns the response body as text.
Fetcher = Callable[[str, float], str]


class PromError(RuntimeError):
    """Raised when an endpoint cannot be reached or returns a bad response."""


def http_get(url: str, timeout: float) -> str:
    req = urllib.request.Request(url, headers={"Accept": "text/plain, application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed scheme below)
        charset = resp.headers.get_content_charset() or "utf-8"
        return cast(str, resp.read().decode(charset))


def _get_with_retries(
    url: str, *, fetch: Fetcher, timeout: float, retries: int, backoff: float
) -> str:
    if not url.startswith(("http://", "https://")):
        raise PromError(f"refusing non-HTTP(S) URL: {url!r}")
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fetch(url, timeout)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
    raise PromError(f"request to {url} failed after {retries + 1} attempt(s): {last}")


@dataclass
class PrometheusClient:
    """Client for a Prometheus server's HTTP API."""

    base_url: str
    timeout: float = 5.0
    retries: int = 2
    backoff: float = 0.2
    # None resolves to http_get at call time, so http_get can be monkeypatched.
    fetch: Fetcher | None = None

    def _api(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        url = f"{self.base_url.rstrip('/')}{path}?{query}"
        body = _get_with_retries(
            url,
            fetch=self.fetch or http_get,
            timeout=self.timeout,
            retries=self.retries,
            backoff=self.backoff,
        )
        try:
            return cast("dict[str, Any]", json.loads(body))
        except json.JSONDecodeError as exc:
            raise PromError(f"invalid JSON from {url}: {exc}") from exc

    def query(self, expr: str) -> dict[str, Any]:
        """Run an instant query and return the raw JSON payload."""

        return self._api("/api/v1/query", {"query": expr})

    def build_info(self) -> dict[str, Any]:
        """Fetch Prometheus build info; a cheap connectivity probe."""

        return self._api("/api/v1/status/buildinfo", {})


@dataclass
class ExporterClient:
    """Client that scrapes a /metrics endpoint directly."""

    url: str
    timeout: float = 5.0
    retries: int = 2
    backoff: float = 0.2
    # None resolves to http_get at call time, so http_get can be monkeypatched.
    fetch: Fetcher | None = None

    def scrape(self) -> str:
        return _get_with_retries(
            self.url,
            fetch=self.fetch or http_get,
            timeout=self.timeout,
            retries=self.retries,
            backoff=self.backoff,
        )
