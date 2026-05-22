#!/usr/bin/env python3
"""
Pass 4: Throughput regression fix + context ceiling confirmation for Qwen3.6-27B.

Goals:
  1. Regression check — confirm baseline (32K/0.82/auto) is still ~80 t/s
  2. fp8 KV impact — current broken script uses fp8; pass3 used auto; measure delta
  3. High-ctx sweep with fp8 — fp8 KV gives more VRAM headroom; find max stable ctx
  4. Throughput squeeze — can we hit 85 t/s with any config?
  5. EVERY experiment includes a 16K ctx probe (real long prompt) to catch OOM before production
  6. Writes winner config to production start script

Decision gate: tg512 >= 85 t/s → promote to Mike substrate
Fallback: highest stable ctx with tg512 >= 78 t/s (within 3% of pass3 baseline)

Fixes vs pass3:
  - SCRIPT path corrected to /home/dino/bin/vllm-genesis-start.sh
  - Added ctx_probe() — sends ~16K token prompt, verifies no OOM/crash
  - Writes winner config to production script at end
"""
import datetime
import os
import statistics
import subprocess
import sys
import time

import requests

LOG     = "/home/dino/inference-research/autoresearch-vllm-27b-pass4-log.md"
TSV     = "/home/dino/inference-research/autoresearch-vllm-27b-pass4-results.tsv"
SCRIPT  = "/home/dino/bin/vllm-genesis-start.sh"
BASE_URL = "http://localhost:8022"
API_KEY  = "genesis-local"
MODEL    = "qwen3627b"
HEADERS  = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

# Canonical baseline — same as pass3 winner (32K/0.82/auto = 80.65 t/s)
BASELINE = {
    "gpu_memory_utilization":                0.82,
    "max_model_len":                         32768,
    "max_num_seqs":                          2,
    "max_num_batched_tokens":                4096,
    "kv_cache_dtype":                        "auto",
    "mtp_n":                                 3,
    "NCCL_P2P_DISABLE":                      "1",
    "VLLM_USE_FLASHINFER_SAMPLER":           "1",
    "OMP_NUM_THREADS":                       "1",
    "CUDA_DEVICE_MAX_CONNECTIONS":           "8",
    "GENESIS_BUFFER_MODE":                   "shared",
    "GENESIS_PREALLOC_TOKEN_BUDGET":         "4096",
    "VLLM_MARLIN_USE_ATOMIC_ADD":            "1",
    "VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE": str(413 * 1024 * 1024),
    "NCCL_BUFFSIZE":                         "4194304",
    "PYTORCH_MAX_SPLIT_MB":                  "512",
}

# Part A: regression check + kv_cache_dtype delta (2)
# Part B: high-ctx with fp8 KV — fp8 frees VRAM for longer ctx (5)
# Part C: throughput squeeze at 32K — can we beat 85 t/s? (4)
EXPERIMENTS = [
    # A: baseline regression + fp8 comparison
    ("32K/0.82/fp8",   {"kv_cache_dtype": "fp8"}),
    ("32K/0.82/0.80",  {"gpu_memory_utilization": 0.80}),

    # B: high-ctx with fp8 KV (pass3 showed 128K/0.90/auto = 80.04; fp8 should extend ceiling)
    ("96K/0.85/fp8",   {"max_model_len": 98304,  "gpu_memory_utilization": 0.85, "kv_cache_dtype": "fp8"}),
    ("128K/0.85/fp8",  {"max_model_len": 131072, "gpu_memory_utilization": 0.85, "kv_cache_dtype": "fp8"}),
    ("128K/0.88/fp8",  {"max_model_len": 131072, "gpu_memory_utilization": 0.88, "kv_cache_dtype": "fp8"}),
    ("128K/0.90/auto", {"max_model_len": 131072, "gpu_memory_utilization": 0.90}),  # pass3 winner reconfirm
    ("128K/0.90/fp8",  {"max_model_len": 131072, "gpu_memory_utilization": 0.90, "kv_cache_dtype": "fp8"}),
    ("160K/0.90/fp8",  {"max_model_len": 163840, "gpu_memory_utilization": 0.90, "kv_cache_dtype": "fp8"}),
    ("160K/0.92/fp8",  {"max_model_len": 163840, "gpu_memory_utilization": 0.92, "kv_cache_dtype": "fp8"}),

    # C: throughput squeeze — smaller batch budget, more MTP tokens
    ("32K/0.82/b2048",  {"max_num_batched_tokens": 2048}),
    ("32K/0.82/b8192",  {"max_num_batched_tokens": 8192, "GENESIS_PREALLOC_TOKEN_BUDGET": "8192"}),
    ("32K/0.82/mtp4",   {"mtp_n": 4}),
    ("32K/0.82/s1",     {"max_num_seqs": 1}),
]

TECH_PROMPT = (
    "Write a comprehensive technical deep-dive on transformer attention mechanisms, "
    "covering scaled dot-product attention, multi-head attention, positional encodings, "
    "and how attention patterns emerge during training. Include pseudocode and complexity analysis."
)

# ~16K token prompt for ctx probe — counting sequence stresses KV allocator
_CTX_PROBE_PAYLOAD = (
    "Count from 1 to 1200 in English words, then summarize what you counted in one sentence: "
    + ", ".join(str(i) for i in range(1, 1201))
    + ". Summary:"
)


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def log(msg):
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def completions(prompt, max_tokens=512, timeout=120):
    t0 = time.perf_counter()
    try:
        r = requests.post(f"{BASE_URL}/v1/completions", headers=HEADERS, json={
            "model":       MODEL,
            "prompt":      prompt,
            "max_tokens":  max_tokens,
            "temperature": 0.0,
            "stream":      False,
        }, timeout=timeout)
        elapsed = time.perf_counter() - t0
        data = r.json()
        if "error" in data:
            return 0.0, 0, data["error"]
        toks = data["usage"]["completion_tokens"]
        tps  = toks / elapsed if elapsed > 0 else 0.0
        return tps, toks, None
    except Exception as e:
        return 0.0, 0, str(e)


def wait_healthy(timeout=210):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(5)
    return False


def ctx_probe():
    """Send a ~16K token prompt and return (ok, prompt_tokens, error_msg)."""
    try:
        r = requests.post(f"{BASE_URL}/v1/completions", headers=HEADERS, json={
            "model":       MODEL,
            "prompt":      _CTX_PROBE_PAYLOAD,
            "max_tokens":  50,
            "temperature": 0.0,
            "stream":      False,
        }, timeout=90)
        data = r.json()
        if "error" in data:
            return False, 0, str(data["error"])
        ptoks = data.get("usage", {}).get("prompt_tokens", 0)
        return True, ptoks, None
    except Exception as e:
        return False, 0, str(e)


def write_launch_script(cfg, label="pass4-winner"):
    gmu       = cfg["gpu_memory_utilization"]
    ctx       = cfg["max_model_len"]
    seqs      = cfg["max_num_seqs"]
    batched   = cfg["max_num_batched_tokens"]
    kv_dtype  = cfg["kv_cache_dtype"]
    mtp_n     = cfg["mtp_n"]
    nccl_p2p  = cfg.get("NCCL_P2P_DISABLE", "1")
    fi_samp   = cfg.get("VLLM_USE_FLASHINFER_SAMPLER", "1")
    omp       = cfg.get("OMP_NUM_THREADS", "1")
    cuda_conn = cfg.get("CUDA_DEVICE_MAX_CONNECTIONS", "8")
    g_buf     = cfg.get("GENESIS_BUFFER_MODE", "shared")
    prealloc  = str(max(int(cfg.get("GENESIS_PREALLOC_TOKEN_BUDGET", "4096")), batched))
    marlin_aa = cfg.get("VLLM_MARLIN_USE_ATOMIC_ADD", "1")
    fi_ws     = cfg.get("VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE", str(413 * 1024 * 1024))
    nccl_buf  = cfg.get("NCCL_BUFFSIZE", "4194304")
    max_split = cfg.get("PYTORCH_MAX_SPLIT_MB", "512")
    now_str   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    content = f"""#!/bin/bash
# Qwen3.6-27B AutoRound INT4 — vLLM + Genesis — dual RTX 5060 Ti (32GB)
# Generated by autoresearch-vllm-27b-pass4.py ({label}) — {now_str}
# Config: {{gpu_memory_utilization: {gmu}, max_model_len: {ctx}, max_num_seqs: {seqs}, max_num_batched_tokens: {batched}, kv_cache_dtype: {kv_dtype}, mtp_n: {mtp_n}}}

export PATH=/usr/local/cuda-13.0/bin:$PATH
export LD_LIBRARY_PATH=${{LD_LIBRARY_PATH:-}}:/usr/local/cuda-13.0/lib64
export CUDA_HOME=/usr/local/cuda-13.0

export VLLM_NO_USAGE_STATS=1
export VLLM_USE_FLASHINFER_SAMPLER={fi_samp}
export VLLM_FLOAT32_MATMUL_PRECISION=high
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_LOGGING_LEVEL=WARNING
export VLLM_MARLIN_USE_ATOMIC_ADD={marlin_aa}
export VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE={fi_ws}
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:{max_split}
export NCCL_P2P_DISABLE={nccl_p2p}
export NCCL_BUFFSIZE={nccl_buf}
export OMP_NUM_THREADS={omp}
export CUDA_DEVICE_MAX_CONNECTIONS={cuda_conn}

export GENESIS_ENABLE_P60_GDN_NGRAM_FIX=1
export GENESIS_ENABLE_P60B_TRITON_KERNEL=1
export GENESIS_ENABLE_P64_QWEN3CODER_MTP_STREAMING=1
export GENESIS_ENABLE_P67_TQ_MULTI_QUERY_KERNEL=1
export GENESIS_ENABLE_P67B=1
export GENESIS_ENABLE_P70_AUTO_STRICT_NGRAM=1
export GENESIS_ENABLE_P72_PROFILE_RUN_CAP=1
export GENESIS_ENABLE_P74_CHUNK_CLAMP=1
export GENESIS_ENABLE_P77_ADAPTIVE_NGRAM_K=1
export GENESIS_ENABLE_P78_TOLIST_CAPTURE_GUARD=1
export GENESIS_ENABLE_P82=1
export GENESIS_P82_THRESHOLD_SINGLE=0.3
export GENESIS_BUFFER_MODE={g_buf}
export GENESIS_PREALLOC_TOKEN_BUDGET={prealloc}

/opt/ai/vllm-env/bin/python3 -m vllm._genesis.patches.apply_all

exec /opt/ai/vllm-env/bin/vllm serve \\
  /home/dino/models/Qwen3.6-27B-int4-AutoRound \\
  --quantization gptq_marlin \\
  --tensor-parallel-size 2 \\
  --gpu-memory-utilization {gmu} \\
  --max-model-len {ctx} \\
  --kv-cache-dtype {kv_dtype} \\
  --max-num-seqs {seqs} \\
  --max-num-batched-tokens {batched} \\
  --enable-chunked-prefill \\
  --enable-prefix-caching \\
  --dtype bfloat16 \\
  --disable-custom-all-reduce \\
  --trust-remote-code \\
  --language-model-only \\
  --enable-auto-tool-choice \\
  --tool-call-parser qwen3_coder \\
  --reasoning-parser qwen3 \\
  --speculative-config '{{"method":"mtp","num_speculative_tokens":{mtp_n}}}' \\
  --prefix-caching-hash-algo xxhash \\
  --api-key genesis-local \\
  --served-model-name qwen3627b \\
  --host 0.0.0.0 \\
  --port 8022 \\
  --disable-log-stats
"""
    with open(SCRIPT, "w") as f:
        f.write(content)
    os.chmod(SCRIPT, 0o755)


def restart_service():
    subprocess.run(["systemctl", "--user", "restart", "vllm-genesis.service"], check=True)
    time.sleep(10)


def bench(n=10, max_tokens=512):
    tps_list = []
    for _ in range(n):
        tps, _, _ = completions(TECH_PROMPT, max_tokens=max_tokens)
        if tps > 0:
            tps_list.append(tps)
    if not tps_list:
        return 0.0, 0.0
    med = statistics.median(tps_list)
    p90 = sorted(tps_list)[int(len(tps_list) * 0.9)]
    return med, p90


def run_experiment(idx, name, overrides, baseline_median):
    cfg = {**BASELINE, **overrides}
    ctx  = cfg["max_model_len"]
    gmu  = cfg["gpu_memory_utilization"]
    kv   = cfg["kv_cache_dtype"]

    log(f"--- Exp {idx}: {name}  ctx={ctx}  gmu={gmu}  kv={kv} ---")
    write_launch_script(cfg, label=name)
    restart_service()

    if not wait_healthy(210):
        log(f"  TIMEOUT — did not become healthy in 3.5 min")
        return 0.0, 0.0, False, "TIMEOUT"

    log("  healthy — Marlin warmup (4×128)")
    for _ in range(4):
        completions(TECH_PROMPT, max_tokens=128)

    # ctx probe first — bail early if it OOMs
    log("  ctx probe (~16K tokens) ...")
    ok, ptoks, err = ctx_probe()
    if not ok:
        log(f"  ctx probe FAILED: {err}")
        return 0.0, 0.0, False, "CTX_OOM"

    log(f"  ctx probe OK — prompt_tokens={ptoks}")

    log("  benchmarking (10×512)")
    median, p90 = bench(10, 512)
    if median == 0:
        log("  FAILED — no successful bench requests")
        return 0.0, 0.0, True, "BENCH_FAIL"

    delta = median - baseline_median
    pct   = delta / baseline_median * 100
    log(f"  median={median:.2f} t/s  p90={p90:.2f}  delta={delta:+.2f} ({pct:+.1f}%)")

    if median >= 85.0:
        outcome = "GATE_HIT"      # beats the 85 t/s decision gate
    elif delta >= 1.0:
        outcome = "IMPROVEMENT"
    elif pct >= -5.0:
        outcome = "MARGINAL"
    elif pct >= -10.0:
        outcome = "DEGRADED"
    else:
        outcome = "BAD"

    return median, p90, True, outcome


def write_tsv_row(f, idx, name, ctx, gmu, kv, median, p90, delta, ctx_ok, outcome):
    ctx_str = "OK" if ctx_ok else "FAIL"
    f.write(f"{idx}\t{name}\t{ctx}\t{gmu:.2f}\t{kv}\t{median:.2f}\t{p90:.2f}\t{delta:+.2f}\t{ctx_str}\t{outcome}\n")
    f.flush()


def main():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG, "w") as f:
        f.write(f"# autoresearch-vllm-27b-pass4  started {now_str}\n\n")
    with open(TSV, "w") as f:
        f.write("iter\tname\tmax_model_len\tgmu\tkv\ttg_median\ttg_p90\tdelta\tctx_probe\toutcome\n")

    log("=== Pass 4: Regression fix + fp8 ctx ceiling + throughput squeeze ===")
    log(f"Experiments: {len(EXPERIMENTS) + 1} (baseline + {len(EXPERIMENTS)})")
    log(f"Decision gate: 85 t/s tg512 AND 16K ctx probe passes")

    # ── Baseline ──────────────────────────────────────────────────────────────
    log("\n## [0] Baseline: 32K/0.82/auto")
    write_launch_script(BASELINE, label="baseline")
    restart_service()
    if not wait_healthy(210):
        log("FATAL: baseline did not start")
        sys.exit(1)

    log("  warming up (4×128)")
    for _ in range(4):
        completions(TECH_PROMPT, max_tokens=128)

    log("  ctx probe")
    ok, ptoks, err = ctx_probe()
    log(f"  ctx probe: {'OK prompt_tokens=' + str(ptoks) if ok else 'FAIL: ' + str(err)}")

    log("  benchmarking (10×512)")
    baseline_median, baseline_p90 = bench(10, 512)
    log(f"  Baseline: {baseline_median:.2f} t/s  p90={baseline_p90:.2f}")

    with open(TSV, "a") as f:
        write_tsv_row(f, 0, "baseline", BASELINE["max_model_len"],
                      BASELINE["gpu_memory_utilization"], BASELINE["kv_cache_dtype"],
                      baseline_median, baseline_p90, 0.0, ok, "BASELINE")

    # Track bests
    best_tps  = {"name": "baseline", "median": baseline_median, "ctx": BASELINE["max_model_len"],
                 "cfg": dict(BASELINE), "ctx_ok": ok}
    best_ctx  = {"name": "baseline", "median": baseline_median, "ctx": BASELINE["max_model_len"],
                 "cfg": dict(BASELINE), "ctx_ok": ok}

    # ── Experiments ───────────────────────────────────────────────────────────
    for i, (name, overrides) in enumerate(EXPERIMENTS, 1):
        with open(LOG, "a") as f:
            f.write(f"\n## [{i}/{len(EXPERIMENTS)}] {name}\n")

        median, p90, ctx_ok, outcome = run_experiment(i, name, overrides, baseline_median)
        delta = median - baseline_median
        cfg   = {**BASELINE, **overrides}

        with open(TSV, "a") as f:
            write_tsv_row(f, i, name,
                          cfg["max_model_len"], cfg["gpu_memory_utilization"], cfg["kv_cache_dtype"],
                          median, p90, delta, ctx_ok, outcome)

        if median > 0 and ctx_ok:
            if median > best_tps["median"]:
                best_tps = {"name": name, "median": median, "ctx": cfg["max_model_len"],
                            "cfg": cfg, "ctx_ok": ctx_ok}
                log(f"  → new best tps: {name}  {median:.2f} t/s")
            if cfg["max_model_len"] > best_ctx["ctx"] and outcome in ("GATE_HIT", "IMPROVEMENT", "MARGINAL"):
                best_ctx = {"name": name, "median": median, "ctx": cfg["max_model_len"],
                            "cfg": cfg, "ctx_ok": ctx_ok}
                log(f"  → new best ctx: {name}  {cfg['max_model_len']} tok  {median:.2f} t/s")

    # ── Pick winner and write production script ───────────────────────────────
    # Prefer: highest ctx that passed probe AND tps >= 78 t/s (within 3% of baseline)
    # If best_ctx beats that, use it; otherwise fall back to best_tps
    winner = best_ctx if best_ctx["median"] >= 78.0 and best_ctx["ctx_ok"] else best_tps
    winner_label = f"pass4-winner ({winner['name']})"
    write_launch_script(winner["cfg"], label=winner_label)
    restart_service()
    healthy = wait_healthy(210)

    log("\n=== PASS 4 COMPLETE ===")
    log(f"  Baseline:   {baseline_median:.2f} t/s @ 32K ctx (GMU 0.82 / auto)")
    log(f"  Best tps:   {best_tps['name']}  {best_tps['median']:.2f} t/s  ctx={best_tps['ctx']}")
    log(f"  Best ctx:   {best_ctx['name']}  {best_ctx['median']:.2f} t/s  ctx={best_ctx['ctx']}")
    log(f"  → WINNER:   {winner['name']}  {winner['median']:.2f} t/s  ctx={winner['ctx']}")
    gate = "PASS" if winner["median"] >= 85.0 else "FAIL"
    log(f"  85 t/s gate: {gate}")
    log(f"  Production script written to {SCRIPT}")
    log(f"  Service restarted: {'healthy' if healthy else 'UNHEALTHY — check logs'}")

    with open(LOG, "a") as f:
        f.write(f"\n## PASS 4 COMPLETE — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Winner: {winner}\n")
        f.write(f"85 t/s gate: {gate}\n")


if __name__ == "__main__":
    main()
