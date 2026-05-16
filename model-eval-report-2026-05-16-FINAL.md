# Qwen3 Quantization Benchmark: 5 Formats on Dual RTX 5060 Ti
*cha0tiktower | 2026-05-16 | vLLM 0.21.0 + Genesis patches*

---

## Hardware

| Component | Spec |
|---|---|
| GPUs | 2× NVIDIA GeForce RTX 5060 Ti |
| VRAM per GPU | 16 311 MiB GDDR7 |
| GPU architecture | Blackwell SM_120 |
| PCIe | GPU 0 ×8 Gen 5 / GPU 1 ×4 Gen 4 |
| CPU | Intel Core Ultra 7 265F (8P + 12E cores, 5.3 GHz boost) |
| RAM | 32 GB DDR5 |
| OS | Ubuntu 24.04 LTS |
| CUDA | 12.8 |
| Inference engine | vLLM 0.21.0 + Genesis patches (TP=2) |

---

## Test Protocol

**Objective:** Compare generation throughput across five quantization formats — NVFP4 (Blackwell-native W4A4), FP8 (W8A8), and GPTQ INT4 — spanning dense 14B/32B and MoE 30B-A3B architectures on consumer Blackwell hardware.

| Parameter | Value |
|---|---|
| Metric | Generation tokens/second (t/s), single-request sequential |
| Output tokens | 512 per request (fixed `max_tokens`) |
| Warmup runs | 2 (discarded) |
| Timed runs | 5–7 per model |
| Reported stat | Median t/s |
| Cache control | 7 unique technical prompts, one per run — no prefix cache reuse |
| VRAM isolation | Full drain to ≥15 000 MiB free (both GPUs) before each model |
| Eval port | 8023 (production genesis on 8022, untouched throughout) |
| Attention backend | `TRITON_ATTN` (see Analysis — SM 12.0 / CUDA 12.8 constraint) |
| MTP | None (genesis MTP is a model-specific patch; not available for arbitrary models) |

---

## Production Baseline

**Genesis — Qwen3.6-27B INT4 AutoRound**

| Field | Value |
|---|---|
| Architecture | Qwen3.6 27B (Mamba/GDN SSM hybrid — 16 full-attn + 48 SSM layers) |
| Quantization | GPTQ Marlin INT4 (AutoRound, group_size=128) |
| MTP | n=3 speculative tokens (genesis-patch drafter-free method, +33 t/s) |
| VRAM | 425 / 1 387 MiB free at GMU=0.90 |
| Speed | **73.35 t/s** (median, 7 varied prompts, 2026-05-16) |

Note: genesis's MTP contributes ~33 t/s of its score. The bare autoregressive ceiling for this hardware with a 27B INT4 model is ~40 t/s. All eval models below run without MTP and should be compared against that ~40 t/s floor, not the MTP-boosted 73.35.

---

## Results Summary

| Rank | Model | Arch | Format | Disk | VRAM (GPU0/1) | Median t/s | vs Genesis |
|---|---|---|---|---|---|---|---|
| — | **Genesis** (baseline) | SSM hybrid 27B | GPTQ INT4 + MTP n=3 | 15.6 GB | ~15 086 / 14 124 MiB | **73.35** | — |
| 1 | **Qwen3-14B FP8** | Dense 14B | FP8 W8A8 | ~14 GB | 13 069 / 12 300 MiB | **43.54** | -29.8 (-41%) |
| 2 | **Qwen3-30B-A3B GPTQ INT4** | MoE 30B / ~3B active | GPTQ Marlin INT4 | 16 GB | 14 633 / 13 454 MiB | **41.33** | -32.0 (-44%) |
| 3 | **Qwen3-32B GPTQ INT4** ⚠️ | Dense 32B | GPTQ Marlin INT4 | 16 GB | 14 635 / 13 844 MiB | **5.25** | -68.1 (-93%) |
| — | **Qwen3-30B-A3B NVFP4** | MoE 30B / ~3B active | NVFP4 W4A4 | ~9 GB | — | — | ⛔ CUDA 12.8 |
| — | **Qwen3-32B NVFP4** | Dense 32B | NVFP4 W4A4 | ~16 GB | — | — | ⛔ CUDA 12.8 |

⚠️ Required `--cpu-offload-gb 1.0` to initialize (see Analysis). Throughput reflects PCIe offload overhead, not native GPU capability.

---

## Per-Model Details

---

### Qwen3-14B FP8 — 43.54 t/s ✅

**Source:** `Qwen/Qwen3-14B-FP8` | **Quantization:** FP8 W8A8 | **Disk:** ~14 GB

```bash
vllm serve /home/dino/models/Qwen3-14B-FP8 \
  --quantization fp8 --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.80 --max-model-len 32768 \
  --kv-cache-dtype auto --max-num-seqs 4 \
  --max-num-batched-tokens 8192 \
  --enable-chunked-prefill --enable-prefix-caching \
  --dtype bfloat16 --disable-custom-all-reduce \
  --trust-remote-code --language-model-only \
  --reasoning-parser qwen3
```

| Metric | Value |
|---|---|
| Median t/s | **43.54** |
| Min / Max | 42.73 / 43.69 t/s |
| Std dev | 0.41 t/s |
| vs Genesis | -29.81 t/s (-41%) |
| VRAM (GPU 0 / GPU 1) | 13 069 / 12 300 MiB |
| cpu-offload | None — loads natively |

**Per-run:** 43.54 | 42.73 | 43.69 | 43.65 | 43.15

**Notes:** Loads cleanly with no workarounds. FP8 at 14B is ~7 GB/GPU shard, well within the 15.47 GiB limit including all initialization overhead. Triton attention backend works transparently.

---

### Qwen3-30B-A3B GPTQ INT4 — 41.33 t/s ✅ ⚠️

**Source:** `Qwen/Qwen3-30B-A3B-GPTQ-Int4` | **Quantization:** GPTQ Marlin INT4 | **Disk:** 16 GB

```bash
vllm serve /home/dino/models/Qwen3-30B-A3B-GPTQ-Int4 \
  --quantization gptq_marlin --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.82 --max-model-len 4096 \
  --kv-cache-dtype auto --max-num-seqs 2 \
  --max-num-batched-tokens 512 \
  --cpu-offload-gb 1.0 --enforce-eager \
  --enable-chunked-prefill --enable-prefix-caching \
  --dtype bfloat16 --disable-custom-all-reduce \
  --trust-remote-code --language-model-only \
  --reasoning-parser qwen3
```

| Metric | Value |
|---|---|
| Median t/s | **41.33** |
| Min / Max | 41.01 / 41.38 t/s |
| Std dev | 0.17 t/s |
| vs Genesis | -32.02 t/s (-44%) |
| VRAM (GPU 0 / GPU 1) | 14 633 / 13 454 MiB |
| cpu-offload | 1.0 GB required to initialize |

**Per-run:** 41.37 | 41.09 | 41.38 | 41.33 | 41.01

**Notes:** MoE architecture is the key finding here. Despite requiring cpu-offload to initialize (same 16 GB disk size as the dense 32B), inference throughput is barely affected — 41.33 t/s vs the theoretical ~5 t/s penalty that devastates the dense model. The reason: MoE routing activates only ~3B params per token. The 1 GB offloaded to CPU covers a small subset of expert weights; the active computation path remains almost entirely on-GPU. This makes MoE a dramatically better choice than dense 32B for memory-constrained hardware.

---

### Qwen3-32B GPTQ INT4 — 5.25 t/s ⚠️ (cpu-offload bottlenecked)

**Source:** local disk | **Quantization:** GPTQ Marlin INT4 (AutoRound 0.5.1) | **Disk:** 16 GB

```bash
vllm serve /home/dino/models/Qwen3-32B-autoround-4bit-gptq \
  --quantization gptq_marlin --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.90 --max-model-len 4096 \
  --kv-cache-dtype auto --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --cpu-offload-gb 1.0 \
  --enable-chunked-prefill --enable-prefix-caching \
  --dtype bfloat16 --disable-custom-all-reduce \
  --trust-remote-code --language-model-only \
  --reasoning-parser qwen3
```

| Metric | Value |
|---|---|
| Median t/s | **5.25** |
| Min / Max | 5.25 / 5.26 t/s |
| Std dev | 0.00 t/s |
| vs Genesis | -68.10 t/s (-93%) |
| VRAM (GPU 0 / GPU 1) | 14 635 / 13 844 MiB |
| cpu-offload | 1.0 GB required to initialize |

**Per-run:** 5.25 | 5.26 | 5.25 | 5.26 | 5.25

**Notes:** The 5.25 t/s is not a measure of model capability — it is a PCIe bandwidth ceiling. With dense 32B, every generated token requires accessing all 32B model weights sequentially. The 1 GB offloaded to CPU must traverse the PCIe bus on every forward pass. σ=0.00 across all runs confirms this is a hard hardware throughput floor, not inference noise. Estimated native throughput (no offload, if hardware permitted) would be ~25–35 t/s based on model size relative to the 14B FP8 result. This model requires hardware with ≥24 GB VRAM per GPU (or larger TP configuration) to run without offload.

**Why cpu-offload was necessary:** The 32B dense GPTQ INT4 model (16 GB on disk) creates a Marlin weight-repacking peak of ~9.53 GB/GPU during initialization — approximately 1.19× the steady-state shard size. Combined with ~4.5 GB of CUDA/NCCL worker overhead and ~1.2 GB of CUDA contexts from ancillary processes, the initialization peak reaches ~15.2 GB — exceeding the 15.47 GiB GPU limit by ~200 MiB. Offloading 0.5 GB/GPU brings the peak to ~8.93 GB/GPU, providing ~800 MiB headroom. Genesis (27B INT4, 15.65 GB disk) clears this same constraint because its shard is ~166 MB/GPU smaller, giving exactly the required margin.

---

### Qwen3-30B-A3B NVFP4 — SKIPPED ⛔

**Source:** `nvidia/Qwen3-30B-A3B-NVFP4` | **Quantization:** NVFP4 (modelopt W4A4)

**Block:** CUDA 12.8 — requires CUDA ≥ 12.9

FlashInfer's `mm_fp4` → `get_gemm_sm120_module_cutlass_fp4()` JIT-compiles CUTLASS SM120 FP4 GEMM kernels that require CUDA 12.9. This system runs CUDA 12.8 (NVIDIA skipped 12.9 and went directly to 13.0; CUDA 13.0 is installed but crashes genesis with `BLACKWELL_NATIVE_FP4` errors on Q4_K_M weights). Until FlashInfer is updated to build against CUDA 13.0 or NVIDIA releases a compatible 12.x patch, NVFP4 inference is blocked on this hardware.

Expected performance (if CUDA constraint were resolved): NVFP4 uses Blackwell tensor core FP4 paths natively — projected 80–120 t/s range for 30B-A3B MoE, potentially faster than genesis.

---

### Qwen3-32B NVFP4 — SKIPPED ⛔

**Source:** `nvidia/Qwen3-32B-NVFP4` | **Quantization:** NVFP4 (modelopt W4A4)

Same CUDA 12.8 block as above. Additionally, the dense 32B NVFP4 model (~16 GB) would face the same initialization overhead constraint as the GPTQ INT4 version — likely requiring cpu-offload or 24 GB+ GPUs to load even if CUDA were resolved.

---

## Analysis

### The two-tier hardware boundary on 2×16 GB Blackwell

This benchmark defines two distinct viability tiers for 2× RTX 5060 Ti (32 GB total VRAM):

**Tier 1 — Runs natively:**
- Models ≤ ~14–15 GB disk size run cleanly with no workarounds
- Qwen3-14B FP8 (14 GB): 43.54 t/s, loads in ~90s, no flags needed
- Genesis / Qwen3.6-27B INT4 (15.65 GB): 73.35 t/s with MTP, ~40 t/s base

**Tier 2 — Requires cpu-offload to initialize, throughput limited:**
- Models at ~16 GB disk hit a 200 MiB initialization wall from Marlin repacking peak (1.19× weight overhead during repack)
- Dense 32B: cpu-offload makes it usable but 5.25 t/s is not production-viable
- MoE 30B-A3B: cpu-offload required to load but MoE architecture bypasses the throughput penalty — 41.33 t/s

### MoE vs Dense at the memory boundary

The 30B-A3B MoE and 32B dense models are the same disk size (16 GB). Both need cpu-offload to initialize. The throughput difference — 41.33 vs 5.25 t/s — is entirely architectural:

Dense 32B: every token accesses all 32B parameter weights. The offloaded 1 GB must traverse PCIe on every forward pass → PCIe becomes the bottleneck.

MoE 30B-A3B: ~3B params active per token. The offloaded portion is part of the expert weight pool; many tokens route entirely through on-GPU experts, barely touching the offloaded slice. The effective PCIe pressure is ~10× lower.

**Practical conclusion:** On 2×16 GB hardware, MoE at 30B is the better choice over dense at 32B by roughly 8×, despite identical VRAM requirements.

### NVFP4 — the locked door

NVFP4 is the format this hardware was built for. The RTX 5060 Ti has Blackwell SM_120 tensor cores with native FP4 support. An NVFP4 30B-A3B MoE at ~9 GB could load with full KV headroom and potentially exceed genesis throughput without MTP. It's blocked purely by the CUDA 12.8 → 12.9 dependency in FlashInfer's CUTLASS kernel JIT. Resolution: upgrade CUDA runtime or wait for a FlashInfer update.

### Attention backend — TRITON_ATTN

FlashInfer 0.6.8.post1 fails with `No supported CUDA architectures found for major versions [12]` for standard Transformer models on SM 12.0 + CUDA 12.8. Genesis avoids this via a model-specific Triton kernel substitution (P60B genesis patch) that is architecture-specific to the GDN/SSM hybrid. All eval models use `VLLM_ATTENTION_BACKEND=TRITON_ATTN` (Triton 3.6.0), which compiles correctly for SM 12.0. Throughput impact vs FlashInfer is not characterized here but expected to be small (<5%) for these model sizes.

---

*Benchmark by Dino Vitale | cha0tiktower | 2026-05-16*
*Hardware: 2× RTX 5060 Ti 16 GB (Blackwell SM_120) | vLLM 0.21.0 + Genesis patches | CUDA 12.8*
