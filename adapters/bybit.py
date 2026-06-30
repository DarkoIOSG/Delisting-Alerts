from adapters.base import get_json

EXCHANGE = "Bybit"
# api.bybit.com geo-blocks requests from US-region IPs (which is where
# GitHub Actions runners are hosted) — api.bytick.com is Bybit's own
# documented mirror domain for the same data, unaffected by that block.
_URL = "https://api.bytick.com/v5/market/instruments-info"


def fetch_listed_bases() -> set[str]:
    data = get_json(_URL, params={"category": "spot"})
    return {
        i["baseCoin"].upper()
        for i in data["result"]["list"]
        if i.get("status") == "Trading"
    }
