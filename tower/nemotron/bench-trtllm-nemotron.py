#!/usr/bin/env python3
"""
bench-trtllm-nemotron.py — TRT-LLM 1.2.1 benchmark vs llama.cpp baseline
Model: Nemotron 3 Nano 30B A3B FP8 (HuggingFace format)
Hardware: dual RTX 5060 Ti 16GB
Baseline: llama.cpp Q4_K_M = 123.6 t/s

Uses TRT-LLM LLM API (torch path / AutoDeploy) — no engine build required.
"""

import time, statistics
from datetime import datetime

LOG = "/home/dino/inference-research/bench-trtllm-nemotron.log"
BASELINE_TPS = 123.6

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

PROMPTS = [
    "Explain in technical detail how CUDA tensor cores accelerate matrix multiplication on Blackwell GPU architecture. Cover hardware pipeline, precision handling, and memory implications.",
    "Describe the engineering challenges of running large language model inference at scale, covering batching strategies, KV cache management, and quantization approaches.",
    "Explain how retrieval augmented generation works end to end, covering embedding models, vector databases, chunking strategies, and reranking.",
    "Describe how speculative decoding accelerates autoregressive inference, covering draft models, token verification, and multi-token prediction approaches.",
    "Explain CUDA memory management for deep learning: cudaMalloc, memory pools, VRAM fragmentation, and best practices for multi-GPU inference.",
    "Describe prefix caching in LLM inference servers: KV cache reuse, hash-based lookup, eviction policies, and throughput impact.",
    "Explain the Mamba state space model architecture, selective state spaces, input-dependent transitions, and how SSMs compare to attention.",
    "Describe multi-GPU tensor parallelism for LLM inference: weight sharding, all-reduce patterns, and latency-throughput tradeoffs.",
]

N_WARMUP = 3
N_BENCH  = 8
MAX_TOKENS = 400

def main():
    import os
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
    open(LOG, "w").close()
    log(f"bench-trtllm-nemotron start — {datetime.now().isoformat()}")
    log(f"TRT-LLM LLM API, FP8 model, tensor_parallel_size=2")

    log("Loading TRT-LLM...")
    from tensorrt_llm import LLM, SamplingParams

    log("Initializing LLM (first load will compile — may take a few minutes)...")
    t_load = time.time()
    try:
        llm = LLM(
            model="/home/dino/models/Nemotron-3-Nano-30B-A3B-FP8",
            tensor_parallel_size=2,
            trust_remote_code=True,
        )
    except Exception as e:
        log(f"FAIL: LLM init error: {e}")
        log("Trying tensor_parallel_size=1...")
        try:
            llm = LLM(
                model="/home/dino/models/Nemotron-3-Nano-30B-A3B-FP8",
                tensor_parallel_size=1,
                trust_remote_code=True,
            )
        except Exception as e2:
            log(f"FAIL: single GPU also failed: {e2}")
            return

    load_time = time.time() - t_load
    log(f"Model loaded in {load_time:.1f}s")

    sampling = SamplingParams(max_tokens=MAX_TOKENS, temperature=0.7)

    # warmup
    log(f"Warmup ({N_WARMUP} runs)...")
    for i in range(N_WARMUP):
        t0 = time.time()
        outputs = llm.generate([PROMPTS[i % len(PROMPTS)]], sampling_params=sampling)
        elapsed = time.time() - t0
        tokens = len(outputs[0].outputs[0].token_ids) if outputs[0].outputs else 0
        tps = tokens / elapsed if elapsed > 0 else 0
        log(f"  warmup {i+1}: {tps:.1f} t/s ({tokens} tokens, {elapsed:.2f}s)")

    # bench
    log(f"Bench ({N_BENCH} runs)...")
    readings = []
    for i in range(N_BENCH):
        t0 = time.time()
        outputs = llm.generate([PROMPTS[i % len(PROMPTS)]], sampling_params=sampling)
        elapsed = time.time() - t0
        tokens = len(outputs[0].outputs[0].token_ids) if outputs[0].outputs else 0
        tps = tokens / elapsed if elapsed > 0 else 0
        if tps > 0:
            readings.append(tps)
            log(f"  run {i+1}: {tps:.1f} t/s ({tokens} tokens)")
        else:
            log(f"  run {i+1}: FAIL")

    if not readings:
        log("ALL RUNS FAILED")
        return

    med    = statistics.median(readings)
    stddev = statistics.stdev(readings) if len(readings) > 1 else 0.0
    delta  = med - BASELINE_TPS
    sign   = "+" if delta >= 0 else ""

    log(f"\n{'='*50}")
    log(f"RESULT: median={med:.1f} t/s  stddev={stddev:.2f}  n={len(readings)}")
    log(f"vs llama.cpp baseline: {sign}{delta:.1f} t/s ({sign}{delta/BASELINE_TPS*100:.1f}%)")
    log(f"{'WIN' if delta > 5 else 'MARGINAL' if delta > 0 else 'SLOWER'}: TRT-LLM FP8 {'faster' if delta > 0 else 'slower'} than llama.cpp Q4_K_M")
    log(f"{'='*50}")
    log(f"\nbench-trtllm-nemotron complete")

if __name__ == "__main__":
    import os
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
    main()
