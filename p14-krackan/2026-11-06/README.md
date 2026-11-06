# P14 model survey — 2026-11-06: Groot-19B-A3B vs production (speed pass run; quality pass skipped)

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

## RESULT (run 2026-11-06 13:30–15:30, same protocol as 2026-10-20): Groot loses on speed; production stays

172/172 valid runs, two interleaved repetitions (rep 2 reverse order), 150 s idle per cell, sustained clocks
(sclk 2507–2619 MHz in the deep cells), `-ngl 99 -c 65536 -t 8 -fa on`, llama.cpp b11776 Vulkan, UMA 16 GiB.
Rep-to-rep agreement ≤ 0.7 t/s on every cell. Raw: `raw/speed.jsonl`, server logs in `raw/`.

| cell | tg clean | tg 4.5k | tg 31k | pp 4.5k | pp 31k | MTP accept c/l/d |
|---|---|---|---|---|---|---|
| **qwen-iq4-mtp2 (production control)** | **33.8** | 29.6 | 19.0 | 291 | 205 | 83/73/53 % |
| qwen-iq4-mtp1 | 30.9 | 28.3 | **21.7** | 291 | 206 | 88/83/74 % |
| groot-iq4nl-mtp2 | 25.6 | 28.1 | 20.2 | **408** | **265** | 52/68/61 % |
| groot-iq4nl-nomtp | 23.9 | 22.9 | 19.2 | 429 | 284 | – |
| groot-q4km-mtp2 | 26.7 | 27.8 | 20.7 | 390 | 258 | 56/67/63 % |

- **Control reproduces October exactly** (33.9/28.2/19.4 then; 33.8/29.6/19.0 now).
- **Groot's raw decode = production's raw decode** (23.9 vs 23.7 no-MTP). Pruning 35B → 19B total changed nothing per
  token: both move the same ~3B active weights and this APU is bandwidth-bound. The 11.7 GB file fitting inside the
  UMA carve-out did not help decode.
- **Groot's MTP head is worse than the parent's**: 52 % acceptance at short context vs 83 %, so speculative decoding
  lifts it to 26 t/s instead of 34. That is the entire gap. Q4_K_M behaves the same (56 %).
- **Groot wins prefill by ~40 %** at every context (408 vs 291 at 4.5k; 265 vs 205 at 31k) — fewer full-attention
  layers. Real, but prefill was never the bottleneck for the offline agent.
- **`--spec-draft-n-max 1` is a trade, not a win** on this quant: −2.9 t/s at short context, +2.7 t/s at 31k
  (acceptance 88/83/74 vs 83/73/53). The 860M owner's "41 t/s" was a UD-Q2_K_XL file at `-c 4096`; it does not
  transfer to UD-IQ4_NL at 64k. Worth revisiting only if the agent's typical context is long.

**Verdict:** keep `Qwen3.6-35B-A3B-UD-IQ4_NL` + `--spec-type draft-mtp --spec-draft-n-max 2`. The replacement bar
was ≥ 9.06/11 AND ≥ 34 t/s; speed failed by 8 t/s, so the quality pass was skipped on Dino's call
(`stop-after-speed.sh`, `raw/progress.log`). Groot's quality is therefore unmeasured here; its vendor claims stand
untested. Groot files left in `~/models/` on the P14 (2 × 12.5 GB) for any later prefill-focused use.

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
