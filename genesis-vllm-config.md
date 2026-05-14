# Genesis vLLM Config — Qwen3.6-27B INT4 on Dual RTX 5060 Ti (Blackwell)

**Hardware:** 2× RTX 5060 Ti 16GB GDDR7, Blackwell SM_120, Arrow Lake CPU  
**Stack:** vLLM 0.19.2rc1.dev228 (Genesis custom-patched build, P60–P82)  
**Model:** Qwen3.6-27B-int4-AutoRound (GPTQ-Marlin INT4)  
**Speed:** ~80 t/s sustained | TTFT ~100ms | 64K context  

---

## Why UV install will not work

This is not a standard vLLM install. Two reasons:

1. **Dev build required.** The stable vLLM release does not have Blackwell (SM_120) CUDA kernel paths for GPTQ-Marlin or flashinfer on this architecture. You need `0.19.x` nightly minimum.
2. **Genesis patches.** This build has custom patches (P60–P82) applied on top of vLLM for Blackwell-specific MTP speculative decoding, triton kernel fixes, and adaptive ngram. These are applied at startup via `vllm._genesis.patches.apply_all`. Without them, you get correct but slower inference.

If you just want a working baseline without genesis patches, the flags below will still work with a compatible vLLM nightly — you just lose ~5-10 t/s and some MTP stability.

---

## Environment Variables

```bash
export PATH=/usr/local/cuda-13.0/bin:$PATH
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}:/usr/local/cuda-13.0/lib64
export CUDA_HOME=/usr/local/cuda-13.0

export VLLM_NO_USAGE_STATS=1
export VLLM_USE_FLASHINFER_SAMPLER=1
export VLLM_FLOAT32_MATMUL_PRECISION=high
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_LOGGING_LEVEL=WARNING
export VLLM_MARLIN_USE_ATOMIC_ADD=1
export VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE=413138944
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512
export NCCL_P2P_DISABLE=1
export NCCL_BUFFSIZE=4194304
export OMP_NUM_THREADS=1
export CUDA_DEVICE_MAX_CONNECTIONS=8
```

**Key flags explained:**
- `NCCL_P2P_DISABLE=1` — required for dual-GPU without NVLink (PCIe-only, no direct peer transfer)
- `VLLM_MARLIN_USE_ATOMIC_ADD=1` — Blackwell GPTQ-Marlin kernel correctness fix
- `VLLM_WORKER_MULTIPROC_METHOD=spawn` — required for TP=2 stability on this CPU
- `VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE` — pre-allocated workspace; tuned for 2-sequence concurrent load

---

## vllm serve flags

```bash
vllm serve /path/to/Qwen3.6-27B-int4-AutoRound \
  --quantization gptq_marlin \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 65536 \
  --kv-cache-dtype auto \
  --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --enable-chunked-prefill \
  --enable-prefix-caching \
  --dtype bfloat16 \
  --disable-custom-all-reduce \
  --trust-remote-code \
  --language-model-only \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml \
  --reasoning-parser qwen3 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":3}' \
  --prefix-caching-hash-algo xxhash \
  --api-key your-key-here \
  --served-model-name qwen3627b \
  --host 0.0.0.0 \
  --port 8022 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --disable-log-stats
```

**Hard limits — do not change:**

| Flag | Value | Why |
|---|---|---|
| `--max-num-batched-tokens` | 4096 | Genesis MTP buffer hard ceiling — crashes at 8192 |
| `--max-num-seqs` | 2 | vLLM bug #35288 corrupts output at ≥4 concurrent seqs |
| `--gpu-memory-utilization` | 0.90 | Higher risks OOM during profile run at startup |
| `--speculative-config mtp n=3` | keep | n=4 OOMs on startup; removing costs ~50% throughput |

---

## Model

`Qwen3.6-27B-int4-AutoRound` — GPTQ-Marlin INT4 quantization via AutoRound.  
Pull from HuggingFace: look for AutoRound INT4 variants of Qwen3.6-27B.  
The model has native MTP heads which vLLM uses for speculative decoding — this is why `mtp` works here without a separate draft model.

---

## Thinking mode

This config disables Qwen3 thinking by default (`enable_thinking: false`). Thinking mode burns tokens fast and is not useful for agent workloads. Enable per-request if needed via the chat template kwargs.

---

## Benchmarks (2026-05-09, verified)

| Metric | Value |
|---|---|
| Sustained t/s (1000 tokens) | 80.4 t/s |
| TTFT (short prompt) | ~100ms |
| TTFT (8K prompt) | ~1400ms |
| Concurrent load (2 reqs) | 76.3 combined t/s |
| Prefix cache speedup | 3.84× |
| GPU temps under load | 66°C / 64°C |
| Thermal headroom | ~17°C |

Full benchmark writeup: `genesis-baseline-2026-05-09.md`

---

## What this does not cover

- How to install the Genesis-patched vLLM build (not public yet)
- The local-proxy layer that sits in front of this (port 8010, single swap point for all clients)
- AEON config (NVFP4 variant, ~69 t/s, different tradeoffs)

This is the start script and flags. The Genesis patch layer is the part that is not yet published.
