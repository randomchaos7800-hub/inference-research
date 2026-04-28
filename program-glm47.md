# GLM-4.7-Flash Inference Optimization — Research Program

## Goal
Maximize generation speed (tok/s) for GLM-4.7-Flash Q5_K_M on dual RTX 5060 Ti (32GB total VRAM).
Baseline: 95.9 tok/s gen, 149.7 tok/s prompt.

## Hardware Context
- 2x RTX 5060 Ti, Blackwell SM120, 15.8GB VRAM each (31.6GB total)
- Model uses ~20GB VRAM at rest, ~8GB headroom across both cards
- Arrow Lake CPU: 8 P-cores (0-7), 12 E-cores (8-19), no AVX-512
- All model layers fit on GPU — no CPU offload needed
- CUDA 12.8 binary (build/), NOT build-cuda13/ which crashes

## Model Architecture
- GLM-4.7-Flash: 30B total params, MoE with ~3B active per token
- Expert routing is a key compute pattern — bandwidth matters more than raw FLOPS
- Flash attention enabled, KV cache at q4_0 baseline

## Research Priorities (in order)
1. KV cache quantization — try q8_0, f16, iq4_nl, q5_0 combinations for K and V separately
2. ubatch-size tuning — try 512, 2048, 4096; MoE may batch experts differently than dense models
3. Parallel slots (--parallel) — test 1, 2, 4, 8; affects KV cache allocation
4. Tensor split ratio — try slight imbalances (1.1,0.9 etc) to balance actual VRAM usage
5. defrag-thold — test 0.01, 0.1, 0.5 for KV cache fragmentation
6. --no-mmap — may help or hurt depending on model load path

## Exact Flag Names (use these exactly in flags_changed)
- KV cache key type:   `ctk` with values: q4_0, q8_0, f16, iq4_nl, q5_0
- KV cache value type: `ctv` with values: q4_0, q8_0, f16, iq4_nl, q5_0
- ubatch size:         `ubatch_size` (integer)
- context size:        `ctx_size` (integer)
- GPU layers:          `n_gpu_layers` (integer)
- tensor split:        `tensor_split` (string like "1,1" or "1.2,0.8")
- threads:             `threads` (integer)
- mlock:               `mlock` (true/false)
- flash attention:     `flash_attn` (true/false)
- For other flags use `extra_flags` array with exact llama-server syntax e.g. ["--defrag-thold 0.1"]

## Hard Constraints
- NEVER change --model, --host, --port, --alias
- NEVER set tensor-split that causes OOM (both GPUs have ~8GB headroom at baseline)
- NEVER disable flash-attn (always helps on Blackwell)
- NEVER use CUDA 13 build path
- If a server fails to start, mark as FAILED and try something different
- NEVER STOP — run all 10 iterations without pausing

## Scoring Guidance
Each criterion score must be exactly 0 or 1 (integer). No decimals, no other values.
- novelty: 1 if not tried before, 0 if already in results history
- feasibility: 1 if achievable with llama-server flags only
- impact: 1 if plausibly moves gen tok/s by more than 3%
- safety: 1 if low OOM/crash risk given 8GB VRAM headroom
- measurable: 1 if produces a clear numeric tok/s result
- orthogonality: 1 if independent from other experiments this session
