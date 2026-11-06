# P14 model survey — 2026-11-06 (search only, no benchmarks run)

**Question:** anything released since the 2026-10-21 survey that could beat production
(Qwen3.6-35B-A3B UD-IQ4_NL + `--spec-type draft-mtp`: 34 t/s short / 19 t/s at 31k, 9.06/11 on the
9-scenario agent harness, 262k ctx) on cha0tikp14 (Ryzen AI 7 PRO 350, Radeon 860M gfx1152, 64 GB
DDR5-5600, UMA 16 GB, llama.cpp Vulkan)?

Two independent searches, same bar: Grok over X (`grok-x-survey.md`) and a web/HF/llama.cpp sweep.
Both converged.

## Verdict: one candidate worth an afternoon — Groot-19B-A3B-261023

| | Groot-19B-A3B-261023 | production |
|---|---|---|
| org / date / licence | GrootTeam, 2026-10-23, Apache 2.0 | Qwen |
| architecture | expert-pruned Qwen3.6-35B-A3B, same GDN+full-attention hybrid, same MTP head (`qwen35moe`) | — |
| total / active | ~19B / ~3B (+0.4B MTP) | 35B / 3B |
| Q4 GGUF size | **11.7 GB → fits inside the 16 GB UMA carve-out** | ~19–20 GB (spills to GTT) |
| context | 262k native | 262k |
| vendor claims | beats Qwen3.6-35B-A3B on 12/16 benches (Terminal-Bench 2.1 52.1 vs 43.8, LongBench v2 62.0 vs 48.1), 23% fewer output tokens | — |
| independent evidence | **none** | our own harness |
| GGUF to use | bartowski `GrootTeam_Groot-19B-A3B-261023-GGUF` or prithivMLmods `…-MTP-GGUF` (the official GGUF strips the MTP layer) | — |

Mechanism to beat production on both axes: same active width + same MTP path (so ≥ 34 t/s is plausible),
whole model resident in VRAM (no GTT spill), shorter outputs. Everything about quality is self-reported.
**Test = speedbench.sh + harness.py exactly as 2026-10-20; replace production only if ≥ 9.06/11 and ≥ 34 t/s.**

## Checked and parked
- **Flint 40B-A2.5B** (RecursiveSI, 10-21): strong vendor SWE/Terminal numbers, llama.cpp-native since b11803, 262k; but no MTP, bigger file than production, 7900 XTX Vulkan users see it no faster per token than the 35B-A3B class, tool-call bug open on NVFP4/IQ quants (#31000). Secondary test only if Groot fails on quality.
- **Xing4.0-29B-A4B** (China Telecom; llama.cpp support merged 11-05): mHC ops have no Vulkan kernels → CPU fallback per layer; 4B active. Park until Vulkan DSV4_HC lands.
- **Clover-35B-A3B-Preview** (DiffuSpace, 10-24): production-derived; AR mode only in llama.cpp, self-speculation PR #31732 unmerged, 128k ctx. Skip.
- **Nemotron 3.5 Bolt E4B**, MiMo-V2.6-9B, Metis-1.6, Air-26B-A4B (Gemma 4 requant), LFM3 small models: fail the quality or size bar.
- Over size cap: Qwen3.8-27B, Qwen3.8-Flash-Next, DeepSeek-V4.1-Flash, Mistral Large 4, Kimi K3.1 Pro, Ripple-65B, Nemotron Bolt 74B/Super 120B.

## Free speed for production (independent of model choice)
1. **`--spec-draft-n-max 1`**: an 860M owner (same silicon) measured 33.0 → 41.2 t/s with n-max 1 at 91% acceptance vs 39.8 at n-max 2 (github.com/demian63s/llama-amd-igpu-notes, Qwen3.6-35B-A3B UD-Q2_K_XL, b11706). Cheapest test on the table.
2. **Rebuild llama.cpp ≥ b12170** (v0.9.0 = 11-04): RDNA3 small-n split-K (#30146, APUs pass the gate but unmeasured), rms-norm subgroup reductions, MTP checkpoint fixes (#30141/#31350), ClassLRU MoE host-expert cache (#31233, +6–7% decode vs SLRU — the "experts in host RAM, cache on device" shape of a 16 GB carve-out). Open patch worth trying: #25666 (disable MMVQ on AMD for spec-decode steps).
3. **Linux 7.4 AMD IOMMU PerfOpt** (default-on for Radeon iGPUs; Phoronix: Strix Point up to +23%, Krackan "very large gains"): arrives with Tumbleweed's 7.4 kernel (~late Dec). Biggest free win; nothing to do but take the kernel when it ships.

Notes: ROCm has no gfx1152 Tensile libs (Lemonade #2002) — Vulkan stays the path. Nobody on X or the
forums posted a new "best model" for Krackan/860M in this window.
