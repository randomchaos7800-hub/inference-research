#!/usr/bin/env python3
"""
AEON NVFP4 autoresearch — Qwen3.5-27B NVFP4 on dual RTX 5060 Ti.
Sweeps: mtp_n, max_num_batched_tokens, max_num_seqs, gmu, prealloc budget.
Baseline: current production config (122880 ctx, gmu=0.90, fp8 KV, mtp_n=3).
Writes best config back to vllm-aeon-nvfp4-start.sh at end.
"""
import datetime, os, statistics, subprocess, sys, time
import requests

LOG    = "/home/dino/inference-research/autoresearch-aeon-nvfp4-log.md"
TSV    = "/home/dino/inference-research/autoresearch-aeon-nvfp4-results.tsv"
SCRIPT = "/home/dino/vllm-aeon-nvfp4-start.sh"
BASE_URL = "http://localhost:8023"
API_KEY  = "genesis-local"
MODEL    = "aeon-nvfp4"
HEADERS  = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

BASELINE = {
    "gpu_memory_utilization":                0.90,
    "max_model_len":                         122880,
    "max_num_seqs":                          2,
    "max_num_batched_tokens":                4096,
    "kv_cache_dtype":                        "fp8",
    "mtp_n":                                 3,
    "NCCL_P2P_DISABLE":                      "1",
    "VLLM_USE_FLASHINFER_SAMPLER":           "1",
    "OMP_NUM_THREADS":                       "1",
    "CUDA_DEVICE_MAX_CONNECTIONS":           "8",
    "GENESIS_BUFFER_MODE":                   "shared",
    "GENESIS_PREALLOC_TOKEN_BUDGET":         "4096",
    "VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE": str(413 * 1024 * 1024),
    "NCCL_BUFFSIZE":                         "4194304",
    "PYTORCH_MAX_SPLIT_MB":                  "512",
    "VLLM_NVFP4_GEMM_BACKEND":              "flashinfer-cutlass",
}

EXPERIMENTS = [
    # MTP tokens — biggest lever for speculative decode speed
    ("mtp_n=1",   {"mtp_n": 1}),
    ("mtp_n=2",   {"mtp_n": 2}),
    ("mtp_n=4",   {"mtp_n": 4}),
    ("mtp_n=5",   {"mtp_n": 5}),

    # Batched tokens — spec decode can benefit from more headroom
    ("batched=8192",  {"max_num_batched_tokens": 8192}),
    ("batched=2048",  {"max_num_batched_tokens": 2048}),

    # Seqs — single slot reduces contention
    ("seqs=1",    {"max_num_seqs": 1}),

    # GMU — more VRAM for KV cache
    ("gmu=0.88",  {"gpu_memory_utilization": 0.88}),
    ("gmu=0.92",  {"gpu_memory_utilization": 0.92}),

    # Prealloc budget
    ("prealloc=8192",  {"GENESIS_PREALLOC_TOKEN_BUDGET": "8192"}),
    ("prealloc=2048",  {"GENESIS_PREALLOC_TOKEN_BUDGET": "2048"}),

    # Combos of best candidates (filled in after initial sweep if gains found)
    ("mtp_n=4+batched=8192", {"mtp_n": 4, "max_num_batched_tokens": 8192}),
    ("mtp_n=4+seqs=1",       {"mtp_n": 4, "max_num_seqs": 1}),
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
        "max_tokens":           max_tokens,
        "temperature":          0.0,
        "stream":               False,
        "chat_template_kwargs": {"enable_thinking": False},
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
    gmu      = cfg["gpu_memory_utilization"]
    ctx      = cfg["max_model_len"]
    seqs     = cfg["max_num_seqs"]
    batched  = cfg["max_num_batched_tokens"]
    kv_dtype = cfg["kv_cache_dtype"]
    mtp_n    = cfg["mtp_n"]
    prealloc = str(max(int(cfg.get("GENESIS_PREALLOC_TOKEN_BUDGET", "4096")), batched))
    fi_ws    = cfg.get("VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE", str(413 * 1024 * 1024))
    nccl_buf = cfg.get("NCCL_BUFFSIZE", "4194304")
    max_split= cfg.get("PYTORCH_MAX_SPLIT_MB", "512")
    nvfp4_be = cfg.get("VLLM_NVFP4_GEMM_BACKEND", "flashinfer-cutlass")
    now_str  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    content = f"""#!/bin/bash
# Qwen3.6-27B AEON NVFP4 MTP-XS — vLLM + Genesis — dual RTX 5060 Ti (32GB)
# NVFP4 quant (modelopt), 16 full-attn layers (4x smaller KV cache), vision tower, MTP grafted BF16
# Generated by autoresearch-aeon-nvfp4.py — {now_str}
# Config: {{gpu_memory_utilization: {gmu}, max_model_len: {ctx}, max_num_seqs: {seqs}, kv_cache_dtype: {kv_dtype}, mtp_n: {mtp_n}}}

export PATH=/usr/local/cuda-13.0/bin:$PATH
export LD_LIBRARY_PATH=${{LD_LIBRARY_PATH:-}}:/usr/local/cuda-13.0/lib64
export CUDA_HOME=/usr/local/cuda-13.0

export VLLM_NO_USAGE_STATS=1
export VLLM_USE_FLASHINFER_SAMPLER=1
export VLLM_FLOAT32_MATMUL_PRECISION=high
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_LOGGING_LEVEL=WARNING
export VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE={fi_ws}
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:{max_split}
export NCCL_P2P_DISABLE=1
export NCCL_BUFFSIZE={nccl_buf}
export OMP_NUM_THREADS=1
export CUDA_DEVICE_MAX_CONNECTIONS=8

# NVFP4-specific
export VLLM_NVFP4_GEMM_BACKEND={nvfp4_be}
export VLLM_USE_FLASHINFER_MOE_FP4=0

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
export GENESIS_BUFFER_MODE=shared
export GENESIS_PREALLOC_TOKEN_BUDGET={prealloc}

/opt/ai/vllm-env/bin/python3 -m vllm._genesis.patches.apply_all

exec /opt/ai/vllm-env/bin/vllm serve \\
  /home/dino/models/Qwen3.6-27B-AEON-NVFP4-MTP-XS \\
  --quantization modelopt \\
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
  --enable-auto-tool-choice \\
  --tool-call-parser qwen3_coder \\
  --reasoning-parser qwen3 \\
  --speculative-config '{{"method":"mtp","num_speculative_tokens":{mtp_n}}}' \\
  --prefix-caching-hash-algo xxhash \\
  --api-key genesis-local \\
  --served-model-name aeon-nvfp4 \\
  --host 0.0.0.0 \\
  --port 8023 \\
  --disable-log-stats
"""
    with open(SCRIPT, "w") as f:
        f.write(content)
    os.chmod(SCRIPT, 0o755)


def restart_service():
    subprocess.run(["systemctl", "--user", "restart", "vllm-aeon.service"], check=True)
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
    log(f"--- Exp {idx}: {name} ---")
    write_launch_script(cfg)
    restart_service()

    if not wait_healthy(180):
        log(f"  TIMEOUT — did not become healthy in 3 min")
        return 0.0, 0.0, "TIMEOUT"

    log("  healthy — warmup (4×128)")
    for _ in range(4):
        chat(TECH_PROMPT, max_tokens=128)

    log("  benchmarking (10×512)")
    median, p90 = bench(10, 512)
    if median == 0:
        log("  FAILED — no successful requests")
        return 0.0, 0.0, "FAILED"

    delta = median - baseline_median
    pct   = delta / baseline_median * 100
    log(f"  median={median:.2f} t/s  p90={p90:.2f}  delta={delta:+.2f} ({pct:+.1f}%)")

    if delta >= 1.0:
        outcome = "IMPROVEMENT"
    elif pct >= -3.0:
        outcome = "NEUTRAL"
    else:
        outcome = "REGRESSION"

    return median, p90, outcome


def write_tsv_row(f, idx, name, median, p90, delta, outcome):
    f.write(f"{idx}\t{name}\t{median:.2f}\t{p90:.2f}\t{delta:+.2f}\t{outcome}\n")
    f.flush()


def main():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG, "w") as f:
        f.write(f"# autoresearch-aeon-nvfp4  started {now_str}\n\n")
    with open(TSV, "w") as f:
        f.write("iter\tname\ttg_median\ttg_p90\tdelta\toutcome\n")

    log("=== AEON NVFP4 autoresearch ===")
    log(f"Baseline: ctx={BASELINE['max_model_len']} gmu={BASELINE['gpu_memory_utilization']} "
        f"fp8 KV mtp_n={BASELINE['mtp_n']}")
    log(f"Experiments: {len(EXPERIMENTS)}  (~{len(EXPERIMENTS)*5} min)")

    # Baseline
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
        write_tsv_row(f, 0, "baseline", baseline_median, baseline_p90, 0.0, "BASELINE")

    best_cfg  = dict(BASELINE)
    best_name = "baseline"
    best_med  = baseline_median

    for i, (name, overrides) in enumerate(EXPERIMENTS, 1):
        with open(LOG, "a") as f:
            f.write(f"\n## [{i}/{len(EXPERIMENTS)}] {name}\n")

        median, p90, outcome = run_experiment(i, name, overrides, baseline_median)
        delta = median - baseline_median

        with open(TSV, "a") as f:
            write_tsv_row(f, i, name, median, p90, delta, outcome)

        if outcome == "IMPROVEMENT" and median > best_med:
            best_cfg  = {**BASELINE, **overrides}
            best_name = name
            best_med  = median
            log(f"  → new best: {name}  {median:.2f} t/s")

    # Write best config back
    log(f"--- Writing best config: {best_name} ({best_med:.2f} t/s) ---")
    write_launch_script(best_cfg)
    restart_service()
    if wait_healthy(180):
        log("  Best config live and healthy")
    else:
        log("  WARNING: best config did not restart cleanly")

    gain = (best_med - baseline_median) / baseline_median * 100
    log(f"\n=== COMPLETE ===")
    log(f"  Baseline: {baseline_median:.2f} t/s")
    log(f"  Best:     {best_med:.2f} t/s  ({gain:+.1f}%)  [{best_name}]")
    log(f"  Config written to {SCRIPT}")

    with open(LOG, "a") as f:
        f.write(f"\n## COMPLETE — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Best: {best_name}  {best_med:.2f} t/s  ({gain:+.1f}%)\n")


if __name__ == "__main__":
    main()
