# SGLang vs vLLM — SM_120 (RTX 5060 Ti) Side-by-Side

**Hardware:** 2x RTX 5060 Ti 16GB GDDR7, Blackwell SM_120, Intel Core Ultra 7 265F, Ubuntu 24.04  
**Current stack:** vLLM dual-instance, Genesis ~80 t/s + AEON ~69 t/s  
**Assessment date:** 2026-05-05

---

## Feature Comparison

| Feature | vLLM (current) | SGLang | Notes |
|---|---|---|---|
| **SM_120 quantized inference** | ✅ Field-confirmed working | ❌ Garbage output bug #21132 (open) | Blockers: INT4 + FP8 both affected |
| **GPTQ-Marlin INT4** | ✅ Working (Genesis live) | ❌ Broken on SM_120 | Same bug |
| **NVFP4 / modelopt** | ⚠️ Marlin fallback (open #31085) | ❌ SM100+ only, SM_120 unsupported | AEON weights unusable in SGLang |
| **MTP speculative decoding** | ✅ Working; Marlin path ~-22% penalty | ✅ Working; same Marlin penalty | Both penalize MTP via Marlin on SM_120 |
| **fp8 KV cache** | ✅ Working (Genesis live 160K) | ⚠️ Shared-memory overflow reported (#16816) | SM_120 needs 114KB, has 99KB |
| **TP=2 dual-GPU** | ✅ Battle-tested (your live setup) | ⚠️ Hang reports on dual-consumer Blackwell (#23512) | CUDA 13.0 implicated |
| **RadixAttention (prefix cache)** | ⚠️ Manual `--enable-prefix-caching` | ✅ Automatic, always-on | ~7-10% TTFT gain on warm cache |
| **Context length 160K** | ✅ Live (160K Genesis) | ✅ Supports up to 262K | Not a differentiator |
| **OpenAI API compatibility** | ✅ Full | ✅ Full drop-in | Zero client changes needed |
| **Blackwell production stability** | ✅ More field reports, tracked workarounds | ⚠️ Beta-quality on SM_120 consumer | H100/A100 SGLang is stable |

---

## Performance Benchmarks

| Scenario | vLLM | SGLang | Source |
|---|---|---|---|
| H100, high concurrency, 8B model | 12,500 t/s | 16,200 t/s (+29%) | LMSYS benchmark |
| H100, single-turn unique prompts | 60 t/s | 52.7 t/s (-12%) | Community test |
| H100, 7K-token cached prefix | 32.8 t/s | ~35 t/s (+7%) | RunPod analysis |
| SM_120, correct output w/ INT4 | ✅ Confirmed | ❌ Garbage output | #21132 |
| Your Genesis config (SM_120, INT4) | **~80 t/s live** | Unknown (blocked by #21132) | Live measurement |

> The 29% SGLang win requires high concurrency batching. Single-user, single-stream workloads see ~7% on cached prefixes, ~0% or negative on unique requests.

---

## Config Translation (if you ever migrate)

| vLLM flag | SGLang equivalent |
|---|---|
| `--gpu-memory-utilization 0.88` | `--mem-fraction-static 0.88` |
| `--enable-prefix-caching` | Automatic (always on) |
| `--quantization gptq_marlin` | Auto-detected, or `--quantization gptq_marlin` |
| `--kv-cache-dtype fp8` | `--kv-cache-dtype fp8_e4m3` |
| `--tensor-parallel-size 2` | `--tp 2` |
| `--max-model-len 163840` | `--context-length 163840` |
| `--speculative-config` (MTP) | `--speculative-algorithm EAGLE --speculative-num-steps 3 --speculative-eagle-topk 1 --speculative-num-draft-tokens 4` + `SGLANG_ENABLE_SPEC_V2=1` |

---

## Verdict

**Stay on vLLM.** SGLang issue #21132 (garbage output with quantized models on SM_120) is unresolved and hits both Genesis and AEON configs directly. NVFP4 on SM_120 is unsupported entirely.

**One real SGLang advantage:** RadixAttention would give ~7-10% faster TTFT on agent calls that share long system prompts/tool definitions. Not worth the migration risk against an open correctness bug.

**Revisit when:** SGLang closes #21132 and ships a stable SM_120 wheel. Check 2026 Q2 roadmap milestone. Estimated: 3-4 months.

---

## Key Issue Tracker Links

- SGLang SM_120 garbage output (INT4 + FP8): https://github.com/sgl-project/sglang/issues/21132
- SGLang SM_120 CUDA graph bug: https://github.com/sgl-project/sglang/issues/9542
- SGLang NVFP4 on SM_120 (SM100+ only): https://github.com/sgl-project/sglang/issues/11725
- SGLang fp8 shared-memory overflow SM_120: https://github.com/sgl-project/sglang/issues/16816
- SGLang dual-consumer Blackwell hang: https://github.com/sgl-project/sglang/discussions/23512
- SGLang 2026 Q2 roadmap: https://github.com/sgl-project/sglang/issues/22949
- vLLM SM_120 NVFP4 kernel routing: https://github.com/vllm-project/vllm/issues/31085
- vLLM MTP crash on Qwen3.6-27B FP8: https://github.com/vllm-project/vllm/issues/40756
