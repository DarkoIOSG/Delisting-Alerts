"""Binance adapter.

api.binance.com (and its load-balanced siblings api1-4.binance.com) return
HTTP 451 for requests from US-region IPs, which is where GitHub Actions
runners live — this is a deliberate Binance geo-restriction with no public
unrestricted mirror. Goes through CoinGecko Pro instead (see adapters/base.py).
"""

from adapters.base import fetch_via_coingecko

EXCHANGE = "Binance"
_COINGECKO_EXCHANGE_ID = "binance"


def fetch_listed_bases() -> set[str]:
    return fetch_via_coingecko(_COINGECKO_EXCHANGE_ID)
