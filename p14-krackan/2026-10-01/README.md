# ROCm vs Vulkan on an AMD Krackan Point iGPU — 2026-10-01

Qwen3.6-35B-A3B (MoE, 3B active, UD-IQ4_NL) on a **ThinkPad P14s Gen 6 AMD**:
Ryzen AI 7 PRO 350, Radeon 860M, **gfx1152**, 32 GB RAM, 16 GiB UMA carve-out,
openSUSE Tumbleweed, kernel 7.2.6, on AC, `performance` governor.

Reviewers benchmark Strix Halo because it is the 128 GB halo part. **Krackan is
the cheap one in an ordinary work laptop, which is the configuration most people
actually have, and nobody measures it.** These are receipts for that gap.

Write-up: [`../../papers/what-took-the-clock.md`](../../papers/what-took-the-clock.md)
*(What Took the Clock: Toolchain, Power and Backend Attribution on an AMD APU)*.

Method: [`../../BENCHMARK-PROTOCOL.md`](../../BENCHMARK-PROTOCOL.md). Most of
that protocol was written *because of* this run — every rule in it is traceable
to a number here that we measured, believed, and had to retract.

---

## Headline

**The compiler matters more than the backend, and ROCm loses despite having the
better kernels.**

Loaded context (5201-token prompt), sustained clocks, `-ngl 36/40`, all binaries
at llama.cpp commit `07fc586e3`:

| binary | prefill t/s | decode t/s | GPU clock | package W |
|---|---|---|---|---|
| ROCm / HIP (Clang 22) | **301.1** | 13.88 | 1044 MHz | 33.1 |
| Vulkan (Clang 22) | 278.6 | 14.77 | 877 MHz | 33.5 |
| Vulkan (GCC 11.4) | 290.5 | 19.88 | 2718 MHz | 34.5 |
| Vulkan (GCC) + MTP | 194.3 | **29.50** | 2552 MHz | 36.3 |

Decode decomposition — backend **+6.4%**, compiler **+34.6%**, MTP **+48.4%**;
the production stack is **2.13×** ROCm end to end.

### Normalise by clock and it inverts

| | prefill per MHz | decode per MHz |
|---|---|---|
| ROCm | **0.288** | **0.0133** |
| Vulkan (GCC) | 0.107 | 0.0073 |

**ROCm is 2.7× more clock-efficient on prefill and 1.8× on decode.** It delivers
*more* prefill than Vulkan while pinned at 1044 MHz against Vulkan's 2718. Its
kernels are not slower — they are better. It loses because binaries built with
`hipcc`/Clang draw 47–48 W against GCC's ~39 W, trip the package power ceiling,
and the hardware takes two thirds of the GPU clock away.

We proved the toolchain effect **on Vulkan**, by building the same source both
ways (Clang: 16.40 t/s @ 877 MHz; GCC: 21.23 t/s @ 2762 MHz). We **cannot** run
the counterfactual for ROCm, because llama.cpp's HIP backend cannot be built
without `hipcc`. So the claim is bounded: *ROCm on this part is defeated by its
required build chain*, not *ROCm would win*.

## Platform limits found

- **ROCm cannot load a 17.1 GB model at a 16 GiB carve-out.** HIP treats the BIOS
  carve-out as a hard VRAM ceiling; RADV spills into GTT transparently. Kernel
  view: VRAM 16384 MiB, GTT 7810 MiB — Vulkan addresses both, ROCm only the
  first. `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1` does not rescue it. **ROCm's
  availability on an APU is a BIOS setting, not a driver question.**
- **ROCm + MTP never boots** at this carve-out (confirmed twice under the clean
  protocol) — the speculative draft context needs VRAM on top of an exhausted
  budget.
- Because of the above, every cell here runs at **partial offload, `-ngl 36`**,
  which is the largest ROCm can take. That is a constraint of the fence, not a
  choice. Full-offload numbers are not in this dataset.
- The BIOS offers `Auto;1GB;2GB;4GB;8GB;16GB;32GB;48GB` — **no 24 GB step**. The
  carve-out is settable from Linux via `think-lmi`
  (`/sys/class/firmware-attributes/thinklmi/attributes/UMAFramebufferSize`).

## Power behaviour

The APU boosts to ~50 W at ~2200 MHz for roughly 25 seconds, then settles to a
sustained ~36 W. Under the Clang-built binaries the GPU clock collapses from
~2200 to ~1050 MHz to stay inside that budget; the GCC build never reaches the
ceiling and holds ~2750 MHz indefinitely.

This is **not thermal** — the package plateaus at 68–72 °C under ROCm, and the
Vulkan control ran *hotter* (80 °C) without throttling at all. It is **not
software state** — restarting the server does not reset it, and RSS is identical
across restarts.

## Corrections made during this run

Published here because the protocol exists to prevent repeats, and hiding them
would make the protocol look like foresight rather than scar tissue.

1. **"Vulkan +23%" → +41% → decomposed.** ROCm was measured first with a fresh
   boost budget while Vulkan ran immediately after in sustained mode. Comparing
   sustained-to-sustained gave +41%, which the compiler control then split into
   `+8.8% backend × +29.4% compiler = +40.8%`.
2. **"MTP costs 2.2% of prefill" → −33%.** The original figure came from full
   offload with boost contamination. Measured clean at matched offload, MTP
   trades **−33% prefill for +48% decode**.
3. **A mechanism we published to ourselves and then disproved.** The throttling
   was first attributed to HIP's host↔device copies for CPU-resident layers.
   Building Vulkan with Clang killed that: it throttles identically with no such
   copies. The variable is the toolchain.
4. **One void cell**, kept in `raw/bench-vulkan-20261001.jsonl`: a rate computed
   from two generated tokens after the model hit EOS on a repetitive prompt.
   `ignore_eos` is mandatory for throughput cells; the void cell is retained
   rather than deleted so the hole in the method stays visible.

## Validity

- Final pass: **64 runs, 0 invalid** — every run asserts `n_prompt == 5201` and
  `n_pred == 128`.
- **Order controlled**: cells interleaved, two repetitions. Worst rep1-vs-rep2
  disagreement 2.8% (MTP, whose draft-acceptance rate is content-dependent); all
  others ≤1.2%.
- Every data point carries its GPU clock, package power, temperature and the top
  CPU process at that moment.
- Browsers killed and page cache dropped before the publication passes; two
  unscored warm-ups per cell so an mmap-based backend is not charged page-fault
  cost a copy-based one avoids.

## Files

| file | what |
|---|---|
| `raw/bench-loaded-*.jsonl` | **final pass** — 5201-token prompt, prefill + loaded decode, 4 cells × 2 reps × 8 runs |
| `raw/bench-pub-*.jsonl` | publication pass — short-prompt decode, 4 cells × 2 reps × 12 runs (its `pp_tps` is launch overhead, **not** prefill) |
| `raw/bench-matched-*.jsonl` | first matched comparison (boost-contaminated; superseded, kept for the corrections above) |
| `raw/bench-vulkan-*.jsonl` | Vulkan-only baseline incl. the void two-token cell |
| `raw/diag-rocm-*.jsonl`, `raw/diag-vulkan-*.jsonl` | throttle diagnosis: batch A / restart / batch B |
| `raw/*sample*.jsonl` | 2-second telemetry traces (clock, busy, temp, power, VRAM, GTT) |
| `bench-*.sh`, `build-*.sh` | the exact scripts, including the idle/warm-up/ordering logic |
| `ggufmeta.py` | reads GGUF KV metadata without loading the model |

## Model facts (from the GGUF header)

`context_length` **262144**, `block_count` 41 (40 + MTP layer), `embedding_length`
2048, `head_count` 16, **`head_count_kv` 2**, `expert_count` 256 /
`expert_used_count` 8. KV works out to ~40 KB/token, so the full 256k context is
~10.7 GB of KV on top of 17.26 GB of weights.
