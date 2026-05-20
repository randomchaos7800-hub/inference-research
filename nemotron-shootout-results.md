# Nemotron 3 Nano 30B — Shootout Results

**Date:** 2026-05-20
**Status:** Q4_K_M CONFIRMED WORKING — cuda128-clean build

## Working Configuration

Binary: /home/dino/llama.cpp/build-cuda128-clean/bin/llama-server
Model:  Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf (23 GB)
Flags:  --n-gpu-layers 999 --ctx-size 32768 --threads 8 --cache-ram 0
Port:   8022
GPU split: GPU0: 11819 MiB / GPU1: 13097 MiB (24.9 GB total)

## Benchmark — via proxy :8010 (12 runs, 200 tokens each, 2026-05-20)

Smoke tests: 4/4 PASS (completions, chat/v1, short, long prompt)

run  1: 117.27 t/s
run  2: 117.31 t/s
run  3:  13.55 t/s  <- SWA cache rebuild outlier (transient, not repeated)
run  4: 117.45 t/s
run  5: 117.25 t/s
run  6: 117.26 t/s
run  7: 117.38 t/s
run  8: 117.24 t/s
run  9: 117.46 t/s
run 10: 117.60 t/s
run 11: 117.53 t/s
run 12: 117.37 t/s

median  117.34 t/s | peak 117.60 | min 13.55 (outlier)
Steady state (excl. outlier): ~117.3 t/s
Prefill: 1200-2500 t/s depending on prompt length
Note: run 3 outlier caused by SWA hybrid memory forcing full prompt reprocess - transient

## Failure Modes

### 1. build-cuda13 crashes with MMQ CUDA error
Symptom: Server starts, serves 1-3 tokens, then dies:
  CUDA error: invalid argument in ggml_cuda_mul_mat_q at mmq.cu:183
Root cause: cuda13 MMQ kernel incompatible with RTX 5060 Ti (Blackwell/SM120)
Fix: ALWAYS use build-cuda128-clean. Never build-cuda13 on this GPU.

### 2. vllm FP8 - unrecognized flag --disable-log-requests
Symptom: vllm exits immediately with "unrecognized arguments: --disable-log-requests"
Root cause: Flag removed in newer vllm. nemotron-experiment.py used old API.
Fix: Remove --disable-log-requests from all vllm commands.

### 3. vllm FP8 TP=2 - needs 2 free GPUs
Symptom: RuntimeError: Engine core initialization failed
Root cause: --tensor-parallel-size 2 requires 2 GPUs both free simultaneously.
Fix: Kill the llama-server first to free both GPUs before launching vllm FP8.

### 4. nemotron-experiment.py - hardcoded wrong binary
Symptom: All experiment runs fail, no results file written
Root cause: Script uses build-cuda13 binary (the broken one)
Fix: Change LLAMA_BIN in nemotron-experiment.py to build-cuda128-clean/bin/llama-server

### 5. Proxy model name mismatch (cosmetic)
Symptom: config.toml says model=qwen3627b but port 8022 serves Nemotron
Root cause: Config not updated when Nemotron replaced Genesis on 8022
Fix: Update config.toml or leave it - proxy just forwards, name does not matter

## Start Command

/home/dino/llama.cpp/build-cuda128-clean/bin/llama-server \
  --model /home/dino/models/Nemotron-3-Nano-30B-A3B/nvidia_Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8022 \
  --n-gpu-layers 999 --ctx-size 32768 --threads 8 --cache-ram 0

Requires both GPUs (~24.9 GB VRAM). Kill any other model server first.
