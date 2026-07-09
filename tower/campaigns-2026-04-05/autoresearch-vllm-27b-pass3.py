#!/usr/bin/env python3
"""
Pass 3: Context ceiling sweep for Qwen3.6-27B on dual RTX 5060 Ti.
Grid: max_model_len × gpu_memory_utilization → find highest stable context.
Baseline: canonical pass2 config (32K, GMU 0.82, ~80.5 t/s).
Restores baseline at end — does NOT write high-ctx config to production.
"""
import datetime
import os
import statistics
import subprocess
import sys
import time

import requests

LOG    = "/home/dino/inference-research/autoresearch-vllm-27b-pass3-log.md"
TSV    = "/home/dino/inference-research/autoresearch-vllm-27b-pass3-results.tsv"
SCRIPT = "/home/dino/vllm-genesis-start.sh"
BASE_URL = "http://localhost:8022"
API_KEY  = "genesis-local"
MODEL    = "qwen3627b"
HEADERS  = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

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
    "VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE": str(394 * 1024 * 1024),
    "NCCL_BUFFSIZE":                         "4194304",
    "PYTORCH_MAX_SPLIT_MB":                  "512",
}

# Grid: sweep ctx at GMU 0.82 first, then push with higher GMU for OOM cases
EXPERIMENTS = [
    # GMU 0.82 — how far does the current allocation take us?
    ("40K/0.82",  {"max_model_len": 40960,  "gpu_memory_utilization": 0.82}),
    ("48K/0.82",  {"max_model_len": 49152,  "gpu_memory_utilization": 0.82}),
    ("64K/0.82",  {"max_model_len": 65536,  "gpu_memory_utilization": 0.82}),
    ("80K/0.82",  {"max_model_len": 81920,  "gpu_memory_utilization": 0.82}),
    ("96K/0.82",  {"max_model_len": 98304,  "gpu_memory_utilization": 0.82}),
    ("128K/0.82", {"max_model_len": 131072, "gpu_memory_utilization": 0.82}),
    # GMU 0.85 — +3% headroom for KV blocks
    ("40K/0.85",  {"max_model_len": 40960,  "gpu_memory_utilization": 0.85}),
    ("48K/0.85",  {"max_model_len": 49152,  "gpu_memory_utilization": 0.85}),
    ("64K/0.85",  {"max_model_len": 65536,  "gpu_memory_utilization": 0.85}),
    ("80K/0.85",  {"max_model_len": 81920,  "gpu_memory_utilization": 0.85}),
    ("96K/0.85",  {"max_model_len": 98304,  "gpu_memory_utilization": 0.85}),
    ("128K/0.85", {"max_model_len": 131072, "gpu_memory_utilization": 0.85}),
    # GMU 0.88 — push harder
    ("64K/0.88",  {"max_model_len": 65536,  "gpu_memory_utilization": 0.88}),
    ("80K/0.88",  {"max_model_len": 81920,  "gpu_memory_utilization": 0.88}),
    ("96K/0.88",  {"max_model_len": 98304,  "gpu_memory_utilization": 0.88}),
    ("128K/0.88", {"max_model_len": 131072, "gpu_memory_utilization": 0.88}),
    # GMU 0.90 — max safe push
    ("96K/0.90",  {"max_model_len": 98304,  "gpu_memory_utilization": 0.90}),
    ("128K/0.90", {"max_model_len": 131072, "gpu_memory_utilization": 0.90}),
]

TECH_PROMPT = (
    "Write a comprehensive technical deep-dive on transformer attention mechanisms, "
    "covering scaled dot-product attention, multi-head attention, positional encodings, "
    "and how attention patterns emerge during training. Include pseudocode and complexity analysis."
)


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def log(msg):
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def chat(prompt, max_tokens=512):
    t0 = time.perf_counter()
    r = requests.post(f"{BASE_URL}/v1/chat/completions", headers=HEADERS, json={
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens":             max_tokens,
        "temperature":            0.0,
        "stream":                 False,
        "chat_template_kwargs":   {"enable_thinking": False},
    }, timeout=300)
    elapsed = time.perf_counter() - t0
    data = r.json()
    if "error" in data:
        return 0.0, 0
    toks = data["usage"]["completion_tokens"]
    return (toks / elapsed if elapsed > 0 else 0.0), toks


def wait_healthy(timeout=180):
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


def write_launch_script(cfg):
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
    fi_ws     = cfg.get("VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE", str(394 * 1024 * 1024))
    nccl_buf  = cfg.get("NCCL_BUFFSIZE", "4194304")
    max_split = cfg.get("PYTORCH_MAX_SPLIT_MB", "512")
    now_str   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    content = f"""#!/bin/bash
# Qwen3.6-27B AutoRound INT4 — vLLM + Genesis v7.53 — dual RTX 5060 Ti (32GB)
# Generated by autoresearch-vllm-27b-pass3.py — {now_str}
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
    subprocess.run(["systemctl", "--user", "restart", "vllm-genesis"], check=True)
    time.sleep(10)


def bench(n=10, max_tokens=512):
    tps_list = []
    for _ in range(n):
        tps, _ = chat(TECH_PROMPT, max_tokens=max_tokens)
        if tps > 0:
            tps_list.append(tps)
    if not tps_list:
        return 0.0, 0.0
    med = statistics.median(tps_list)
    p90 = sorted(tps_list)[int(len(tps_list) * 0.9)] if len(tps_list) >= 10 else tps_list[-1]
    return med, p90


def run_experiment(idx, name, overrides, baseline_median):
    cfg = {**BASELINE, **overrides}
    ctx = cfg["max_model_len"]
    gmu = cfg["gpu_memory_utilization"]

    log(f"--- Exp {idx}: {name}  ctx={ctx}  gmu={gmu} ---")
    write_launch_script(cfg)
    restart_service()

    if not wait_healthy(180):
        log(f"  TIMEOUT — did not become healthy in 3 min")
        return 0.0, 0.0, "TIMEOUT"

    log("  healthy — Marlin warmup (4×128)")
    for _ in range(4):
        chat(TECH_PROMPT, max_tokens=128)

    log("  benchmarking (10×512)")
    median, p90 = bench(10, 512)
    if median == 0:
        log("  FAILED — no successful requests after warmup")
        return 0.0, 0.0, "TIMEOUT"

    delta = median - baseline_median
    pct   = delta / baseline_median * 100
    log(f"  median={median:.2f} t/s  p90={p90:.2f}  delta={delta:+.2f} ({pct:+.1f}%)")

    # Classify by throughput loss — for ctx sweep, tolerate up to 10% loss
    if delta >= 1.0:
        outcome = "IMPROVEMENT"
    elif pct >= -5.0:
        outcome = "MARGINAL"   # ≤5% loss — likely acceptable for higher ctx
    elif pct >= -10.0:
        outcome = "DEGRADED"   # 5–10% loss — costly but possible
    else:
        outcome = "NO_CHANGE"  # >10% loss — not worth it

    return median, p90, outcome


def write_tsv_row(f, idx, name, ctx, gmu, median, p90, delta, outcome, desc):
    f.write(f"{idx}\t{name}\t{ctx}\t{gmu:.2f}\t{median:.2f}\t{p90:.2f}\t{delta:+.2f}\t{outcome}\t{desc}\n")
    f.flush()


def main():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG, "w") as f:
        f.write(f"# autoresearch-vllm-27b-pass3  started {now_str}\n\n")
    with open(TSV, "w") as f:
        f.write("iter\tname\tmax_model_len\tgmu\ttg_median\ttg_p90\tdelta\toutcome\tdesc\n")

    log("=== Pass 3: Context ceiling sweep ===")
    log(f"Experiments: {len(EXPERIMENTS)}  (~{len(EXPERIMENTS)*5} min)")

    # ── Baseline ──────────────────────────────────────────────────────────────
    log("--- Baseline ---")
    write_launch_script(BASELINE)
    restart_service()
    if not wait_healthy(180):
        log("FATAL: baseline did not start")
        sys.exit(1)
    for _ in range(4):
        chat(TECH_PROMPT, max_tokens=128)
    baseline_median, baseline_p90 = bench(10, 512)
    log(f"  Baseline: {baseline_median:.2f} t/s  p90={baseline_p90:.2f}")

    with open(TSV, "a") as f:
        write_tsv_row(f, 0, "baseline", BASELINE["max_model_len"],
                      BASELINE["gpu_memory_utilization"],
                      baseline_median, baseline_p90, 0.0, "BASELINE", "canonical pass2 config")

    # Track best context with ≤5% throughput loss
    best = {"ctx": BASELINE["max_model_len"], "gmu": BASELINE["gpu_memory_utilization"],
            "median": baseline_median, "name": "baseline"}

    # ── Experiments ───────────────────────────────────────────────────────────
    for i, (name, overrides) in enumerate(EXPERIMENTS, 1):
        with open(LOG, "a") as f:
            f.write(f"\n## [{i}/{len(EXPERIMENTS)}] {name}\n")

        median, p90, outcome = run_experiment(i, name, overrides, baseline_median)
        delta = median - baseline_median
        cfg   = {**BASELINE, **overrides}
        ctx   = cfg["max_model_len"]
        gmu   = cfg["gpu_memory_utilization"]

        with open(TSV, "a") as f:
            write_tsv_row(f, i, name, ctx, gmu, median, p90, delta, outcome,
                          f"ctx={ctx} gmu={gmu}")

        if median > 0 and outcome in ("IMPROVEMENT", "MARGINAL") and ctx > best["ctx"]:
            best = {"ctx": ctx, "gmu": gmu, "median": median, "name": name}
            log(f"  → new best high-ctx: {name}  {ctx} tok  {median:.2f} t/s")

    # ── Restore production baseline ───────────────────────────────────────────
    log("--- Restoring canonical baseline config (32K/0.82) ---")
    write_launch_script(BASELINE)
    restart_service()
    if wait_healthy(180):
        log("  Production baseline restored and healthy")
    else:
        log("  WARNING: baseline did not restart cleanly — check service")

    # ── Summary ───────────────────────────────────────────────────────────────
    loss_pct = (best["median"] - baseline_median) / baseline_median * 100
    log(f"\n=== PASS 3 COMPLETE ===")
    log(f"  Baseline:      {baseline_median:.2f} t/s @ 32K ctx (GMU 0.82)")
    log(f"  Best high-ctx: {best['name']}  {best['ctx']} tok @ GMU {best['gmu']}  "
        f"{best['median']:.2f} t/s ({loss_pct:+.1f}%)")
    log(f"  Production restored to 32K — update manually if you want higher ctx")

    with open(LOG, "a") as f:
        f.write(f"\n## PASS 3 COMPLETE — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Best high-ctx (≤5% loss): {best}\n")


if __name__ == "__main__":
    main()
