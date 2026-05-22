#!/usr/bin/env python3
"""
bench-bigctx.py — big context bench against live nemotron via proxy :8010
Tests ctx=65536 window with progressively larger inputs.
"""

import json, statistics, time, urllib.request
from datetime import datetime

LOG    = "/home/dino/inference-research/bench-bigctx.log"
URL    = "http://localhost:8010/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}

BASELINE_TPS = 123.6
MAX_TOKENS   = 400

# Base technical passage (~400 tokens). Repeat N times to hit target ctx sizes.
PASSAGE = """
Transformer attention computes query, key, and value projections for each token in the sequence.
The attention score is the dot product of query and key vectors, scaled by the square root of the
head dimension, then passed through softmax to produce a probability distribution over sequence positions.
Each attention head learns different relational patterns — syntactic dependencies, coreference, semantic roles.
Multi-head attention concatenates these views before a final linear projection. The KV cache stores key and
value tensors from previous tokens during autoregressive decoding, allowing O(1) per-step computation at the
cost of O(n) memory growth with sequence length. Flash attention reorders the computation to minimize HBM
reads by fusing the softmax and matmul into a single tiled kernel operating in SRAM. For Mamba SSM layers,
there is no KV cache: the hidden state is a fixed-size vector updated recurrently, giving O(1) memory and
O(1) compute per token regardless of sequence length. The tradeoff is reduced expressivity for distant
dependencies versus full attention. Hybrid architectures interleave SSM and attention layers to balance
long-context efficiency against in-context retrieval capability.
"""

QUESTION = "Summarize the key architectural tradeoffs between attention and SSM layers described above."

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def bench_one(ctx_tokens):
    repeats = max(1, ctx_tokens // len(PASSAGE.split()))
    big_context = (PASSAGE.strip() + "\n\n") * repeats
    prompt = big_context + "\n\n" + QUESTION
    actual_words = len(prompt.split())

    payload = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers=HEADERS)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.loads(r.read())
        elapsed = time.time() - t0
        usage   = resp.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        comp_tokens   = usage.get("completion_tokens", 0)
        tps = comp_tokens / elapsed if elapsed > 0 and comp_tokens > 0 else 0
        return tps, prompt_tokens, comp_tokens, elapsed
    except Exception as e:
        log(f"  error: {e}")
        return None, 0, 0, 0

def main():
    open(LOG, "w").close()
    log(f"bench-bigctx start — {datetime.now().isoformat()}")
    log(f"target: proxy :8010 → nemotron ctx=65536")
    log(f"baseline: {BASELINE_TPS} t/s")

    # warmup
    log("Warmup...")
    bench_one(500)

    ctx_targets = [1000, 4000, 8000, 16000, 32000, 48000]
    results = []

    for target in ctx_targets:
        tps, ptok, ctok, elapsed = bench_one(target)
        if tps:
            delta = tps - BASELINE_TPS
            sign  = "+" if delta >= 0 else ""
            log(f"  ctx~{target:>5}: {tps:6.1f} t/s  prompt={ptok}tok  gen={ctok}tok  {elapsed:.1f}s  ({sign}{delta:.1f} vs baseline)")
            results.append((target, ptok, tps))
        else:
            log(f"  ctx~{target:>5}: FAIL")

    if results:
        tps_vals = [r[2] for r in results]
        log(f"\n{'='*50}")
        log(f"ctx range: {results[0][1]}–{results[-1][1]} tokens")
        log(f"tps range: {min(tps_vals):.1f}–{max(tps_vals):.1f} t/s")
        log(f"degradation 1k→32k+: {tps_vals[0]:.1f} → {tps_vals[-1]:.1f} t/s  ({(tps_vals[-1]-tps_vals[0])/tps_vals[0]*100:+.1f}%)")
        log(f"{'='*50}")

    log("bench-bigctx complete")

if __name__ == "__main__":
    main()
