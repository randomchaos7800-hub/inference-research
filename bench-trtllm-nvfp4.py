#!/usr/bin/env python3
"""
bench-trtllm-nvfp4.py — TRT-LLM NVFP4 benchmark via trtllm-serve
Model: Nemotron 3 Nano 30B A3B NVFP4
Hardware: dual RTX 5060 Ti 16GB, CUDA 13.0
Baseline: llama.cpp Q4_K_M = 123.6 t/s

Uses trtllm-serve --backend _autodeploy with official nano_v3 sharding
(ep/bmm, not standard TP) — required for Mamba hybrid architecture.
"""

import json, os, statistics, subprocess, time, urllib.request
from datetime import datetime

LOG    = "/home/dino/inference-research/bench-trtllm-nvfp4.log"
MODEL  = "/home/dino/models/Nemotron-3-Nano-30B-A3B-NVFP4"
PORT   = 8033
URL    = f"http://localhost:{PORT}/v1/chat/completions"
HEALTH = f"http://localhost:{PORT}/health"

BASELINE_TPS = 123.6
N_WARMUP = 2
N_BENCH  = 6
MAX_TOKENS = 400

NANO_V3_YAML = """\
runtime: trtllm
compile_backend: torch-simple
max_batch_size: 1
max_seq_len: 2048
enable_chunked_prefill: false
attn_backend: trtllm
model_factory: AutoModelForCausalLM
skip_loading_weights: false
kv_cache_config:
  free_gpu_memory_fraction: 0.05
  enable_block_reuse: false
transforms:
  detect_sharding:
    allreduce_strategy: SYMM_MEM
    sharding_dims: ['ep', 'bmm']
    sharding_source: ['manual']
    manual_config:
      head_dim: 128
      tp_plan:
        "in_proj": "mamba"
        "out_proj": "rowwise"
        "q_proj": "colwise"
        "k_proj": "colwise"
        "v_proj": "colwise"
        "o_proj": "rowwise"
        "up_proj": "colwise"
        "down_proj": "rowwise"
        "fc1_latent_proj": "gather"
        "fc2_latent_proj": "gather"
  multi_stream_moe:
    stage: compile
    enabled: true
  gather_logits_before_lm_head:
    enabled: true
  fuse_mamba_a_log:
    stage: post_load_fusion
    enabled: true
  insert_cached_ssm_attention:
    backend: flashinfer_ssm
  compile_model:
    piecewise_enabled: true
"""

PROMPTS = [
    "Explain in technical detail how CUDA tensor cores accelerate matrix multiplication on Blackwell GPU architecture.",
    "Describe the engineering challenges of running large language model inference at scale.",
    "Explain how retrieval augmented generation works end to end.",
    "Describe how speculative decoding accelerates autoregressive inference.",
    "Explain CUDA memory management for deep learning workloads.",
    "Describe prefix caching in LLM inference servers.",
    "Explain the Mamba state space model architecture.",
    "Describe multi-GPU tensor parallelism for LLM inference.",
]

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def kill_server():
    subprocess.run(["pkill", "-9", "-f", "trtllm-serve"], capture_output=True)
    subprocess.run(["pkill", "-9", "-f", f"port.*{PORT}"], capture_output=True)
    time.sleep(3)

def wait_ready(timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH, timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(5)
    return False

def bench_one(prompt):
    payload = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(URL, data=payload,
                                  headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read())
        elapsed = time.time() - t0
        usage = resp.get("usage", {})
        tokens = usage.get("completion_tokens", 0)
        return tokens / elapsed if elapsed > 0 and tokens > 0 else None
    except Exception as e:
        log(f"    request error: {e}")
        return None

def main():
    open(LOG, "w").close()
    log(f"bench-trtllm-nvfp4 start — {datetime.now().isoformat()}")
    log(f"model: {MODEL}")
    log(f"backend: _autodeploy, ep/bmm sharding, max_seq_len=4096")

    yaml_path = "/tmp/nano_v3_bench.yaml"
    with open(yaml_path, "w") as f:
        f.write(NANO_V3_YAML)

    kill_server()

    env = os.environ.copy()
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    cmd = [
        "/opt/ai/trtllm-env/bin/trtllm-serve", "serve",
        MODEL,
        "--backend", "_autodeploy",
        "--trust_remote_code",
        "--host", "0.0.0.0",
        "--port", str(PORT),
        "--config", yaml_path,
    ]
    log(f"Starting trtllm-serve (first run compiles CUDA graphs ~5-10 min)...")
    srv_log = open("/tmp/trtllm-serve-nvfp4.log", "w")
    proc = subprocess.Popen(cmd, env=env, stdout=srv_log, stderr=srv_log)

    log("Waiting for server ready...")
    if not wait_ready(timeout=900):
        log("FAIL: server did not come up in 15 min")
        try:
            with open("/tmp/trtllm-serve-nvfp4.log") as f:
                for line in f.readlines()[-10:]:
                    log(f"  SRV: {line.rstrip()}")
        except Exception:
            pass
        proc.terminate()
        srv_log.close()
        return

    log("Server ready.")

    vram = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True).stdout.strip()
    log(f"VRAM after load: {vram}")

    log(f"Warmup ({N_WARMUP})...")
    for i in range(N_WARMUP):
        tps = bench_one(PROMPTS[i % len(PROMPTS)])
        log(f"  warmup {i+1}: {tps:.1f} t/s" if tps else f"  warmup {i+1}: FAIL")

    log(f"Bench ({N_BENCH})...")
    readings = []
    for i in range(N_BENCH):
        tps = bench_one(PROMPTS[i % len(PROMPTS)])
        if tps:
            readings.append(tps)
            log(f"  run {i+1}: {tps:.1f} t/s")
        else:
            log(f"  run {i+1}: FAIL")

    proc.terminate()
    srv_log.close()

    if not readings:
        log("ALL RUNS FAILED")
        return

    med    = statistics.median(readings)
    stddev = statistics.stdev(readings) if len(readings) > 1 else 0.0
    delta  = med - BASELINE_TPS
    sign   = "+" if delta >= 0 else ""

    log(f"\n{'='*50}")
    log(f"RESULT: median={med:.1f} t/s  stddev={stddev:.2f}  n={len(readings)}")
    log(f"vs llama.cpp Q4_K_M: {sign}{delta:.1f} t/s ({sign}{delta/BASELINE_TPS*100:.1f}%)")
    log(f"VERDICT: {'WIN' if delta > 5 else 'MARGINAL' if delta > -5 else 'SLOWER'}")
    log(f"{'='*50}")
    log(f"\nbench-trtllm-nvfp4 complete")

if __name__ == "__main__":
    main()
