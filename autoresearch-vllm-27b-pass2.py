#!/usr/bin/env python3
"""
Karpathy-style autoresearch — Pass 2 — Qwen3.6-27B vLLM (port 8022).

Pass 1 canonical result: 80.58 t/s  (kv_cache_dtype=auto was the only improvement)
Pass 2 baseline: that canonical config (fp16 KV, all other pass-1 settings unchanged)

New experiments this pass:
  - VLLM_MARLIN_USE_ATOMIC_ADD=1  — atomic-add reduce in Marlin kernel for small-n decode
      (confirmed in vllm/model_executor/layers/quantization/utils/marlin_utils.py;
       SM12 Blackwell is exempt from the sm8x bfloat16 restriction → fully eligible)
  - VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE  — FlashInfer workspace (default 394 MB)
  - NCCL_BUFFSIZE tuning  — allreduce buffer size
  - OMP_NUM_THREADS=2  — bisect between pass-1 values (1=baseline, 4=marginal +0.94)
  - PYTORCH_CUDA_ALLOC_CONF max_split_size_mb tuning
  - Combos of pass-1 marginals: OMP=4+exclusive, OMP=4+exclusive+GMU 0.88

Architecture constraint (unchanged from pass 1):
  PIECEWISE CUDA graph mode only — GDN linear_attn + MTP proposer, not fixable.
"""

import csv
import json
import os
import subprocess
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import requests

# ── Config ─────────────────────────────────────────────────────────────────────

# Pass-1 canonical best config
BASELINE = {
    "gpu_memory_utilization":          0.82,
    "max_model_len":                   32768,
    "max_num_seqs":                    2,
    "max_num_batched_tokens":          4096,
    "kv_cache_dtype":                  "auto",   # fp16 — pass-1 improvement
    "mtp_n":                           3,
    # env vars
    "NCCL_P2P_DISABLE":                "1",
    "VLLM_USE_FLASHINFER_SAMPLER":     "1",
    "OMP_NUM_THREADS":                 "1",
    "CUDA_DEVICE_MAX_CONNECTIONS":     "8",
    "GENESIS_BUFFER_MODE":             "shared",
    "GENESIS_PREALLOC_TOKEN_BUDGET":   "4096",
    # new in pass 2 — baseline values (off/default)
    "VLLM_MARLIN_USE_ATOMIC_ADD":      "0",
    "VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE": str(394 * 1024 * 1024),  # 413 MB default
    "NCCL_BUFFSIZE":                   "4194304",   # 4 MB NCCL default
    "PYTORCH_MAX_SPLIT_MB":            "512",        # used in PYTORCH_CUDA_ALLOC_CONF
}

SERVICE          = "vllm-genesis"
PORT             = 8022
API_KEY          = "genesis-local"
MODEL            = "qwen3627b"
BASE_URL         = f"http://localhost:{PORT}"
STARTUP_TIMEOUT  = 480
BENCH_WARMUP     = 4
BENCH_REPS       = 5
BENCH_TOKENS     = 512
IMPROVE_THRESHOLD = 1.5
REGRESSION_FLOOR  = 20.0

LOG_FILE    = Path("/home/dino/inference-research/autoresearch-vllm-27b-pass2-log.md")
RESULTS_TSV = Path("/home/dino/inference-research/autoresearch-vllm-27b-pass2-results.tsv")
BEST_FLAGS  = Path("/home/dino/inference-research/current-best-flags-vllm-27b.sh")
LAUNCH_SH   = Path("/home/dino/vllm-genesis-start.sh")

BENCH_PROMPT = (
    "Write a comprehensive technical deep-dive on transformer attention mechanisms, "
    "covering scaled dot-product attention, multi-head attention, positional encodings, "
    "and how attention patterns emerge during training. Include pseudocode and complexity analysis."
)


# ── Candidate menu ─────────────────────────────────────────────────────────────

CANDIDATE_MENU = [
    # ── Marlin atomic-add reduce ───────────────────────────────────────────────
    # Confirmed in vllm/model_executor/layers/quantization/utils/marlin_utils.py:
    # Active when n < 2048 AND k >= 2048. TP=2 splits hidden dims → many layers
    # land under n=2048 per GPU. SM12 (Blackwell) passes the sm8x bfloat16 check.
    # This is the highest-confidence new candidate.
    {"name": "Marlin atomic-add",
     "var":  "VLLM_MARLIN_USE_ATOMIC_ADD", "val": "1",
     "desc": "atomic-add reduce in gptq_marlin kernel for small-n decode layers (TP=2 eligible)"},

    # ── FlashInfer workspace size ──────────────────────────────────────────────
    # Default 394 MB. If workspace overflows it reallocates mid-request.
    # 1 GB gives plenty of headroom; 16 GB per GPU makes this cheap.
    {"name": "FlashInfer workspace 1GB",
     "var":  "VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE", "val": str(1024 * 1024 * 1024),
     "desc": "FlashInfer workspace 1 GB (default 394 MB) — prevents mid-request realloc"},
    {"name": "FlashInfer workspace 768MB",
     "var":  "VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE", "val": str(768 * 1024 * 1024),
     "desc": "FlashInfer workspace 768 MB — bisect between default and 1 GB"},

    # ── OMP threads bisect ─────────────────────────────────────────────────────
    # Pass 1: OMP=1 (baseline), OMP=4 (+0.94 t/s MARGINAL). Test OMP=2 midpoint.
    {"name": "OMP threads 2",
     "var":  "OMP_NUM_THREADS", "val": "2",
     "desc": "OMP=2 threads — bisect between pass-1 baseline (1) and marginal (4)"},

    # ── NCCL buffer size ───────────────────────────────────────────────────────
    # Larger allreduce buffer reduces fragmentation for TP=2 all-reduce on PCIe.
    # Default 4 MB; 8 MB doubles it.
    {"name": "NCCL buffer 8MB",
     "var":  "NCCL_BUFFSIZE", "val": "8388608",
     "desc": "NCCL allreduce buffer 8 MB (default 4 MB) — reduces fragmentation on TP=2 PCIe"},
    {"name": "NCCL buffer 16MB",
     "var":  "NCCL_BUFFSIZE", "val": "16777216",
     "desc": "NCCL allreduce buffer 16 MB — test if larger buffer helps further"},

    # ── CUDA allocator max_split_size_mb ──────────────────────────────────────
    # Tighter pools reduce fragmentation over long decode runs.
    # Current: 512 MB. Test 64 MB (aggressive) and 128 MB.
    {"name": "max_split_mb 64",
     "var":  "PYTORCH_MAX_SPLIT_MB", "val": "64",
     "desc": "PYTORCH_CUDA_ALLOC_CONF max_split_size_mb=64 — tighter allocator pools"},
    {"name": "max_split_mb 128",
     "var":  "PYTORCH_MAX_SPLIT_MB", "val": "128",
     "desc": "PYTORCH_CUDA_ALLOC_CONF max_split_size_mb=128 — moderate pool tightening"},

    # ── Pass-1 marginal combos ─────────────────────────────────────────────────
    # OMP=4 (+0.94) and exclusive buffer (+1.05) were each MARGINAL in pass 1.
    # Together they may clear the 1.5 t/s threshold.
    {"name": "OMP4 + exclusive buffer",
     "var":  "OMP_NUM_THREADS", "val": "4",
     "also": {"GENESIS_BUFFER_MODE": "exclusive"},
     "desc": "stack pass-1 marginals: OMP=4 (+0.94) + exclusive buffer (+1.05)"},

    # Add GMU 0.88 to the OMP+exclusive combo
    {"name": "OMP4 + exclusive + GMU 0.88",
     "var":  "OMP_NUM_THREADS", "val": "4",
     "also": {"GENESIS_BUFFER_MODE": "exclusive", "gpu_memory_utilization": 0.88},
     "desc": "triple marginal stack: OMP=4 + exclusive + GMU 0.88 (+0.94+1.05+0.45)"},

    # ctx 16K + GMU 0.88 — both were marginal in pass 1, test stacked
    {"name": "ctx 16K + GMU 0.88",
     "var":  "max_model_len", "val": 16384,
     "also": {"gpu_memory_utilization": 0.88},
     "desc": "stack ctx 16K (+0.40) + GMU 0.88 (+0.45) — smaller graphs + more KV blocks"},

    # ── Marlin atomic-add + best marginal combo ────────────────────────────────
    # If Marlin atomic-add improves, stack it with the OMP+exclusive combo.
    # Run unconditionally — worst case it just shows the stack doesn't help.
    {"name": "Marlin atomic + OMP4 + exclusive",
     "var":  "VLLM_MARLIN_USE_ATOMIC_ADD", "val": "1",
     "also": {"OMP_NUM_THREADS": "4", "GENESIS_BUFFER_MODE": "exclusive"},
     "desc": "Marlin atomic-add + OMP=4 + exclusive buffer — three-way stack"},
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
    spec_config = (
        f'{{"method":"mtp","num_speculative_tokens":{cfg["mtp_n"]}}}'
        if cfg["mtp_n"] > 0 else ""
    )
    spec_flag = (
        f'  --speculative-config \'{spec_config}\' \\\n'
        if cfg["mtp_n"] > 0 else ""
    )

    nccl_p2p    = cfg.get("NCCL_P2P_DISABLE", "1")
    fi_sampler  = cfg.get("VLLM_USE_FLASHINFER_SAMPLER", "1")
    omp         = cfg.get("OMP_NUM_THREADS", "1")
    cuda_conn   = cfg.get("CUDA_DEVICE_MAX_CONNECTIONS", "8")
    buf_mode    = cfg.get("GENESIS_BUFFER_MODE", "shared")
    nccl_buf    = cfg.get("NCCL_BUFFSIZE", "4194304")
    marlin_aa   = cfg.get("VLLM_MARLIN_USE_ATOMIC_ADD", "0")
    fi_ws       = cfg.get("VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE", str(394 * 1024 * 1024))
    max_split   = cfg.get("PYTORCH_MAX_SPLIT_MB", "512")
    # P28 buffer must be >= max_num_batched_tokens to avoid FlashInfer autotune overflow
    prealloc    = str(max(int(cfg.get("GENESIS_PREALLOC_TOKEN_BUDGET", "4096")),
                          cfg["max_num_batched_tokens"]))

    content = f"""#!/bin/bash
# Qwen3.6-27B AutoRound INT4 — vLLM + Genesis v7.53 — dual RTX 5060 Ti (32GB)
# Generated by autoresearch-vllm-27b-pass2.py — {datetime.now().strftime("%Y-%m-%d %H:%M")}
# Config: {{{", ".join(f"{k}: {v}" for k, v in cfg.items() if k not in (
    "NCCL_P2P_DISABLE","VLLM_USE_FLASHINFER_SAMPLER","OMP_NUM_THREADS",
    "CUDA_DEVICE_MAX_CONNECTIONS","GENESIS_BUFFER_MODE","GENESIS_PREALLOC_TOKEN_BUDGET",
    "VLLM_MARLIN_USE_ATOMIC_ADD","VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE",
    "NCCL_BUFFSIZE","PYTORCH_MAX_SPLIT_MB"))}}}

export PATH=/usr/local/cuda-13.0/bin:$PATH
export LD_LIBRARY_PATH=${{LD_LIBRARY_PATH:-}}:/usr/local/cuda-13.0/lib64
export CUDA_HOME=/usr/local/cuda-13.0

export VLLM_NO_USAGE_STATS=1
export VLLM_USE_FLASHINFER_SAMPLER={fi_sampler}
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


# ── Benchmark ─────────────────────────────────────────────────────────────────

def single_bench(max_tokens: int = BENCH_TOKENS) -> float:
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
        raise RuntimeError(f"Only {toks} tokens returned")
    return toks / elapsed

def run_bench() -> tuple[float, float]:
    log(f"  warming up ({BENCH_WARMUP} requests, Marlin kernel JIT)...")
    for i in range(BENCH_WARMUP):
        tps = single_bench(max_tokens=128)
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

    assert median > 0
    if median < REGRESSION_FLOOR:
        raise RuntimeError(
            f"FATAL REGRESSION: {median:.1f} t/s < floor {REGRESSION_FLOOR} t/s"
        )
    return median, p90


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Fresh log for pass 2
    LOG_FILE.write_text("")
    init_tsv()

    log_section("autoresearch-vllm-27b pass2 — Karpathy loop")
    log(f"Pass-1 canonical baseline: {BASELINE}")
    log(f"Experiments: {len(CANDIDATE_MENU)}")
    log(f"Bench: {BENCH_WARMUP} warmup + {BENCH_REPS} timed reps × {BENCH_TOKENS} tokens")
    log(f"Improve threshold: {IMPROVE_THRESHOLD} t/s")

    # ── Measure baseline ───────────────────────────────────────────────────────
    log_section("BASELINE — pass-1 canonical config")
    write_launch_script(BASELINE)
    restart_service()
    assert wait_for_ready(), "FATAL: baseline vLLM failed to start"
    baseline_med, baseline_p90 = run_bench()
    log(f"Baseline: {baseline_med:.2f} t/s median, {baseline_p90:.2f} t/s p90")
    append_tsv(0, "baseline", "-", "-", baseline_med, baseline_p90, 0.0, "BASELINE",
               "pass-1 canonical (fp16 KV)")

    best_cfg = deepcopy(BASELINE)
    best_tps = baseline_med
    tried    = set()
    results  = []
    improved_vars: dict[str, bool] = {}

    # ── Experiment loop ────────────────────────────────────────────────────────
    for iteration, exp in enumerate(CANDIDATE_MENU, start=1):
        name     = exp["name"]
        var      = exp["var"]
        val      = exp["val"]
        desc     = exp.get("desc", "")
        also     = exp.get("also", {})

        if name in tried:
            continue
        tried.add(name)

        log_section(f"[{iteration}/{len(CANDIDATE_MENU)}] {name}")
        log(f"  {desc}")
        log(f"  Change: {var} = {val!r}" + (f" also {also}" if also else ""))

        candidate = deepcopy(best_cfg)
        candidate[var] = val
        for k, v in also.items():
            candidate[k] = v

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
            _write_best_flags(best_cfg, best_tps)
        elif delta > 0:
            outcome = "MARGINAL"
            improved_vars[var] = False
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
    log_section("CANONICAL — pass 2 complete")
    log(f"Pass-1 baseline: {baseline_med:.2f} t/s")
    log(f"Best:            {best_tps:.2f} t/s  (Δ{best_tps - baseline_med:+.2f})")
    log(f"Best config: {best_cfg}")

    improvements = [r for r in results if r.get("outcome") == "IMPROVEMENT"]
    log(f"Improvements found: {len(improvements)}")
    for r in improvements:
        log(f"  + {r['name']}: {r['var']}={r['val']} → +{r['delta']:.2f} t/s")

    write_launch_script(best_cfg)
    _write_best_flags(best_cfg, best_tps)

    restart_service()
    assert wait_for_ready(), "FATAL: final service start failed"
    final_med, final_p90 = run_bench()
    log(f"Final verification: {final_med:.2f} t/s median, {final_p90:.2f} t/s p90")
    append_tsv(99, "FINAL", "-", "-", final_med, final_p90,
               final_med - baseline_med, "FINAL", "best config re-verified")

    if abs(final_med - best_tps) > 3.0:
        log(f"WARNING: final bench {final_med:.1f} differs from recorded best {best_tps:.1f}")

    log("CANONICAL ✓")


def _write_best_flags(cfg: dict, tps: float):
    lines = [
        f"#!/bin/bash",
        f"# Best vLLM config — pass 2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"# Best t/s: {tps:.2f}",
        "",
    ]
    for k, v in cfg.items():
        lines.append(f"# {k} = {v}")
    lines += ["", "# Full launch script: ~/vllm-genesis-start.sh",
              f"# Source: autoresearch-vllm-27b-pass2.py"]
    BEST_FLAGS.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
