"""Shared interface for exchange adapters.

Each adapter module exposes a single function, fetch_listed_bases(), which
returns the set of base-asset tickers currently tradeable (spot) on that
exchange's public market list. No API keys are required — these are all
public market-data endpoints.
"""

from __future__ import annotations

import requests

REQUEST_TIMEOUT = 15
USER_AGENT = "delisting-alerts-monitor/1.0"


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
