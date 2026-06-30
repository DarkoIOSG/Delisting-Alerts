from adapters.base import get_json

EXCHANGE = "Upbit"
_URL = "https://api.upbit.com/v1/market/all"


def fetch_listed_bases() -> set[str]:
    data = get_json(_URL, params={"isDetails": "false"})
    bases = set()
    for m in data:
        market = m.get("market", "")
        if "-" in market:
            bases.add(market.split("-", 1)[1].upper())
    return bases
