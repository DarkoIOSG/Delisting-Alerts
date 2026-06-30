from adapters.base import get_json

EXCHANGE = "KuCoin"
_URL = "https://api.kucoin.com/api/v2/symbols"


def fetch_listed_bases() -> set[str]:
    data = get_json(_URL)
    return {
        s["baseCurrency"].upper()
        for s in data["data"]
        if s.get("enableTrading")
    }
