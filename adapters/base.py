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

_COINGECKO_API_KEY_ENV_VAR = "COINGECKO_API_KEY"
_COINGECKO_TICKERS_URL = "https://pro-api.coingecko.com/api/v3/exchanges/{exchange_id}/tickers"


class ExchangeFetchError(Exception):
    """Raised when an exchange's market list can't be retrieved.

    Callers must treat this as "unknown", not "delisted" — a network
    hiccup or a temporary 5xx must never be interpreted as a delisting.
    """


def get_json(url: str, params: dict | None = None) -> dict | list:
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
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
            resp = requests.get(
                url, params={"page": page}, headers=headers, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
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
