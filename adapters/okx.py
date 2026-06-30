from adapters.base import get_json

EXCHANGE = "OKX"
_URL = "https://www.okx.com/api/v5/public/instruments"


def fetch_listed_bases() -> set[str]:
    data = get_json(_URL, params={"instType": "SPOT"})
    return {
        i["baseCcy"].upper()
        for i in data["data"]
        if i.get("state") == "live" and i.get("baseCcy")
    }
