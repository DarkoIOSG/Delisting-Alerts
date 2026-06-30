from adapters.base import get_json

EXCHANGE = "Binance"
_URL = "https://api.binance.com/api/v3/exchangeInfo"


def fetch_listed_bases() -> set[str]:
    data = get_json(_URL)
    return {
        s["baseAsset"].upper()
        for s in data["symbols"]
        if s.get("status") == "TRADING"
    }
