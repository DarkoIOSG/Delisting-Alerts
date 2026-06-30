from adapters.base import get_json

EXCHANGE = "Gate.io"
_URL = "https://api.gateio.ws/api/v4/spot/currency_pairs"


def fetch_listed_bases() -> set[str]:
    data = get_json(_URL)
    return {
        p["base"].upper()
        for p in data
        if p.get("trade_status") == "tradable"
    }
