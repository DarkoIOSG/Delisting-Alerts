"""Daily delisting check: diff each exchange's live trading-pair list
against yesterday's snapshot and alert on Slack when a tracked token's
base asset drops off an exchange.

Run by .github/workflows/delisting-check.yml on a daily cron. State
(state/snapshot.json) is committed back to the repo by the workflow so
each run can diff against the previous one.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from adapters import ADAPTERS
from adapters.base import ExchangeFetchError
from notifier import slack

ROOT = Path(__file__).parent
TOKENS_FILE = ROOT / "config" / "tokens.yaml"
STATE_FILE = ROOT / "state" / "snapshot.json"

# A token must be missing for at least this long (not just for N consecutive
# runs) before we escalate tentative -> confirmed. Tied to elapsed time
# rather than run count so tightening the check frequency (see workflow
# cron) doesn't also tighten how fast we confirm a delisting.
CONFIRM_AFTER = timedelta(hours=20)


def load_tokens() -> list[dict]:
    with open(TOKENS_FILE) as f:
        tokens = yaml.safe_load(f) or []
    return [t for t in tokens if t.get("ticker")]


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"exchanges": {}, "pending": {}}
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def fetch_current_snapshots() -> tuple[dict[str, list[str]], list[str]]:
    snapshots: dict[str, list[str]] = {}
    failures: list[str] = []
    for adapter in ADAPTERS:
        try:
            bases = adapter.fetch_listed_bases()
            if not bases:
                raise ExchangeFetchError("empty result set")
            snapshots[adapter.EXCHANGE] = sorted(bases)
        except ExchangeFetchError as exc:
            failures.append(f"{adapter.EXCHANGE}: {exc}")
    return snapshots, failures


def project_name(tokens: list[dict], ticker: str) -> str:
    for t in tokens:
        if t["ticker"] == ticker:
            return t["name"]
    return ticker


def diff_and_alert(
    tokens: list[dict],
    prev_exchanges: dict[str, list[str]],
    curr_exchanges: dict[str, list[str]],
    pending: dict[str, dict],
) -> dict[str, dict]:
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    tickers = {t["ticker"] for t in tokens}

    for exchange, curr_bases in curr_exchanges.items():
        if exchange not in prev_exchanges:
            # First time we've successfully fetched this exchange — establish
            # baseline only, nothing to diff against yet.
            continue

        prev_set = set(prev_exchanges[exchange])
        curr_set = set(curr_bases)

        for ticker in tickers:
            key = f"{exchange}:{ticker}"
            is_listed = ticker in curr_set
            in_pending = key in pending
            name = project_name(tokens, ticker)

            if is_listed:
                if in_pending:
                    was_confirmed = pending[key]["confirmed"]
                    del pending[key]
                    label = "confirmed delisting" if was_confirmed else "tentative flag"
                    slack.send(
                        f":white_check_mark: *Re-listed*\n"
                        f"*{name}* ({ticker}) is back in {exchange}'s live trading "
                        f"pairs, reversing an earlier {label}."
                    )
                continue

            # Not listed this run.
            if in_pending:
                if not pending[key]["confirmed"]:
                    first_missing = datetime.fromisoformat(pending[key]["first_missing_run"])
                    if now_dt - first_missing >= CONFIRM_AFTER:
                        pending[key]["confirmed"] = True
                        slack.send(
                            f":rotating_light: *Delisting confirmed*\n"
                            f"*{name}* ({ticker}) has been missing from {exchange}'s "
                            f"live trading pairs for over "
                            f"{CONFIRM_AFTER.total_seconds() / 3600:.0f} hours "
                            f"(first noticed {pending[key]['first_missing_run']})."
                        )
                    # else: still within the grace period — stay silent, wait
                    # for a later run to either confirm or see it relist.
                # else: already confirmed and alerted — stay silent until it relists.
            elif ticker in prev_set:
                # First time we've seen it drop off.
                pending[key] = {"first_missing_run": now, "confirmed": False}
                slack.send(
                    f":warning: *Possible delisting detected*\n"
                    f"*{name}* ({ticker}) is no longer in {exchange}'s live "
                    f"trading pairs as of this run. This could be a temporary "
                    f"API/maintenance blip — will confirm if it's still missing "
                    f"in {CONFIRM_AFTER.total_seconds() / 3600:.0f}+ hours."
                )

    return pending


def main() -> int:
    tokens = load_tokens()
    if not tokens:
        print("No tokens with a ticker in config/tokens.yaml — nothing to do.")
        return 0

    state = load_state()
    prev_exchanges = state.get("exchanges", {})
    pending = state.get("pending", {})

    curr_exchanges, failures = fetch_current_snapshots()

    if failures:
        slack.send(
            ":bug: *Delisting monitor degraded*\n"
            "Couldn't fetch a market list from: " + "; ".join(failures) +
            "\nThose exchanges were skipped this run (not treated as delistings)."
        )

    pending = diff_and_alert(tokens, prev_exchanges, curr_exchanges, pending)

    merged_exchanges = {**prev_exchanges, **curr_exchanges}
    save_state(
        {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "exchanges": merged_exchanges,
            "pending": pending,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
