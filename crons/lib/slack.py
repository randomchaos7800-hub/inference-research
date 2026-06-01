"""Shared Slack posting utility for cron scripts."""

import json
import subprocess
import urllib.request
import os

VAULT = os.path.expanduser("~/.vault/vault.sh")
BRIEF   = "C0B6Q4525EY"   # #brief  — daily reads
ALERTS  = "C0B651Z4C0P"   # #alerts — infra, fires on failure only
X       = "C0B6JDJMH9U"   # #x      — X post confirmations
OPS_LOG = "C0AHSAE9YN9"   # #ops-log — ops digests


def _token():
    r = subprocess.run([VAULT, "get", "slack_ops_bot_token"], capture_output=True, text=True)
    return r.stdout.strip()


def post(text, channel=ALERTS):
    token = _token()
    if not token:
        raise RuntimeError("slack_ops_bot_token not in vault")
    payload = json.dumps({
        "channel": channel,
        "text": text,
        "unfurl_links": False,
        "mrkdwn": True,
    }).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        resp = json.loads(r.read())
        if not resp.get("ok"):
            raise RuntimeError(f"Slack error: {resp.get('error')}")
