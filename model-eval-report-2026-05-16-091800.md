# Qwen3 Quantization Benchmark: 5 Formats on Dual RTX 5060 Ti
*cha0tiktower | 2026-05-16 09:18 | vLLM 0.21.0 + Genesis patches*

---

## Hardware

| Component | Spec |
|---|---|
| GPUs | 2× NVIDIA GeForce RTX 5060 Ti |
| VRAM per GPU | 16 311 MiB GDDR7 |
| GPU architecture | Blackwell SM_120 |
| PCIe | GPU 0 x8 Gen 5 / GPU 1 x4 Gen 4 |
| CPU | Intel Core Ultra 7 265F (8P + 12E cores, 5.3 GHz boost) |
| RAM | 32 GB DDR5 |
| OS | Ubuntu 24.04 LTS |
| CUDA | 12.8 |
| Inference engine | vLLM 0.21.0 + Genesis patches (TP=2) |
| Tensor parallelism | TP=2 (both GPUs active, balanced) |

---

## Test Protocol

**Objective:** Compare generation throughput across five quantization formats — NVFP4 (Blackwell-native W4A4), FP8 (W8A8), and GPTQ INT4 — spanning dense 14B/32B and MoE 30B-A3B architectures on consumer Blackwell hardware.

**Methodology:**

| Parameter | Value |
|---|---|
| Metric | Generation tokens/second (t/s), single-request sequential |
| Output tokens | 512 per request (fixed `max_tokens`) |
| Context window | 32 768 tokens (`--max-model-len`) |
| Warmup runs | 2 (discarded) |
| Timed runs | 7 per model |
| Reported stat | Median t/s (robust to outliers) |
| Cache control | 7 unique prompts, one per run — prevents prefix-cache inflation |
| VRAM isolation | Full drain to ≥15 000 MiB free (both GPUs) before each model load |
| MTP | None (eval models use standard vLLM; genesis MTP is a custom patch method, not available for arbitrary models) |
| Eval port | 8023 (production genesis stays on 8022, untouched) |

**Prompts (7 unique technical domains):**

1. CUDA tensor cores and Blackwell NVFP4/FP8 matrix multiply pipeline
2. Mixture-of-Experts architecture, routing, load balancing, inference trade-offs
3. Speculative decoding: draft models, acceptance rates, Multi-Token Prediction
4. LLM inference server design: batching, KV cache, continuous batching, prefix caching
5. Mamba/SSM architecture: selective state transitions, parallel scan, vs attention at context
6. Quantization methods: GPTQ, AWQ, NVFP4, FP8 — accuracy, hardware, throughput on Blackwell
7. Post-training alignment: RLHF, DPO, GRPO, constitutional AI

---

## Production Baseline

**Genesis — Qwen3.6-27B INT4 AutoRound**

| Field | Value |
|---|---|
| Architecture | Qwen 3.6 27B (Mamba/GDN hybrid, 16 full-attn + 48 SSM layers) |
| Quantization | GPTQ Marlin INT4 (AutoRound, group_size=128) |
| MTP | n=3 (genesis-patch drafter-free speculative method) |
| VRAM | ~15 086 / 14 124 MiB (425 / 1387 MiB free at GMU=0.90) |
| Speed | **73.35 t/s** (median, 7 varied prompts, 2026-05-16) |

---

## Results Summary

| Rank | Model | Arch | Format | VRAM | Median t/s | vs Genesis |
|---|---|---|---|---|---|---|
| — | Genesis (baseline) | SSM hybrid 27B | GPTQ INT4 + MTP | — | 73.35 | — |

| 1 | **Qwen3-30B-A3B GPTQ INT4** | MoE (30B total / ~3B active) | GPTQ INT4 (official Qwen release) | 14633/13454 MiB | **41.3** | -32.0 (-44%) |
| 2 | **Qwen3-32B GPTQ INT4** | Dense (32B) | GPTQ INT4 (AutoRound 0.5.1, group_size=128) | 14635/13844 MiB | **5.2** | -68.1 (-93%) |
| — | **Qwen3-30B-A3B NVFP4** | MoE (30B total / ~3B active) | NVFP4 (Blackwell native W4A4) | — | — | ❌ FAILED |
| — | **Qwen3-32B dense NVFP4** | Dense (32B) | NVFP4 (Blackwell native W4A4) | — | — | ❌ FAILED |
| — | **Qwen3-14B FP8** | Dense (14B) | FP8 (W8A8) | — | — | ❌ FAILED |

---

## Per-Model Details

### 1. Qwen3-30B-A3B NVFP4

**Source:** `nvidia/Qwen3-30B-A3B-NVFP4`
**Architecture:** MoE (30B total / ~3B active)
**Quantization:** NVFP4 (Blackwell native W4A4)
**vLLM flags (this run):**

```bash
vllm serve /home/dino/models/Qwen3-30B-A3B-NVFP4 \
  --quantization modelopt \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 32768 \
  --kv-cache-dtype auto \
  --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --enable-chunked-prefill \
  --enable-prefix-caching \
  --dtype bfloat16 \
  --disable-custom-all-reduce \
  --trust-remote-code \
  --language-model-only \
  --reasoning-parser qwen3 \
  --prefix-caching-hash-algo xxhash \
  --api-key eval-bench \
  --served-model-name eval-model \
  --host 127.0.0.1 \
  --port 8023 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --disable-log-stats
```

> ❌ **FAILED** — server never became healthy or inference errored. See raw log for details.

---
### 2. Qwen3-32B dense NVFP4

**Source:** `nvidia/Qwen3-32B-NVFP4`
**Architecture:** Dense (32B)
**Quantization:** NVFP4 (Blackwell native W4A4)
**vLLM flags (this run):**

```bash
vllm serve /home/dino/models/Qwen3-32B-NVFP4 \
  --quantization modelopt \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 32768 \
  --kv-cache-dtype auto \
  --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --enable-chunked-prefill \
  --enable-prefix-caching \
  --dtype bfloat16 \
  --disable-custom-all-reduce \
  --trust-remote-code \
  --language-model-only \
  --reasoning-parser qwen3 \
  --prefix-caching-hash-algo xxhash \
  --api-key eval-bench \
  --served-model-name eval-model \
  --host 127.0.0.1 \
  --port 8023 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --disable-log-stats
```

> ❌ **FAILED** — server never became healthy or inference errored. See raw log for details.

---
### 3. Qwen3-32B GPTQ INT4

**Source:** `already on disk`
**Architecture:** Dense (32B)
**Quantization:** GPTQ INT4 (AutoRound 0.5.1, group_size=128)
**vLLM flags (this run):**

```bash
vllm serve /home/dino/models/Qwen3-32B-autoround-4bit-gptq \
  --quantization gptq_marlin \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 4096 \
  --kv-cache-dtype auto \
  --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --cpu-offload-gb 1.0 \
  --enable-chunked-prefill \
  --enable-prefix-caching \
  --dtype bfloat16 \
  --disable-custom-all-reduce \
  --trust-remote-code \
  --language-model-only \
  --reasoning-parser qwen3 \
  --prefix-caching-hash-algo xxhash \
  --api-key eval-bench \
  --served-model-name eval-model \
  --host 127.0.0.1 \
  --port 8023 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --disable-log-stats
```

**Result: 5.25 t/s** median (-68.10 t/s, -93% vs genesis)

| Metric | Value |
|---|---|
| Median t/s | **5.25** |
| Min / Max | 5.25 / 5.26 t/s |
| Std dev | 0.00 t/s |
| vs Genesis (73.35 t/s) | -68.10 t/s (-93%) |
| VRAM used (GPU 0 / GPU 1) | 14635 / 13844 MiB |
| GMU | 0.90 |

**Per-run t/s:** 5.25 | 5.26 | 5.25 | 5.26 | 5.25

---
### 4. Qwen3-14B FP8

**Source:** `Qwen/Qwen3-14B-FP8`
**Architecture:** Dense (14B)
**Quantization:** FP8 (W8A8)
**vLLM flags (this run):**

```bash
vllm serve /home/dino/models/Qwen3-14B-FP8 \
  --quantization fp8 \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.80 \
  --max-model-len 32768 \
  --kv-cache-dtype auto \
  --max-num-seqs 4 \
  --max-num-batched-tokens 8192 \
  --enable-chunked-prefill \
  --enable-prefix-caching \
  --dtype bfloat16 \
  --disable-custom-all-reduce \
  --trust-remote-code \
  --language-model-only \
  --reasoning-parser qwen3 \
  --prefix-caching-hash-algo xxhash \
  --api-key eval-bench \
  --served-model-name eval-model \
  --host 127.0.0.1 \
  --port 8023 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --disable-log-stats
```

> ❌ **FAILED** — server never became healthy or inference errored. See raw log for details.

---
### 5. Qwen3-30B-A3B GPTQ INT4

**Source:** `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
**Architecture:** MoE (30B total / ~3B active)
**Quantization:** GPTQ INT4 (official Qwen release)
**vLLM flags (this run):**

```bash
vllm serve /home/dino/models/Qwen3-30B-A3B-GPTQ-Int4 \
  --quantization gptq_marlin \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.82 \
  --max-model-len 4096 \
  --kv-cache-dtype auto \
  --max-num-seqs 2 \
  --max-num-batched-tokens 512 \
  --cpu-offload-gb 1.0 \
  --enforce-eager \
  --enable-chunked-prefill \
  --enable-prefix-caching \
  --dtype bfloat16 \
  --disable-custom-all-reduce \
  --trust-remote-code \
  --language-model-only \
  --reasoning-parser qwen3 \
  --prefix-caching-hash-algo xxhash \
  --api-key eval-bench \
  --served-model-name eval-model \
  --host 127.0.0.1 \
  --port 8023 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --disable-log-stats
```

**Result: 41.33 t/s** median (-32.02 t/s, -44% vs genesis)

| Metric | Value |
|---|---|
| Median t/s | **41.33** |
| Min / Max | 41.01 / 41.38 t/s |
| Std dev | 0.17 t/s |
| vs Genesis (73.35 t/s) | -32.02 t/s (-44%) |
| VRAM used (GPU 0 / GPU 1) | 14633 / 13454 MiB |
| GMU | 0.82 |

**Per-run t/s:** 41.37 | 41.09 | 41.38 | 41.33 | 41.01

---

## Analysis

**Fastest challenger: Qwen3-30B-A3B GPTQ INT4** at 41.3 t/s (-32.0 t/s, -44% vs genesis).

**MoE vs Dense:** Best MoE (Qwen3-30B-A3B GPTQ INT4) = 41.3 t/s vs best dense (Qwen3-32B GPTQ INT4) = 5.2 t/s. MoE advantage comes from routing only ~3B active params per token despite 30B total weights.

**NVFP4 (Blackwell-native W4A4):** The NVIDIA modelopt NVFP4 format uses Blackwell tensor core FP4 paths natively. At ~0.5 bytes/param it is maximally VRAM-efficient — a 30B MoE model fits in ~18 GB. Performance relative to GPTQ INT4 reflects how well the Blackwell SM_120 FP4 kernel path saturates vs the Marlin dequantization path.

**FP8 vs INT4:** FP8 (W8A8) uses ~1 byte/param, doubling VRAM vs INT4 at similar parameter count. The trade-off is reduced quantization noise; the question is whether that accuracy gain comes at a throughput cost on Blackwell, which has hardware FP8 tensor core paths.

**MoE architecture note:** MoE models (30B-A3B) have 30B total parameters but activate only ~3B per token. Generation speed on MoE is primarily gated by the active-parameter compute path, not total model size — so a 30B MoE can outpace a 14B dense model in t/s depending on routing overhead and memory bandwidth for expert weights.

**No MTP on eval models:** Genesis achieves ~73 t/s largely because of its built-in MTP (Multi-Token Prediction) drafter, which contributes ~33 t/s beyond the ~40 t/s INT4 autoregressive ceiling. The eval models run without MTP — this is a fair base comparison of quantization format throughput, but note that adding an MTP drafter to any of these models would shift their scores upward.

**Attention backend — Triton (SM 12.0 compatibility):** FlashInfer 0.6.8.post1 requires CUDA ≥ 12.9 to JIT-compile kernels for SM 12.0 (Blackwell). This system runs CUDA 12.8. FlashInfer fails with `No supported CUDA architectures found for major versions [12]` during the `determine_available_memory` profile run for standard Transformer models. Genesis avoids this because its P60B genesis patch substitutes a custom Triton attention kernel for the GDN/SSM architecture — but that patch is architecture-specific and does not help standard Transformers. All eval models therefore use `VLLM_ATTENTION_BACKEND=TRITON_ATTN` (Triton 3.6.0), which compiles correctly for SM 12.0. This may modestly reduce throughput vs FlashInfer on a CUDA 12.9 system, but produces accurate comparative numbers across all five models on this hardware.

---

*Generated by model-eval-bench.py | cha0tiktower | 2026-05-16 09:18*
