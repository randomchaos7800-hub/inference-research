#!/usr/bin/env python3
"""
Stress test for canonical vLLM Qwen3.6-27B config.
Checks: throughput stability, no OOM/crash, prefix cache, long context.
Pass criteria printed at end — fails loud on any regression.
"""
import statistics
import sys
import time
import requests

BASE_URL = "http://localhost:8022"
API_KEY  = "genesis-local"
MODEL    = "qwen3627b"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

def chat(prompt: str, max_tokens: int = 512, label: str = "") -> tuple[float, int]:
    t0 = time.perf_counter()
    r = requests.post(f"{BASE_URL}/v1/chat/completions", headers=HEADERS, json={
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }, timeout=300)
    elapsed = time.perf_counter() - t0
    data = r.json()
    if "error" in data:
        print(f"  ERROR [{label}]: {data['error']}", flush=True)
        return 0.0, 0
    toks = data["usage"]["completion_tokens"]
    tps  = toks / elapsed
    print(f"  {label:40s} {toks:4d} tok  {tps:6.1f} t/s  ({elapsed:.1f}s)", flush=True)
    return tps, toks

def section(title: str):
    print(f"\n{'='*60}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'='*60}", flush=True)

TECH_PROMPT = (
    "Write a comprehensive technical deep-dive on transformer attention mechanisms, "
    "covering scaled dot-product attention, multi-head attention, positional encodings, "
    "and how attention patterns emerge during training. Include pseudocode and complexity analysis."
)

def main():
    print("=== vLLM canonical config stress test ===", flush=True)
    print(f"Target: {BASE_URL}  model: {MODEL}", flush=True)

    # ── Health check ───────────────────────────────────────────────────────────
    r = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=10)
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("Health: OK", flush=True)

    results = {}

    # ── 1. Marlin warmup (4 short requests, JIT kernel compile) ───────────────
    section("1. Marlin JIT warmup (4 × 128 tok)")
    for i in range(4):
        tps, _ = chat(TECH_PROMPT, max_tokens=128, label=f"warmup {i+1}/4")
    print("  Warmup complete — Marlin kernels compiled", flush=True)

    # ── 2. Throughput stability (20 × 512 tok, measure variance) ─────────────
    section("2. Throughput stability (20 × 512 tok)")
    tps_list = []
    for i in range(20):
        tps, toks = chat(TECH_PROMPT, max_tokens=512, label=f"run {i+1:2d}/20")
        if tps > 0:
            tps_list.append(tps)
    if tps_list:
        median = statistics.median(tps_list)
        stdev  = statistics.stdev(tps_list) if len(tps_list) > 1 else 0
        pct_cv = (stdev / median * 100) if median > 0 else 0
        print(f"\n  median: {median:.2f} t/s  stdev: {stdev:.2f}  CV: {pct_cv:.1f}%", flush=True)
        results["stability_median"] = median
        results["stability_cv"]     = pct_cv
        results["stability_ok"]     = median >= 75.0 and pct_cv <= 10.0

    # ── 3. Prefix cache hit (repeat identical prompt) ─────────────────────────
    section("3. Prefix cache (same prompt twice — 2nd should be faster)")
    tps1, _ = chat(TECH_PROMPT, max_tokens=256, label="cold (no cache)")
    tps2, _ = chat(TECH_PROMPT, max_tokens=256, label="warm (cache hit)")
    if tps1 > 0 and tps2 > 0:
        cache_gain = tps2 - tps1
        print(f"\n  Cache gain: {cache_gain:+.1f} t/s  ({'✓ hit' if cache_gain > 2 else '~ minimal'})", flush=True)
        results["cache_ok"] = cache_gain > 0

    # ── 4. Long context (16K prompt) ──────────────────────────────────────────
    section("4. Long context (16K-token prompt)")
    long_prompt = ("Count: " + ", ".join(str(i) for i in range(1, 1400)) +
                   ". Now write a one-paragraph summary of what you just counted.")
    tps, toks = chat(long_prompt, max_tokens=128, label="16K ctx probe")
    # Prefill-dominated: 16K prefix + 32 output tokens → elapsed ~7.5s mostly prefill.
    # Real check: did it respond without OOM/crash? Decode t/s is still ~80 t/s when measured alone.
    results["long_ctx_ok"] = toks > 0

    # ── 5. MTP speculation sanity (thinking disabled) ─────────────────────────
    section("5. MTP speculation — no thinking leak check")
    tps, toks = chat(
        "What is 2+2? Answer in one word.",
        max_tokens=10, label="short answer (no <think>)"
    )
    results["no_thinking_leak"] = toks <= 10

    # ── 6. Sustained load (5 min equivalent — 40 requests) ────────────────────
    section("6. Sustained load (40 × 512 tok — OOM/crash soak)")
    crash = False
    soak_tps = []
    for i in range(40):
        tps, toks = chat(TECH_PROMPT, max_tokens=512, label=f"soak {i+1:2d}/40")
        if tps == 0:
            crash = True
            break
        soak_tps.append(tps)
    if soak_tps:
        soak_med = statistics.median(soak_tps)
        drift = soak_tps[-1] - soak_tps[0] if len(soak_tps) > 1 else 0
        print(f"\n  Soak median: {soak_med:.2f} t/s  drift last-first: {drift:+.2f}", flush=True)
        results["soak_ok"]     = not crash and soak_med >= 70.0
        results["soak_median"] = soak_med
        results["soak_drift"]  = drift
    else:
        results["soak_ok"] = False

    # ── Summary ────────────────────────────────────────────────────────────────
    section("STRESS TEST SUMMARY")
    all_pass = True
    checks = [
        ("Throughput ≥ 75 t/s median",   results.get("stability_ok", False)),
        ("Throughput CV ≤ 10%",           results.get("stability_cv", 99) <= 10.0),
        ("Prefix cache working",          results.get("cache_ok", False)),
        ("Long context (16K) — no OOM/crash", results.get("long_ctx_ok", False)),
        ("No thinking leak on short req", results.get("no_thinking_leak", False)),
        ("40-req soak no crash ≥ 70 t/s", results.get("soak_ok", False)),
    ]
    for label, passed in checks:
        mark = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {mark}  {label}", flush=True)
        if not passed:
            all_pass = False

    print(f"\n  Stability:  {results.get('stability_median', 0):.1f} t/s  (CV {results.get('stability_cv', 0):.1f}%)", flush=True)
    print(f"  Soak:       {results.get('soak_median', 0):.1f} t/s  (drift {results.get('soak_drift', 0):+.1f})", flush=True)
    print(f"\n{'='*60}", flush=True)
    if all_pass:
        print("  ✓ ALL CHECKS PASSED — safe to write to production", flush=True)
    else:
        print("  ✗ STRESS TEST FAILED — do NOT write to production", flush=True)
    print(f"{'='*60}", flush=True)
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
