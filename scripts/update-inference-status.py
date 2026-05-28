#!/usr/bin/env python3
"""Fetch live model + canonical throughput from local-proxy."""
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROXY = "http://100.120.50.35:8010"
OUT   = Path("/home/dino/www/dinovitale.com/data/inference-status.json")
BENCH = Path("/home/dino/scripts/bench-inference.py")

SPEED_PROMPT = "Count from 1 to 200, one number per line, no commentary."
MAX_TOKENS   = 512


def fetch_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def measure_speed(model_alias: str) -> dict | None:
    try:
        result = subprocess.run(
            [
                "python3",
                str(BENCH),
                "--server-url",
                PROXY,
                "--model",
                model_alias,
                "--prompt",
                SPEED_PROMPT,
                "--max-tokens",
                str(MAX_TOKENS),
                "--timeout",
                "180",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except Exception:
        pass
    return None


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        health = fetch_json(f"{PROXY}/health")
        active = fetch_json(f"{PROXY}/active")
    except Exception as e:
        OUT.write_text(json.dumps({
            "status":  "offline",
            "updated": now,
            "error":   str(e),
        }, indent=2))
        return

    backend = active.get("active", health.get("active", "unknown"))
    model_id = active.get("model", "unknown")
    model_name = "local"

    # map internal model IDs to display names
    display = {
        "aeon-nvfp4": "AEON NVFP4",
        "qwen3627b":  "Qwen3 36B MoE",
        "nvidia_Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf": "Nemotron Nano 30B",
        "local":      "local",
    }
    label = display.get(model_id, model_id)

    bench = measure_speed(model_name)
    tok_s = bench.get("gen_tps") if bench else None

    OUT.write_text(json.dumps({
        "status":    "online",
        "active":    backend,
        "model_id":  model_id,
        "model":     label,
        "tok_s":     tok_s,
        "ttft_ms":   bench.get("ttft_ms") if bench else None,
        "completion_tokens": bench.get("completion_tokens") if bench else None,
        "elapsed_s": bench.get("elapsed_s") if bench else None,
        "gen_s":     bench.get("gen_s") if bench else None,
        "end_to_end_tps": bench.get("end_to_end_tps") if bench else None,
        "metric":    "completion_tps_after_first_stream_token_include_usage",
        "updated":   now,
    }, indent=2))
    print(f"{now}  {label}  {tok_s} tok/s")


if __name__ == "__main__":
    main()
