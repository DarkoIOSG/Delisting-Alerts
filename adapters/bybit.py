"""Bybit adapter.

api.bybit.com geo-blocks GitHub Actions' US-region IPs (403). Its
documented mirror api.bytick.com turned out to be blocked too — same
restriction, different domain. Goes through CoinGecko Pro instead, same as
Binance (see adapters/base.py). Note CoinGecko splits Bybit into separate
spot ("bybit_spot") and futures ("bybit") exchange ids — we want spot.
"""

from adapters.base import fetch_via_coingecko

EXCHANGE = "Bybit"
_COINGECKO_EXCHANGE_ID = "bybit_spot"


def fetch_listed_bases() -> set[str]:
    return fetch_via_coingecko(_COINGECKO_EXCHANGE_ID)
