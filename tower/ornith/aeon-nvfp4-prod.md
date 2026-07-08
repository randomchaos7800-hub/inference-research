# Ornith AEON NVFP4 production (2026-06-27)

Fleet `:8010` → **AEON Ornith-1.0-35B-AEON-Ultimate-Uncensored NVFP4** on native vLLM 0.23 (x86 port of AEON's DGX Spark recipe).

## Live state

| Item | Value |
|---|---|
| Proxy backend | `ornith` |
| Backend | `ornith-backend.service` → `:8030` |
| Model | `AEON-7/Ornith-1.0-35B-AEON-Ultimate-Uncensored-NVFP4` (~23 GB) |
| Engine | vLLM **0.23** (`/home/dino/venvs/vllm-023`) |
| Quant | NVFP4A16 (W4A16): FP4 experts/MLP, BF16 elsewhere |
| Kernels | Marlin linear (auto) + `flashinfer_b12x` MoE + local SM_120 Marlin patch |
| Context | **131072** (`--max-model-len`), **`--kv-cache-dtype fp8`**, `--language-model-only` |
| GMU | 0.88 |
| Client | `http://tower:8010/v1`, model `local` |
| Throughput | ~101 tok/s warmed short-gen through `:8010` (2026-06-27) |

## Tower scripts

| Path | Role |
|---|---|
| `/home/dino/bin/ornith-start.sh` | Production `ExecStart` |
| `/home/dino/bin/apply-vllm023-ornith-patches.sh` | Idempotent SM_120 / W4A16 patches |
| `/home/dino/bin/ornith-llama-start.sh.bak` | Rollback to GGUF llama.cpp |

## GGUF baseline (2026-06-25–26)

| Item | GGUF Q4_K_M | AEON NVFP4 (this deploy) |
|---|---|---|
| Engine | llama.cpp layer-split | vLLM 0.23 TP=2 |
| Weights on disk | ~20 GB | ~23 GB |
| KV cache | q4 (`--cache-type-k/v q4_0`) | **fp8** (required for fair context) |
| Max context | 131072 | **131072** (with fp8 KV; BF16 KV capped ~32k) |
| LangChain brutal | **56/66 (84.8%)** | **56/66 (84.8%)** (2026-06-28) |
| Short-gen speed | ~95–130 tok/s | ~101 tok/s |

## KV cache confound (important)

First NVFP4 port used `kv_cache_dtype=auto` → BF16 attention KV. Against GGUF's q4 KV that unfairly capped context at **32k** and looked like an NVFP4 regression.

With `--kv-cache-dtype fp8` and `--language-model-only` (no vision tower):

- `max-model-len=65536` — loads (288k KV token budget)
- `max-model-len=131072` — loads (338k KV token budget)

AEON's DGX guide omits fp8 KV because full-model vision forces BF16 KV; `language-model-only` avoids that on tower.

## Rollback

```bash
# Cloud failover
ssh dino@tower '/home/dino/bin/proxy-switch openrouter'

# GGUF Ornith
ssh dino@tower 'cp /home/dino/bin/ornith-llama-start.sh.bak /home/dino/bin/ornith-start.sh && systemctl --user restart ornith-backend'

# Genesis
ssh dino@tower '/home/dino/bin/tower-return-prod'
```

## LangChain brutal eval (2026-06-28)

Direct `:8030`, `ornith-aeon-ultimate-nvfp4`, tool flags enabled.

| Task | GGUF | AEON NVFP4 |
|---|---:|---:|
| Typewriter (1 tool) | 20/20 | 19/20 |
| Typewriter (26 tools) | 20/20 | 20/20 |
| Multiverse Math | 10/18 | 10/18 |
| Relational Data | 6/8 | **7/8** |
| **Overall** | **56/66 (84.8%)** | **56/66 (84.8%)** |

Receipts: [langchain-brutal-eval-aeon-nvfp4.json](langchain-brutal-eval-aeon-nvfp4.json), [langchain-brutal-eval-aeon-nvfp4.log](langchain-brutal-eval-aeon-nvfp4.log)

## Autoresearch sweep (2026-06-28)

Karpathy one-var-at-a-time sweep across 11 candidates (mamba cache dtype, linear backend, gmu, max_num_seqs, ctx length, kv dtype, NCCL, chunked prefill, flashinfer sampler). Baseline: 105.19 t/s.

**Result: 0/11 improvements. Baseline is optimal.**

Best confirmed config: gmu=0.88, fp8 KV, float32 Mamba cache, max_num_seqs=2. Key findings:
- gmu=0.90 → OOM on second request (only 74 MiB free post-load)
- fp8 KV confirmed +2.24 t/s over BF16 (biggest lever already in prod)
- linear-backend cutlass/flashinfer → engine crash (unsupported in vLLM-023)

## lm-eval benchmarks (2026-06-28)

lm-evaluation-harness 0.4.12, openai-completions backend, direct :8030, 5-shot where applicable.

| Benchmark | Score | Notes |
|---|---|---|
| MMLU-generative (5-shot) | ❌ Failed | HuggingFace 504 timeout mid-download |
| ARC-Challenge-Chat | 0% exact_match | Format mismatch — chat task over completions API |
| GSM8K (5-shot, n=1319) | **15.6%** flexible / **13.9%** strict | Full test set |

**Verdict:** Mamba hybrid SSMs trade reasoning depth for throughput. GSM8K 15.6% for a 35B model is poor — Qwen2.5-7B scores ~85%. The recurrent state cannot backtrack or attend arbitrarily, which is exactly what multi-step math punishes. This model is a throughput/context vehicle, not a reasoning model. Good fit for long-doc summarization and high-volume chat at speed. Wrong choice for code, math, or multi-step logic.

## Open items

- MMLU re-run (hit transient HF 504, not a model failure)
- fp8 KV quality check on hybrid GatedDeltaNet + attn arch