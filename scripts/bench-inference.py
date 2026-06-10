#!/usr/bin/env python3
"""Benchmark local inference through the tower proxy."""

import argparse
import json
import time
import urllib.request
import urllib.error


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
        "ttft_ms": round((first_token_at - start) * 1000, 1),
        "elapsed_s": round(elapsed_s, 3),
        "gen_s": round(gen_s, 3),
        "completion_tokens": completion_tokens,
        "end_to_end_tps": round(completion_tokens / elapsed_s, 1),
        "gen_tps": round(completion_tokens / gen_s, 1),
        "chunks": chunks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", default="http://100.120.50.35:8010")
    parser.add_argument("--model", default="local")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-tokens", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--api-key")
    args = parser.parse_args()

    print(
        json.dumps(
            run_benchmark(
                args.server_url,
                args.model,
                args.prompt,
                args.max_tokens,
                args.timeout,
                args.api_key,
            )
        )
    )


if __name__ == "__main__":
    main()
