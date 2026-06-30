from adapters.base import get_json

EXCHANGE = "Coinbase"
_URL = "https://api.exchange.coinbase.com/products"


def fetch_listed_bases() -> set[str]:
    data = get_json(_URL)
    return {
        p["base_currency"].upper()
        for p in data
        if p.get("status") == "online" and not p.get("trading_disabled")
    }
