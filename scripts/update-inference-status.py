#!/usr/bin/env python3
"""
Fetches live model + speed from local-proxy, writes data/inference-status.json
to the web root. Runs every 15 minutes via cron.
"""
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

PROXY = "http://100.120.50.35:8010"
OUT   = Path("/home/dino/www/dinovitale.com/data/inference-status.json")

SPEED_PROMPT = "List the planets in order from the sun. One word each."
MAX_TOKENS   = 40


def fetch_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def measure_speed(model_alias: str) -> float | None:
    payload = json.dumps({
        "model":      model_alias,
        "messages":   [{"role": "user", "content": SPEED_PROMPT}],
        "max_tokens": MAX_TOKENS,
        "stream":     False,
    }).encode()

    req = urllib.request.Request(
        f"{PROXY}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
        elapsed = time.time() - t0
        tokens = resp.get("usage", {}).get("completion_tokens", 0)
        if tokens > 0 and elapsed > 0:
            return round(tokens / elapsed, 1)
    except Exception:
        pass
    return None


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        active = fetch_json(f"{PROXY}/health")
    except Exception as e:
        OUT.write_text(json.dumps({
            "status":  "offline",
            "updated": now,
            "error":   str(e),
        }, indent=2))
        return

    model_id   = active.get("model", "unknown")
    backend    = active.get("active", "unknown")
    model_name = active.get("model", "local")

    # map internal model IDs to display names
    display = {
        "aeon-nvfp4": "AEON NVFP4",
        "qwen3627b":  "Qwen3 36B MoE",
        "local":      "local",
    }
    label = display.get(model_id, model_id)

    tok_s = measure_speed(model_name)

    OUT.write_text(json.dumps({
        "status":    "online",
        "active":    backend,
        "model_id":  model_id,
        "model":     label,
        "tok_s":     tok_s,
        "updated":   now,
    }, indent=2))
    print(f"{now}  {label}  {tok_s} tok/s")


if __name__ == "__main__":
    main()
