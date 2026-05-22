# supergemma4-26b Single-GPU Inference Optimization — Research Program

## Goal
Maximize generation speed (tok/s) for supergemma4-26b Q4_K_M on a single RTX 5060 Ti (GPU 0 only).
Baseline: 61.7 tok/s gen, 281.9 tok/s prompt (ctx 32768, q4_0/q4_0, last 6 MoE expert layers on CPU).

## Hardware Context
- Single RTX 5060 Ti, Blackwell SM120, 16311 MiB VRAM (GPU 0 only — CUDA_VISIBLE_DEVICES=0)
- VRAM at baseline: ~15100 MiB used, ~900 MiB headroom — VERY TIGHT
- Arrow Lake CPU: 8 P-cores (0-7, 5.3 GHz) + 12 E-cores (8-19, 4.6 GHz), no AVX-512
- CUDA 12.8 binary (build/), NOT build-cuda13/ which crashes on Blackwell with Q4_K_M

## Model Architecture
- supergemma4-26b: 30 transformer layers, 128 experts, top-8 routing (MoE)
- Expert layers are large — offloading expert tensors to CPU saves significant VRAM
- Current override-tensor offloads last 6 layers (blk.24–29) expert tensors to CPU
- Non-expert tensors (attention, norms) all stay on GPU for all layers

## Research Priorities (in order)
1. **ubatch-size** — try 512 and 2048; MoE expert batching may have a sweet spot (VRAM-neutral)
2. **E-core threading for CPU experts** — try threads=12-16 with cpu-range 0-19 (E-cores help with CPU-offloaded expert computation) — VRAM-neutral
3. **defrag-thold** — try 0.1 and 0.5 to reduce KV cache fragmentation — VRAM-neutral
4. **CPU expert layer count fine-tuning** — try blk.22-29 (8 layers) or blk.26-29 (4 layers) to find the optimal GPU/CPU expert split — may slightly change VRAM
5. **--no-mmap** — test if disabling memory-mapped loading improves runtime throughput
6. **--parallel slots** — try 2 parallel slots to see if pre-allocation affects throughput

## What Has Already Failed (do NOT repeat these)
All ctx_size reduction + KV cache upgrade experiments OOMed (8 failures):
- Offloading blk.20-29 + ctx 16384 + any KV type = OOM every time
- Offloading blk.18-29 + ctx 16384 = OOM
- The model simply cannot accommodate different KV types with current VRAM, regardless of ctx size
- DO NOT suggest any experiment involving ctx_size changes or KV type changes until the new mobo arrives

## Flag Representation
The override-tensor flag is represented as an extra_flag string. To change the CPU offload range:
- Current (6 layers CPU): `--override-tensor "blk\\.(2[4-9])\\..*exps.*=CPU"`
- More CPU (10 layers):   `--override-tensor "blk\\.(2[0-9])\\..*exps.*=CPU"`
- More CPU (12 layers):   `--override-tensor "blk\\.(1[89]|2[0-9])\\..*exps.*=CPU"`
- Always include this flag — removing it causes OOM on single GPU

## Exact Flag Names (use these in flags_changed)
- KV cache key type:   `ctk` with values: q4_0, q8_0, q5_0, iq4_nl
- KV cache value type: `ctv` with values: q4_0, q8_0, q5_0, iq4_nl
- ubatch size:         `ubatch_size` (integer)
- context size:        `ctx_size` (integer)
- threads:             `threads` (integer)
- threads_batch:       `threads_batch` (integer)
- cpu_range:           `cpu_range` (string like "0-7" or "0-19")
- For other flags use `extra_flags` array e.g. ["--defrag-thold 0.1", "--override-tensor \"blk\\\\.(2[0-9])\\\\..*exps.*=CPU\""]

## Hard Constraints
- ALWAYS include --override-tensor in extra_flags — omitting it will OOM (model is ~20GB weights alone)
- NEVER increase ctx_size above 32768 — already at VRAM limit
- NEVER remove flash-attn (always helps on Blackwell)
- NEVER use CUDA 13 build path
- NEVER set CUDA_VISIBLE_DEVICES — it's set in the environment already
- VRAM headroom is ~900 MiB at baseline — any experiment that increases VRAM usage must first free space (e.g. reduce ctx or offload more layers)
- If a server fails to start, mark FAILED and try something that uses LESS VRAM next

## Scoring Guidance
Each criterion score must be exactly 0 or 1 (integer only).
- novelty: 1 if not tried before, 0 if already in results history
- feasibility: 1 if achievable with llama-server flags and won't OOM given tight VRAM
- impact: 1 if plausibly moves gen tok/s by more than 3%
- safety: 1 if low OOM/crash risk (be conservative — headroom is only ~900 MiB)
- measurable: 1 if produces a clear numeric tok/s result
- orthogonality: 1 if independent from other experiments this session
