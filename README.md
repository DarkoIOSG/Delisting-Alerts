# Delisting Alerts

Monitors a fixed list of tokens across 7 major exchanges (Binance, Coinbase,
OKX, Bybit, Upbit, KuCoin, Gate.io) and posts to Slack when a token's
trading pairs disappear from an exchange.

## How it works

Each run (every 8 hours, via GitHub Actions):
1. Pulls the live spot trading-pair list from each exchange's public market
   API (no API keys required).
2. Diffs it against the previous run's snapshot (`state/snapshot.json`,
   committed back to the repo by the workflow).
3. If a tracked token's base asset disappears from an exchange:
   - 1st run missing → **tentative** Slack alert (could be a maintenance
     blip).
   - 2nd consecutive run still missing → **confirmed** Slack alert.
   - If it reappears at any point → **re-listed** Slack alert, reversing
     the earlier flag.
4. If an exchange's API itself can't be reached, that exchange is skipped
   for the run (never treated as a delisting) and a separate "monitor
   degraded" Slack message is sent.

This means a real delisting gets a heads-up alert within 8 hours and a
confirmed alert within 16, while a single missed run's API hiccup doesn't
trigger a false "delisted" report.

## Setup

1. Create a Slack [Incoming Webhook](https://api.slack.com/messaging/webhooks)
   for the channel you want alerts in.
2. Add it as a GitHub Actions secret on this repo: **Settings → Secrets and
   variables → Actions → New repository secret**, name `SLACK_WEBHOOK_URL`.
3. Add a second secret, name `COINGECKO_API_KEY`, value your CoinGecko Pro
   API key (see "Why Binance goes through CoinGecko" below for why this is
   needed).
4. The workflow (`.github/workflows/delisting-check.yml`) runs every 8
   hours (00:00, 08:00, 16:00 UTC), and can also be triggered manually from
   the Actions tab (`workflow_dispatch`).

No further setup needed — the workflow installs dependencies, runs the
check, and commits the updated state file itself.

## Why Binance and Bybit go through CoinGecko

`api.binance.com` (and its mirrors `api1-4.binance.com`) return HTTP 451 for
requests from US-region IPs — a deliberate Binance geo-restriction, and
GitHub Actions runners are hosted on US-region infrastructure. `api.bybit.com`
does the same (403), and its documented mirror `api.bytick.com` turned out
to be subject to the same block rather than being an exemption. Neither
exchange has a working public unrestricted endpoint reachable from GitHub
Actions, so [adapters/binance.py](adapters/binance.py) and
[adapters/bybit.py](adapters/bybit.py) both go through
`fetch_via_coingecko()` in [adapters/base.py](adapters/base.py), which
paginates the CoinGecko Pro API's `/exchanges/{id}/tickers` feed instead —
CoinGecko isn't geo-blocked. This means Binance and Bybit's listing data is
one step removed from their own APIs — sourced via CoinGecko's mirror of it
rather than directly — while the other 5 exchanges (Coinbase, OKX, Upbit,
KuCoin, Gate.io) are queried directly.

If you'd rather not depend on CoinGecko for these two, the alternatives are
running the workflow on a self-hosted runner outside the US, or dropping
them from the tracked exchange list — see [adapters/__init__.py](adapters/__init__.py).

## Customizing

- **Token list**: edit [config/tokens.yaml](config/tokens.yaml). `ticker`
  must match the exchange API's base-asset symbol exactly.
- **Exchanges**: add/remove modules in [adapters/](adapters/) and register
  them in [adapters/__init__.py](adapters/__init__.py). Each adapter just
  needs to expose `EXCHANGE` (display name) and `fetch_listed_bases()`
  (returns a `set[str]` of currently-tradeable base tickers).
- **Frequency**: change the cron schedule in
  [.github/workflows/delisting-check.yml](.github/workflows/delisting-check.yml).
  Note tighter intervals increase the chance of catching an exchange in a
  maintenance window as a false tentative alert (which self-corrects, but
  is noisier).

## Open questions on the token list

A few entries needed inference rather than being an unambiguous ticker —
worth a sanity check (see comments in `config/tokens.yaml`):

- **THQ** → mapped to *Theoriq*. This was the best match found, but
  nothing in the rest of the list confirms it's the intended project —
  please double check.
- **GEL** (Gelato) → not currently listed on any of the 7 tracked
  exchanges. Either it never had a major-exchange listing or it was
  already delisted before this monitor started — there's no baseline to
  alert against until/unless it lists on one of them.
- **OBOL** → only listed on Gate.io among the 7 tracked exchanges, so
  there's no cross-exchange confirmation signal for it specifically.
- **covalent** → tracked as **CXT**, not CQT. CQT was migrated 1:1 to CXT
  in 2024 and no longer trades anywhere.

## What this does not cover

This tracks *trading-pair removal* as the ground-truth signal. It does not
scrape exchange announcement pages, so it won't give early warning during
an exchange's pre-delisting notice period (typically a few days) — only
once the pair is actually pulled. Adding announcement-feed scraping per
exchange would close that gap; flagged as a possible v2.
