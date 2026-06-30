import os

import requests

WEBHOOK_ENV_VAR = "SLACK_WEBHOOK_URL"


def send(text: str) -> None:
    webhook_url = os.environ.get(WEBHOOK_ENV_VAR)
    if not webhook_url:
        print(f"[slack:dry-run, {WEBHOOK_ENV_VAR} not set]\n{text}")
        return
    resp = requests.post(webhook_url, json={"text": text}, timeout=15)
    resp.raise_for_status()
