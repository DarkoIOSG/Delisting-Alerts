from adapters.base import get_json

EXCHANGE = "Bybit"
_URL = "https://api.bybit.com/v5/market/instruments-info"


def fetch_listed_bases() -> set[str]:
    data = get_json(_URL, params={"category": "spot"})
    return {
        i["baseCoin"].upper()
        for i in data["result"]["list"]
        if i.get("status") == "Trading"
    }
