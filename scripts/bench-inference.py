#!/usr/bin/env python3
"""Benchmark local inference through the tower proxy."""

import argparse
import json
import os
import subprocess
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse


def run_benchmark(
    server_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: int,
    api_key: str | None,
) -> dict:
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
    ).encode()

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        f"{server_url.rstrip('/')}/v1/chat/completions",
        data=payload,
        headers=headers,
    )

    start = time.time()
    first_token_at = None
    end = start
    usage = None
    chunks = 0

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw_line in resp:
            line = raw_line.decode().strip()
            if not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                end = time.time()
                break

            chunk = json.loads(line[6:])
            chunks += 1
            if chunk.get("usage"):
                usage = chunk["usage"]

            choices = chunk.get("choices") or []
            if not choices:
                continue

            delta = choices[0].get("delta", {})
            token_text = delta.get("reasoning_content") or delta.get("content") or ""
            if token_text and first_token_at is None:
                first_token_at = time.time()

    if first_token_at is None:
        raise RuntimeError("benchmark produced no streamed content")
    if not usage or usage.get("completion_tokens", 0) <= 0:
        raise RuntimeError("benchmark response did not include completion token usage")

    completion_tokens = int(usage["completion_tokens"])
    elapsed_s = end - start
    gen_s = end - first_token_at

    return {
        "model_id": model,
        "ttft_ms": round((first_token_at - start) * 1000, 1),
        "elapsed_s": round(elapsed_s, 3),
        "gen_s": round(gen_s, 3),
        "completion_tokens": completion_tokens,
        "end_to_end_tps": round(completion_tokens / elapsed_s, 1),
        "gen_tps": round(completion_tokens / gen_s, 1),
        "chunks": chunks,
    }


def tower_backend_settings(server_url: str) -> dict[str, str]:
    """Fetch the active tower backend URL and auth key from the tower config."""

    parsed = urlparse(server_url)
    host = parsed.hostname or ""
    if host not in {"100.120.50.35", "cha0tiktower"}:
        return {}

    result = subprocess.run(
        [
            "ssh",
            "dino@100.120.50.35",
            r"""python3 - <<'PY'
import json
from pathlib import Path
import tomllib

config = tomllib.loads(Path('/home/dino/local-proxy/config.toml').read_text())
active = config.get('active')
backend = config.get('backends', {}).get(active, {})
print(json.dumps({'active': active, 'url': backend.get('url', ''), 'key': backend.get('key', '')}))
PY""",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def resolve_model(server_url: str, model: str, api_key: str | None) -> tuple[str, str | None]:
    """Return the real model ID and the auth key needed to query the backend."""

    if model != "local":
        return model, api_key

    settings = tower_backend_settings(server_url)
    key = api_key or settings.get("key") or os.environ.get("LOCAL_PROXY_API_KEY") or os.environ.get("TOWER_PROXY_API_KEY")
    backend_url = settings.get("url", "")

    if not key or not backend_url:
        return model, api_key

    parsed_server = urlparse(server_url)
    parsed_backend = urlparse(backend_url)
    backend_host = parsed_backend.hostname or parsed_server.hostname or "100.120.50.35"
    if backend_host in {"localhost", "127.0.0.1"}:
        backend_host = parsed_server.hostname or "100.120.50.35"
    backend_netloc = backend_host
    if parsed_backend.port:
        backend_netloc += f":{parsed_backend.port}"
    backend_base = parsed_backend._replace(netloc=backend_netloc).geturl()

    req = urllib.request.Request(
        f"{backend_base.rstrip('/')}/models",
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "curl/8.5.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read())
    data = payload.get("data") or []
    if not data:
        return model, key
    return data[0]["id"], key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", default="http://100.120.50.35:8010")
    parser.add_argument("--model", default="local", help="Model alias or real model ID. 'local' auto-discovers the tower backend model.")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-tokens", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--api-key")
    args = parser.parse_args()

    model, api_key = resolve_model(args.server_url, args.model, args.api_key)

    print(
        json.dumps(
            run_benchmark(
                args.server_url,
                model,
                args.prompt,
                args.max_tokens,
                args.timeout,
                api_key,
            )
        )
    )


if __name__ == "__main__":
    main()
