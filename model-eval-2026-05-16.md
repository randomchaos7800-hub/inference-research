# Model Evaluation — cha0tiktower
**Date:** 2026-05-16 08:35
**Hardware:** 2× RTX 5060 Ti 16GB GDDR7 (Blackwell SM_120), TP=2, 32GB total VRAM
**Inference engine:** vLLM 0.21.0 + Genesis patches
**Context:** 32768 tokens | No MTP (eval models use standard vLLM; MTP is genesis-patch-only)
**Benchmark:** 2 warmup + 7 timed runs, 512 tokens each, 7 unique prompts (no prefix cache reuse)
**Baseline:** Genesis (Qwen3.6-27B INT4 AutoRound, mtp n=3) = **73.35 t/s**

---

## Results Summary

| Model | Arch | Format | VRAM used | Median t/s | vs baseline | Status |
|---|---|---|---|---|---|---|

| **Qwen3-30B-A3B NVFP4** | MoE (30B total / ~3B active) | NVFP4 (Blackwell native W4A4) | — | — | — | ❌ FAILED |
| **Qwen3-32B dense NVFP4** | Dense (32B) | NVFP4 (Blackwell native W4A4) | — | — | — | ❌ FAILED |
| **Qwen3-32B GPTQ INT4** | Dense (32B) | GPTQ INT4 (AutoRound 0.5.1, group_size=128) | — | — | — | ❌ FAILED |
| **Qwen3-14B FP8** | Dense (14B) | FP8 (W8A8) | 13069/12300 MiB | **43.5** | -29.8 (-40.6%) | ⚠️ LOSS |
| **Qwen3-30B-A3B GPTQ INT4** | MoE (30B total / ~3B active) | GPTQ INT4 (official Qwen release) | — | — | — | ❌ FAILED |
| **Qwen3-32B GPTQ INT4** | Dense (32B) | GPTQ INT4 (AutoRound 0.5.1, group_size=128) | 14635/13844 MiB | **5.2** | -68.1 (-92.8%) | ⚠️ LOSS |
| **Qwen3-30B-A3B GPTQ INT4** | MoE (30B total / ~3B active) | GPTQ INT4 (official Qwen release) | 14633/13454 MiB | **41.3** | -32.0 (-43.7%) | ⚠️ LOSS |
---

## Detailed Results

### Qwen3-30B-A3B NVFP4

- **Status:** FAILED
- **Source:** `nvidia/Qwen3-30B-A3B-NVFP4`
- **Notes:** NVFP4 requires CUDA>=12.9: flashinfer.mm_fp4 calls get_gemm_sm120_module_cutlass_fp4() which JIT-compiles CUTLASS SM120 FP4 GEMM kernels — blocked on CUDA 12.8. Requires CUDA upgrade.

### Qwen3-32B dense NVFP4

- **Status:** FAILED
- **Source:** `nvidia/Qwen3-32B-NVFP4`
- **Notes:** NVFP4 requires CUDA>=12.9: flashinfer.mm_fp4 calls get_gemm_sm120_module_cutlass_fp4() which JIT-compiles CUTLASS SM120 FP4 GEMM kernels — blocked on CUDA 12.8. Requires CUDA upgrade.

### Qwen3-32B GPTQ INT4

- **Status:** FAILED
- **Source:** `already on disk`
- **Notes:** server never became healthy — check /tmp/eval-qwen3-32b-gptq.log

### Qwen3-14B FP8

| Field | Value |
|---|---|
| **Source** | `Qwen/Qwen3-14B-FP8` |
| **Architecture** | Dense (14B) |
| **Quantization** | FP8 (W8A8) |
| **VRAM used (GPU 0 / GPU 1)** | 13069/12300 MiB |
| **Median t/s** | **43.54** |
| **Min / Max** | 42.73 / 43.69 t/s |
| **Std dev** | 0.41 t/s |
| **vs genesis (73.35 t/s)** | -29.81 t/s (-40.6%) |
| **MTP** | none (standard vLLM — genesis MTP is patch-only) |
| **Context** | 32768 tokens |
| **GMU** | 0.80 |

**Per-run results:**
  run 1: 43.54 t/s  
  run 2: 42.73 t/s  
  run 3: 43.69 t/s  
  run 4: 43.65 t/s  
  run 5: 43.15 t/s

**Notes:** —

### Qwen3-30B-A3B GPTQ INT4

- **Status:** FAILED
- **Source:** `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- **Notes:** server never became healthy — check /tmp/eval-qwen3-30b-a3b-gptq.log

### Qwen3-32B GPTQ INT4

| Field | Value |
|---|---|
| **Source** | `already on disk` |
| **Architecture** | Dense (32B) |
| **Quantization** | GPTQ INT4 (AutoRound 0.5.1, group_size=128) |
| **VRAM used (GPU 0 / GPU 1)** | 14635/13844 MiB |
| **Median t/s** | **5.25** |
| **Min / Max** | 5.25 / 5.26 t/s |
| **Std dev** | 0.00 t/s |
| **vs genesis (73.35 t/s)** | -68.10 t/s (-92.8%) |
| **MTP** | none (standard vLLM — genesis MTP is patch-only) |
| **Context** | 32768 tokens |
| **GMU** | 0.90 |

**Per-run results:**
  run 1: 5.25 t/s  
  run 2: 5.26 t/s  
  run 3: 5.25 t/s  
  run 4: 5.26 t/s  
  run 5: 5.25 t/s

**Notes:** —

### Qwen3-30B-A3B GPTQ INT4

| Field | Value |
|---|---|
| **Source** | `Qwen/Qwen3-30B-A3B-GPTQ-Int4` |
| **Architecture** | MoE (30B total / ~3B active) |
| **Quantization** | GPTQ INT4 (official Qwen release) |
| **VRAM used (GPU 0 / GPU 1)** | 14633/13454 MiB |
| **Median t/s** | **41.33** |
| **Min / Max** | 41.01 / 41.38 t/s |
| **Std dev** | 0.17 t/s |
| **vs genesis (73.35 t/s)** | -32.02 t/s (-43.7%) |
| **MTP** | none (standard vLLM — genesis MTP is patch-only) |
| **Context** | 32768 tokens |
| **GMU** | 0.82 |

**Per-run results:**
  run 1: 41.37 t/s  
  run 2: 41.09 t/s  
  run 3: 41.38 t/s  
  run 4: 41.33 t/s  
  run 5: 41.01 t/s

**Notes:** —

