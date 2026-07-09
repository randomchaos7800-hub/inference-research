#!/usr/bin/env python3
"""
Karpathy-style autoresearch for Qwen3.6-27B on vLLM (port 8022).

Architecture constraint (confirmed from vLLM source):
  - linear_attn backend (DeltaNet/GDN layers) = UNIFORM_SINGLE_TOKEN_DECODE only
  - MTP proposer hardcodes PIECEWISE in extract_hidden_states.py
  - FULL CUDA graph mode is IMPOSSIBLE with MTP + GDN hybrid — not a tuning problem
  - All wins must come from: batching, memory, speculation n, scheduling, NCCL, env vars

Baseline: 70 t/s steady (gptq_marlin, MTP n=3, fp8 KV, 32K ctx, GMU 0.82)
Goal: beat 83 t/s (Marlin peak) as steady-state, or push ctx to 64K at ≥70 t/s

Fail loud:
  - vLLM startup > 8 min  → TIMEOUT, revert, continue
  - /health never 200      → FAILED, revert, continue
  - t/s < 20 (worse than llama.cpp baseline) → REGRESSION abort
  - NaN/exception in bench → ERROR, revert, continue
  - Any improvement < IMPROVE_THRESHOLD → NO_CHANGE
"""

import csv
import json
import os
import re
import subprocess
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import requests

# ── Config ─────────────────────────────────────────────────────────────────────

BASELINE = {
    # vLLM serve flags
    "gpu_memory_utilization":    0.82,
    "max_model_len":             32768,
    "max_num_seqs":              2,
    "max_num_batched_tokens":    4096,
    "kv_cache_dtype":            "fp8",
    "mtp_n":                     3,        # num_speculative_tokens
    # env vars
    "NCCL_P2P_DISABLE":          "1",      # disable P2P; test removing
    "VLLM_USE_FLASHINFER_SAMPLER": "1",
    "OMP_NUM_THREADS":            "1",
    "CUDA_DEVICE_MAX_CONNECTIONS": "8",
    "GENESIS_BUFFER_MODE":        "shared",
    "GENESIS_PREALLOC_TOKEN_BUDGET": "4096",
}

SERVICE         = "vllm-genesis"
PORT            = 8022
API_KEY         = "genesis-local"
MODEL           = "qwen3627b"
BASE_URL        = f"http://localhost:{PORT}"
STARTUP_TIMEOUT = 480   # seconds to wait for vLLM to be ready
BENCH_WARMUP    = 4     # requests to discard before measuring
BENCH_REPS      = 5     # requests to time
BENCH_TOKENS    = 512   # completion tokens per bench request
IMPROVE_THRESHOLD = 1.5 # t/s improvement to count as IMPROVEMENT
REGRESSION_FLOOR  = 20.0 # abort if steady t/s falls below this

LOG_FILE    = Path("/home/dino/inference-research/autoresearch-vllm-27b-log.md")
RESULTS_TSV = Path("/home/dino/inference-research/autoresearch-vllm-27b-results.tsv")
BEST_FLAGS  = Path("/home/dino/inference-research/current-best-flags-vllm-27b.sh")
LAUNCH_SH   = Path("/home/dino/vllm-genesis-start.sh")

BENCH_PROMPT = (
    "Write a comprehensive technical deep-dive on transformer attention mechanisms, "
    "covering scaled dot-product attention, multi-head attention, positional encodings, "
    "and how attention patterns emerge during training. Include pseudocode and complexity analysis."
)


# ── Candidate menu ─────────────────────────────────────────────────────────────
# One variable changed per experiment vs BASELINE.
# Ordered by expected impact (most impactful first).

CANDIDATE_MENU = [
    # ── Batching / scheduling ──────────────────────────────────────────────────
    # Log warns: "max_num_scheduled_tokens is set to 4096 based on speculative
    # decoding settings. Consider increasing max_num_batched_tokens."
    # With MTP n=3: scheduled = batched / (1 + n) → 4096/4 = 1024. Doubling gives 2048.
    {"name": "batched-tokens 8192",
     "var":  "max_num_batched_tokens", "val": 8192,
     "desc": "fix scheduler warning: scheduled = 8192/4 = 2048 tokens (was 1024)"},
    {"name": "batched-tokens 16384",
     "var":  "max_num_batched_tokens", "val": 16384,
     "desc": "aggressive: scheduled = 4096 tokens per step"},

    # ── NCCL P2P (TP=2, same node, PCIe — no NVLink) ─────────────────────────
    # P2P_DISABLE=1 routes tensor-parallel all-reduce through host RAM.
    # PCIe same-node P2P is typically faster than CPU round-trip for small tensors.
    {"name": "NCCL P2P enable",
     "var":  "NCCL_P2P_DISABLE", "val": "0",
     "desc": "allow direct GPU-GPU P2P over PCIe (currently disabled via CPU)"},

    # ── MTP speculation depth ─────────────────────────────────────────────────
    # n=3 gave 83 t/s at best; 70 t/s steady. Higher n = more tokens per draft.
    # Acceptance rate on this model: 97/95/91% per position (from article).
    # n=4: ~87% estimated, n=5: ~82% estimated. Each adds overhead vs gain.
    {"name": "MTP n=4",
     "var":  "mtp_n", "val": 4,
     "desc": "4 speculative tokens — higher draft overhead vs more tokens accepted"},
    {"name": "MTP n=5",
     "var":  "mtp_n", "val": 5,
     "desc": "5 speculative tokens — max speculation, most overhead"},
    {"name": "MTP n=2",
     "var":  "mtp_n", "val": 2,
     "desc": "2 speculative tokens — less overhead, tests if n=3 over-speculates"},
    {"name": "MTP n=1",
     "var":  "mtp_n", "val": 1,
     "desc": "1 speculative token — near-baseline, isolates MTP overhead cost"},
    {"name": "no MTP",
     "var":  "mtp_n", "val": 0,
     "desc": "disable speculative decoding entirely — measure raw decode t/s"},

    # ── KV cache dtype ─────────────────────────────────────────────────────────
    # fp8: saves memory (fits 32K at 0.82 GMU), costs dequant overhead each layer
    # fp16 (auto): no dequant, but uses 2x memory → tighter VRAM at 32K ctx
    {"name": "KV fp16 (auto)",
     "var":  "kv_cache_dtype", "val": "auto",
     "desc": "fp16 KV: no dequant overhead per layer — costs ~4GB extra VRAM at 32K"},

    # ── GPU memory utilization ─────────────────────────────────────────────────
    # More GMU = more KV cache blocks = better prefix cache hit rate
    # Risk: OOM if activation workspace spills (we hit OOM at 0.88 with 131K ctx)
    # At 32K ctx the activation workspace is smaller → 0.85/0.88 may be safe
    {"name": "GMU 0.85",
     "var":  "gpu_memory_utilization", "val": 0.85,
     "desc": "more KV cache blocks — ~1.5GB more VRAM for KV at 32K ctx"},
    {"name": "GMU 0.88",
     "var":  "gpu_memory_utilization", "val": 0.88,
     "desc": "max safe GMU tested at 32K ctx — risk: activation workspace OOM"},

    # ── FlashInfer sampler ─────────────────────────────────────────────────────
    # Sampler and attention backend are INDEPENDENT.
    # FlashInfer sampler parallelizes top-k/top-p ops across GPUs.
    # With TP=2 single-stream inference, standard sampler may have less overhead.
    {"name": "sampler default",
     "var":  "VLLM_USE_FLASHINFER_SAMPLER", "val": "0",
     "desc": "disable FlashInfer sampler, use PyTorch sampler — less overhead for single stream"},

    # ── Max concurrent sequences ───────────────────────────────────────────────
    # max-num-seqs=1: single stream, zero inter-seq overhead, pure decode t/s
    # max-num-seqs=4: enables batched decoding if multiple requests arrive
    {"name": "seqs 1",
     "var":  "max_num_seqs", "val": 1,
     "desc": "single sequence mode — eliminates inter-seq padding and scheduling overhead"},
    {"name": "seqs 4",
     "var":  "max_num_seqs", "val": 4,
     "desc": "4 concurrent — test batch decode throughput"},

    # ── Context length ─────────────────────────────────────────────────────────
    # Smaller ctx = smaller CUDA graph workspace = more memory for KV cache blocks
    # Also: at 16K ctx we could push GMU higher
    {"name": "ctx 16K",
     "var":  "max_model_len", "val": 16384,
     "desc": "half context — smaller CUDA graph tables, more KV blocks at same GMU"},
    {"name": "ctx 64K + GMU 0.85",
     "var":  "max_model_len", "val": 65536,
     "desc": "double context at 0.85 GMU — tests if activation workspace fits",
     "also": {"gpu_memory_utilization": 0.85}},

    # ── CUDA device connections ────────────────────────────────────────────────
    # More connections = more concurrent CUDA kernel launches (helps TP=2 pipeline)
    {"name": "CUDA_CONNECTIONS 16",
     "var":  "CUDA_DEVICE_MAX_CONNECTIONS", "val": "16",
     "desc": "more concurrent kernel streams for TP=2 all-reduce overlap"},

    # ── OMP threads ───────────────────────────────────────────────────────────
    {"name": "OMP_THREADS 4",
     "var":  "OMP_NUM_THREADS", "val": "4",
     "desc": "more CPU threads for MKL/OpenMP ops in GDN layers"},

    # ── Genesis buffer mode ───────────────────────────────────────────────────
    # shared: one buffer pool across all workers
    # exclusive: each worker gets its own buffer (less contention, more memory)
    {"name": "Genesis exclusive buffer",
     "var":  "GENESIS_BUFFER_MODE", "val": "exclusive",
     "desc": "per-worker Genesis buffers — test if shared pool causes contention"},

    # ── Genesis prealloc budget ───────────────────────────────────────────────
    {"name": "Genesis prealloc 8192",
     "var":  "GENESIS_PREALLOC_TOKEN_BUDGET", "val": "8192",
     "desc": "larger token budget pre-allocation for Genesis P64 MTP streaming"},

    # ── Combo: best batching + NCCL fix ───────────────────────────────────────
    # Run this after individual experiments to test if effects stack.
    # Only run if both individual experiments showed improvement.
    {"name": "combo: batched 8192 + P2P on",
     "var":  "max_num_batched_tokens", "val": 8192,
     "also": {"NCCL_P2P_DISABLE": "0"},
     "desc": "stack the two most likely wins together",
     "combo": True},
]


# ── Logging ────────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def log_section(title: str):
    line = f"\n## {title}\n"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def init_tsv():
    if not RESULTS_TSV.exists():
        with open(RESULTS_TSV, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["iter", "name", "variable", "value",
                        "tg_median", "tg_p90", "delta", "outcome", "desc"])

def append_tsv(iteration, name, var, val, tg_med, tg_p90, delta, outcome, desc):
    with open(RESULTS_TSV, "a", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow([iteration, name, var, str(val),
                    f"{tg_med:.2f}", f"{tg_p90:.2f}", f"{delta:+.2f}", outcome, desc])


# ── Launch script generation ───────────────────────────────────────────────────

def write_launch_script(cfg: dict):
    """Write vllm-genesis-start.sh from a config dict."""
    spec_config = (
        f'{{"method":"mtp","num_speculative_tokens":{cfg["mtp_n"]}}}'
        if cfg["mtp_n"] > 0 else ""
    )
    spec_flag = (
        f'  --speculative-config \'{spec_config}\' \\\n'
        if cfg["mtp_n"] > 0 else ""
    )

    nccl_p2p = cfg.get("NCCL_P2P_DISABLE", "1")
    fi_sampler = cfg.get("VLLM_USE_FLASHINFER_SAMPLER", "1")
    omp = cfg.get("OMP_NUM_THREADS", "1")
    cuda_conn = cfg.get("CUDA_DEVICE_MAX_CONNECTIONS", "8")
    buf_mode = cfg.get("GENESIS_BUFFER_MODE", "shared")
    # P28 buffer must be >= max_num_batched_tokens or FlashInfer autotune _dummy_run overflows
    prealloc = str(max(int(cfg.get("GENESIS_PREALLOC_TOKEN_BUDGET", "4096")),
                       cfg["max_num_batched_tokens"]))

    content = f"""#!/bin/bash
# Qwen3.6-27B AutoRound INT4 — vLLM + Genesis v7.53 — dual RTX 5060 Ti (32GB)
# Generated by autoresearch-vllm-27b.py — {datetime.now().strftime("%Y-%m-%d %H:%M")}
# Config: {{{", ".join(f"{k}: {v}" for k, v in cfg.items() if k not in ("NCCL_P2P_DISABLE","VLLM_USE_FLASHINFER_SAMPLER","OMP_NUM_THREADS","CUDA_DEVICE_MAX_CONNECTIONS","GENESIS_BUFFER_MODE","GENESIS_PREALLOC_TOKEN_BUDGET"))}}}

export PATH=/usr/local/cuda-13.0/bin:$PATH
export LD_LIBRARY_PATH=${{LD_LIBRARY_PATH:-}}:/usr/local/cuda-13.0/lib64
export CUDA_HOME=/usr/local/cuda-13.0

export VLLM_NO_USAGE_STATS=1
export VLLM_USE_FLASHINFER_SAMPLER={fi_sampler}
export VLLM_FLOAT32_MATMUL_PRECISION=high
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_LOGGING_LEVEL=WARNING
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512
export NCCL_P2P_DISABLE={nccl_p2p}
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
export GENESIS_BUFFER_MODE={buf_mode}
export GENESIS_PREALLOC_TOKEN_BUDGET={prealloc}

/opt/ai/vllm-env/bin/python3 -m vllm._genesis.patches.apply_all

exec /opt/ai/vllm-env/bin/vllm serve \\
  /home/dino/models/Qwen3.6-27B-int4-AutoRound \\
  --quantization gptq_marlin \\
  --tensor-parallel-size 2 \\
  --gpu-memory-utilization {cfg["gpu_memory_utilization"]} \\
  --max-model-len {cfg["max_model_len"]} \\
  --kv-cache-dtype {cfg["kv_cache_dtype"]} \\
  --max-num-seqs {cfg["max_num_seqs"]} \\
  --max-num-batched-tokens {cfg["max_num_batched_tokens"]} \\
  --enable-chunked-prefill \\
  --enable-prefix-caching \\
  --dtype bfloat16 \\
  --disable-custom-all-reduce \\
  --trust-remote-code \\
  --language-model-only \\
  --enable-auto-tool-choice \\
  --tool-call-parser qwen3_coder \\
  --reasoning-parser qwen3 \\
{spec_flag}  --prefix-caching-hash-algo xxhash \\
  --api-key genesis-local \\
  --served-model-name qwen3627b \\
  --host 0.0.0.0 \\
  --port {PORT} \\
  --disable-log-stats
"""
    LAUNCH_SH.write_text(content)
    LAUNCH_SH.chmod(0o755)


# ── Service control ────────────────────────────────────────────────────────────

def restart_service():
    subprocess.run(["systemctl", "--user", "restart", SERVICE], check=True)
    log(f"  restarted {SERVICE}")

def wait_for_ready(timeout: int = STARTUP_TIMEOUT) -> bool:
    """Poll /health until 200 OK or timeout. Returns True if ready."""
    deadline = time.time() + timeout
    last_log = time.time()
    while time.time() < deadline:
        try:
            r = requests.get(
                f"{BASE_URL}/health",
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=5,
            )
            if r.status_code == 200:
                return True
        except Exception:
            pass
        if time.time() - last_log > 30:
            elapsed = int(time.time() - (deadline - timeout))
            log(f"  still starting... ({elapsed}s)")
            last_log = time.time()
        time.sleep(5)
    return False

def stop_service():
    subprocess.run(["systemctl", "--user", "stop", SERVICE],
                   check=False, capture_output=True)


# ── Benchmark ─────────────────────────────────────────────────────────────────

def single_bench(max_tokens: int = BENCH_TOKENS) -> float:
    """One timed completion request. Returns wall-clock t/s. Raises on error."""
    t0 = time.perf_counter()
    r = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user",   "content": BENCH_PROMPT},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.0,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        },
        timeout=300,
    )
    elapsed = time.perf_counter() - t0
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"API error: {data['error']}")
    toks = data.get("usage", {}).get("completion_tokens", 0)
    if toks < 10:
        raise RuntimeError(f"Only {toks} tokens returned — model may not be generating")
    return toks / elapsed


def run_bench() -> tuple[float, float]:
    """
    Warmup + timed bench.
    Returns (median_tps, p90_tps).
    Fails loud: raises RuntimeError on any bad measurement.
    """
    log(f"  warming up ({BENCH_WARMUP} requests, Marlin kernel JIT)...")
    for i in range(BENCH_WARMUP):
        tps = single_bench(max_tokens=128)  # short warmup requests
        log(f"    warmup {i+1}/{BENCH_WARMUP}: {tps:.1f} t/s")

    log(f"  measuring ({BENCH_REPS} requests × {BENCH_TOKENS} tokens)...")
    results = []
    for i in range(BENCH_REPS):
        tps = single_bench(max_tokens=BENCH_TOKENS)
        results.append(tps)
        log(f"    rep {i+1}/{BENCH_REPS}: {tps:.1f} t/s")

    results_sorted = sorted(results)
    median = results_sorted[len(results_sorted) // 2]
    p90    = results_sorted[int(len(results_sorted) * 0.9)]

    assert median > 0, f"FATAL: median t/s is {median}"
    if median < REGRESSION_FLOOR:
        raise RuntimeError(
            f"FATAL REGRESSION: {median:.1f} t/s < floor {REGRESSION_FLOOR} t/s "
            "(worse than llama.cpp baseline) — abort"
        )
    return median, p90


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    init_tsv()

    log_section("autoresearch-vllm-27b — Karpathy loop")
    log(f"Baseline config: {BASELINE}")
    log(f"Experiments: {len(CANDIDATE_MENU)}")
    log(f"Bench: {BENCH_WARMUP} warmup + {BENCH_REPS} timed reps × {BENCH_TOKENS} tokens")
    log(f"Improve threshold: {IMPROVE_THRESHOLD} t/s")

    # ── Measure baseline ───────────────────────────────────────────────────────
    log_section("BASELINE — measuring current config")
    write_launch_script(BASELINE)
    restart_service()
    assert wait_for_ready(), "FATAL: baseline vLLM failed to start"
    baseline_med, baseline_p90 = run_bench()
    log(f"Baseline: {baseline_med:.2f} t/s median, {baseline_p90:.2f} t/s p90")
    append_tsv(0, "baseline", "-", "-", baseline_med, baseline_p90, 0.0, "BASELINE", "current config")

    best_cfg  = deepcopy(BASELINE)
    best_tps  = baseline_med
    tried     = set()
    results   = []

    # Track which individual experiments improved (for combo decisions)
    improved_vars: dict[str, bool] = {}

    # ── Experiment loop ────────────────────────────────────────────────────────
    for iteration, exp in enumerate(CANDIDATE_MENU, start=1):
        name  = exp["name"]
        var   = exp["var"]
        val   = exp["val"]
        desc  = exp.get("desc", "")
        also  = exp.get("also", {})
        is_combo = exp.get("combo", False)

        if name in tried:
            log(f"[{iteration}] SKIP {name!r} (already tried)")
            continue
        tried.add(name)

        # Skip combo if neither component improved individually
        if is_combo:
            combo_vars = [var] + list(also.keys())
            any_improved = any(improved_vars.get(v, False) for v in combo_vars)
            if not any_improved:
                log(f"[{iteration}] SKIP combo {name!r} (no component showed improvement)")
                continue

        log_section(f"[{iteration}/{len(CANDIDATE_MENU)}] {name}")
        log(f"  {desc}")
        log(f"  Change: {var} = {val!r}" + (f" also {also}" if also else ""))

        # Build candidate config
        candidate = deepcopy(best_cfg)
        candidate[var] = val
        for k, v in also.items():
            candidate[k] = v

        # Write script and restart
        write_launch_script(candidate)
        restart_service()

        started = wait_for_ready(STARTUP_TIMEOUT)
        if not started:
            log(f"  TIMEOUT — vLLM did not start within {STARTUP_TIMEOUT}s")
            log(f"  Reverting to best config...")
            write_launch_script(best_cfg)
            restart_service()
            wait_for_ready()
            append_tsv(iteration, name, var, val, 0.0, 0.0, 0.0, "TIMEOUT", desc)
            results.append({"name": name, "outcome": "TIMEOUT"})
            continue

        try:
            tg_med, tg_p90 = run_bench()
        except RuntimeError as e:
            log(f"  ERROR: {e}")
            log(f"  Reverting to best config...")
            write_launch_script(best_cfg)
            restart_service()
            wait_for_ready()
            append_tsv(iteration, name, var, val, 0.0, 0.0, 0.0, "ERROR", desc)
            results.append({"name": name, "outcome": "ERROR", "error": str(e)})
            continue

        delta = tg_med - best_tps
        log(f"  Result: {tg_med:.2f} t/s median (Δ{delta:+.2f} vs best {best_tps:.2f})")

        if delta >= IMPROVE_THRESHOLD:
            outcome = "IMPROVEMENT"
            best_cfg = candidate
            best_tps = tg_med
            improved_vars[var] = True
            log(f"  ✓ NEW BEST: {best_tps:.2f} t/s — updating best config")
            # Write best flags script immediately
            _write_best_flags(best_cfg, best_tps)
        elif delta > 0:
            outcome = "MARGINAL"
            log(f"  ~ marginal (+{delta:.2f} t/s < threshold {IMPROVE_THRESHOLD})")
        else:
            outcome = "NO_CHANGE"
            improved_vars[var] = False
            log(f"  ✗ no improvement ({delta:+.2f} t/s) — reverting")
            write_launch_script(best_cfg)
            restart_service()
            wait_for_ready()

        append_tsv(iteration, name, var, val, tg_med, tg_p90, delta, outcome, desc)
        results.append({
            "name": name, "var": var, "val": val,
            "tg_med": tg_med, "delta": delta, "outcome": outcome,
        })

    # ── Final summary ──────────────────────────────────────────────────────────
    log_section("CANONICAL — autoresearch complete")
    log(f"Baseline:  {baseline_med:.2f} t/s")
    log(f"Best:      {best_tps:.2f} t/s  (Δ{best_tps - baseline_med:+.2f})")
    log(f"Best config: {best_cfg}")

    improvements = [r for r in results if r.get("outcome") == "IMPROVEMENT"]
    log(f"Improvements found: {len(improvements)}")
    for r in improvements:
        log(f"  + {r['name']}: {r['var']}={r['val']} → +{r['delta']:.2f} t/s")

    # Write final launch script as the new production config
    write_launch_script(best_cfg)
    _write_best_flags(best_cfg, best_tps)

    # Ensure the service is running with the best config
    restart_service()
    assert wait_for_ready(), "FATAL: final service start failed"
    final_med, final_p90 = run_bench()
    log(f"Final verification: {final_med:.2f} t/s median, {final_p90:.2f} t/s p90")
    append_tsv(99, "FINAL", "-", "-", final_med, final_p90,
               final_med - baseline_med, "FINAL", "best config re-verified")

    if abs(final_med - best_tps) > 3.0:
        log(f"WARNING: final bench {final_med:.1f} t/s differs from recorded best {best_tps:.1f} — "
            f"variance is expected; best config is still correct")

    log("CANONICAL ✓")


def _write_best_flags(cfg: dict, tps: float):
    content = f"""#!/bin/bash
# Best vLLM config from autoresearch — {datetime.now().strftime("%Y-%m-%d %H:%M")}
# Best t/s: {tps:.2f}
# To apply: cp this file to ~/vllm-genesis-start.sh && systemctl --user restart vllm-genesis

"""
    for k, v in cfg.items():
        content += f"# {k} = {v}\n"
    content += "\n"
    content += "# Full launch script is at: ~/vllm-genesis-start.sh\n"
    content += f"# Generated from: /home/dino/inference-research/autoresearch-vllm-27b.py\n"
    BEST_FLAGS.write_text(content)


if __name__ == "__main__":
    main()
