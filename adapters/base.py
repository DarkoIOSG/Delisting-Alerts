"""Shared interface for exchange adapters.

Each adapter module exposes a single function, fetch_listed_bases(), which
returns the set of base-asset tickers currently tradeable (spot) on that
exchange's public market list.

Most adapters call these exchanges' own public APIs directly (no key
needed). A couple of exchanges (Binance, Bybit) geo-block GitHub Actions'
US-region IPs on every domain they expose, with no public unrestricted
mirror — for those, fetch_via_coingecko() proxies the same data through
the CoinGecko Pro API instead, which isn't geo-blocked.
"""

from __future__ import annotations

import os
import time

import requests

REQUEST_TIMEOUT = 15
USER_AGENT = "delisting-alerts-monitor/1.0"
MAX_ATTEMPTS = 4
_BACKOFF_BASE = 2  # seconds; doubles each retry (2, 4, 8)
_MAX_BACKOFF = 60
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

_COINGECKO_API_KEY_ENV_VAR = "COINGECKO_API_KEY"
_COINGECKO_TICKERS_URL = "https://pro-api.coingecko.com/api/v3/exchanges/{exchange_id}/tickers"


class ExchangeFetchError(Exception):
    """Raised when an exchange's market list can't be retrieved.

    Callers must treat this as "unknown", not "delisted" — a network
    hiccup or a temporary 5xx must never be interpreted as a delisting.
    """


def _get_with_retry(url: str, params: dict | None, headers: dict) -> requests.Response:
    """GET with retries on transient failures (connection resets, timeouts,
    429, 5xx). A single blip mid-pagination shouldn't cost a whole exchange
    for the run. Non-transient errors (e.g. 401, 404) fail immediately.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code in _RETRYABLE_STATUS and attempt < MAX_ATTEMPTS:
                retry_after = resp.headers.get("Retry-After", "")
                delay = int(retry_after) if retry_after.isdigit() else _BACKOFF_BASE * 2 ** (attempt - 1)
                time.sleep(min(delay, _MAX_BACKOFF))
                continue
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout):
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(_BACKOFF_BASE * 2 ** (attempt - 1))
    raise AssertionError("unreachable")


def get_json(url: str, params: dict | None = None) -> dict | list:
    try:
        resp = _get_with_retry(url, params, {"User-Agent": USER_AGENT})
        return resp.json()
    except requests.RequestException as exc:
        raise ExchangeFetchError(f"{url} -> {exc}") from exc


def fetch_via_coingecko(exchange_id: str) -> set[str]:
    """Paginate a CoinGecko Pro /exchanges/{id}/tickers feed into a set of
    base-asset tickers, skipping stale/anomalous entries.
    """
    api_key = os.environ.get(_COINGECKO_API_KEY_ENV_VAR)
    if not api_key:
        raise ExchangeFetchError(
            f"{_COINGECKO_API_KEY_ENV_VAR} not set — required to fetch "
            f"{exchange_id} via CoinGecko"
        )

    url = _COINGECKO_TICKERS_URL.format(exchange_id=exchange_id)
    headers = {"x-cg-pro-api-key": api_key, "User-Agent": USER_AGENT}
    bases: set[str] = set()
    page = 1
    while True:
        try:
            resp = _get_with_retry(url, {"page": page}, headers)
        except requests.RequestException as exc:
            raise ExchangeFetchError(f"{url} (page {page}) -> {exc}") from exc

        tickers = resp.json().get("tickers", [])
        if not tickers:
            break

        for t in tickers:
            if t.get("is_stale") or t.get("is_anomaly"):
                continue
            base = t.get("base")
            if base:
                bases.add(base.upper())

        page += 1
        time.sleep(0.5)

    if not bases:
        raise ExchangeFetchError(f"CoinGecko returned no {exchange_id} tickers")

    return bases
