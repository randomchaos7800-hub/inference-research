# supergemma4-26b Dual-GPU Inference Optimization — Research Program

## Goal
Maximize generation speed (tg512 tok/s) for supergemma4-26b Q4_K_M on dual RTX 5060 Ti.
Baseline: 99.2 tok/s tg512 | 97.4 tok/s tg128 | 4502 tok/s pp2048 | 5569 tok/s pp8192
Evaluation: llama-bench (3 reps, pp512+pp2048+pp8192+tg128+tg512)

## Hardware Context
- 2x RTX 5060 Ti (Blackwell SM120), 16 GB each = 32 GB total VRAM
- GPU 0: PCIe x8 Gen5 (from CPU) | GPU 1: PCIe x4 Gen4 (chipset) — Z890 board design
- Model uses ~10.4/10.0 GB per GPU — ~12 GB headroom total
- Arrow Lake CPU: 8 P-cores (0-7) + 12 E-cores (8-19), no AVX-512
- CUDA 12.8 binary (build/), NOT build-cuda13/ — CUDA 13 crashes with Q4_K_M on Blackwell

## Current Config (baseline)
- No --override-tensor (all 30 layers on GPU — fits cleanly with 32 GB VRAM)
- No CUDA_VISIBLE_DEVICES (both GPUs used, auto-balanced)
- -ctk q4_0 -ctv q4_0, --ubatch-size 1024, --flash-attn on, --mlock
- --threads 8, --cpu-range 0-7, --cpu-strict 1, --ctx-size 65536

## Key Change vs Previous Research
Prior research (single GPU) was VRAM-constrained (~900 MiB headroom).
This run has ~12 GB headroom — experiments that were blocked before are now safe.
DO NOT add --override-tensor back — model fits entirely on GPU and is faster without it.

## Research Priorities
1. **KV cache quant** — q4_0 is current; test q8_0, iq4_nl, q5_0 — may affect GPU memory bandwidth
2. **ubatch-size** — 1024 is current; test 512, 2048, 4096 — MoE expert batching sweet spot may differ on dual GPU
3. **batch-size** — test 4096, 8192 for prompt processing
4. **Split mode** — layer (default) vs row vs tensor — row/tensor may exploit PCIe bandwidth differently
5. **Tensor split ratio** — GPU 0 has 2x PCIe bandwidth vs GPU 1 (x8 vs x4); slight bias to GPU 0 may help
6. **Threading** — test E-core inclusion (threads 12-20 with cpu-range 0-19)
7. **poll** — 0 (pure event) vs 100 (max polling) — affects GPU sync latency
8. **NUMA** — distribute mode may help Arrow Lake memory topology

## Forbidden
- DO NOT add --override-tensor
- DO NOT set CUDA_VISIBLE_DEVICES
- DO NOT use CUDA 13 build (build-cuda13/)
- DO NOT reduce ctx-size (bench uses default small context anyway)
- NEVER skip flash-attn

## Scoring
Primary metric: tg512 tok/s (higher = better)
Secondary: pp2048 tok/s (note: improvements to generation sometimes regress prompt — acceptable tradeoff)
Improvement threshold: +0.8 tok/s (~1%) to count as a confirmed improvement
