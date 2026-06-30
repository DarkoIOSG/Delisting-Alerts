"""Binance adapter.

api.binance.com (and its load-balanced siblings api1-4.binance.com) return
HTTP 451 for requests from US-region IPs, which is where GitHub Actions
runners live — this is a deliberate Binance geo-restriction with no public
unrestricted mirror. Instead we go through the CoinGecko Pro API, which
proxies Binance's own live ticker list and isn't geo-blocked.
"""

import os
import time

import requests

EXCHANGE = "Binance"
_URL = "https://pro-api.coingecko.com/api/v3/exchanges/binance/tickers"
_API_KEY_ENV_VAR = "COINGECKO_API_KEY"


def fetch_listed_bases() -> set[str]:
    from adapters.base import ExchangeFetchError, REQUEST_TIMEOUT, USER_AGENT

    api_key = os.environ.get(_API_KEY_ENV_VAR)
    if not api_key:
        raise ExchangeFetchError(
            f"{_API_KEY_ENV_VAR} not set — required to fetch Binance via CoinGecko"
        )

    headers = {"x-cg-pro-api-key": api_key, "User-Agent": USER_AGENT}
    bases: set[str] = set()
    page = 1
    while True:
        try:
            resp = requests.get(
                _URL,
                params={"page": page},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ExchangeFetchError(f"{_URL} (page {page}) -> {exc}") from exc

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
        raise ExchangeFetchError("CoinGecko returned no Binance tickers")

    return bases
