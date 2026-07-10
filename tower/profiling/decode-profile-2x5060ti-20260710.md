# Where do the milliseconds go? Decode profiling on 2× RTX 5060 Ti

**Date:** 2026-07-10 · **Model:** Qwen3.6-27B AutoRound INT4 (hybrid linear-attention,
64 layers: 48 linear + 16 full attention, dense MLPs) · **Stack:** vLLM 0.21 +
Genesis patches, GPTQ-Marlin, TP=2 · **Hardware:** 2× RTX 5060 Ti 16GB (SM_120),
PCIe Gen5 x8 + Gen4 x4, no P2P, no NVLink

Question: on a budget dual-GPU consumer Blackwell box, what actually limits
single-stream decode — and where is optimization effort best spent?

## Method

Single-stream 600-token generations (temp 0.3, same prompts across arms),
2+ runs per configuration, all arms **without** speculative decoding except the
production row (so the parallelism/graph comparisons are clean). GPU utilization
sampled with `nvidia-smi dmon` at 1Hz during steady decode.

## Results

| Config | tok/s | vs control |
|---|---:|---|
| **Production** (TP=2 + CUDA graphs + MTP spec, 3 draft tokens) | **62.1** | +59% |
| A — control: TP=2 + CUDA graphs, no spec | 39.2 | — |
| B — PP=2 (pipeline instead of tensor parallel), no spec | 24.1 | −39% |
| C — TP=2 --enforce-eager (no CUDA graphs), no spec | 21.7–25.4* | −40% |

\* Eager mode also showed a reproducible pathology: the second consecutive request
ran at 7.2–7.3 tok/s (3× slower, prompt-deterministic, thermals/clocks normal).
Did not occur with CUDA graphs in any run. Unexplained; filed as a curiosity.

Steady-state utilization during TP=2 decode: **SM ~98%, memory controller ~72%,
PCIe ~250 MB/s per direction per card** (a few % of even the Gen4 x4 link).

## What this says

1. **Speculative decoding is the #1 software lever on this class of hardware.**
   MTP with 3 draft tokens takes 39 → 62 tok/s (+59%) at zero quality cost.
   If you tune one thing, tune this.

2. **CUDA graphs are #2 (+60–75% over eager).** With 128+ kernel launches per
   token on a 64-layer model, launch overhead is brutal on consumer parts —
   never run eager in production, and be suspicious of any benchmark that did.

3. **Tensor parallel beats pipeline parallel for single-stream, even over PCIe
   without P2P.** PP=2 decodes at one-GPU pace (the halves run sequentially at
   batch=1); TP=2 works both cards on every layer. The gap also quantifies the
   TP communication tax: ideal 2-way scaling from PP's sequential pace would be
   ~48 tok/s, measured 39 → **~20% of each token is lost to all-reduce latency**
   (NCCL through host RAM; consumer cards have no P2P). Real, but a fifth of
   the budget — not the villain.

4. **Decode here is compute-bound, not bandwidth-bound.** SM ~98% vs memory
   ~72% inverts the classic dense-decoder profile. The hybrid linear-attention
   architecture (48 of 64 layers do state updates rather than KV lookups)
   shifts the bottleneck to compute — meaning kernel tuning (Marlin configs,
   linear-attention kernels, fused ops) has headroom that "it's all bandwidth"
   folk wisdom says shouldn't exist. Notably, the Marlin per-SM tuning tables
   in this stack have **no entry for SM_120** — consumer Blackwell falls back
   to a generic heuristic.

5. **PCIe link width barely matters for 2-way TP decode.** ~250 MB/s of traffic
   fits comfortably in a Gen4 x4 slot; the cost of no-P2P all-reduce is latency
   per operation, not bandwidth. Don't buy a bigger motherboard for 2-GPU
   inference; the x4 second slot is fine.

## The controlled experiment: same model, different quant format

The strongest claim above — that the kernel path, not the model, explains most
performance gaps on consumer Blackwell — got a same-weights test: **Qwen3.6-27B
INT4 (AutoRound/GPTQ-Marlin) vs Qwen3.6-27B NVFP4 (ModelOpt)**. Identical
architecture, identical parameter count, only the quantization format differs.

| Config (same model, both TP=2) | tok/s |
|---|---:|
| INT4 → native Marlin + CUDA graphs + MTP spec (production) | **62.1** |
| INT4 → native Marlin + CUDA graphs, no spec | 39.2 |
| NVFP4 → Marlin FP4-emulation + CUDA graphs (GMU 0.85, 65K ctx), no spec | 23.2 |
| NVFP4 as previously deployed (eager, GMU 0.90, 131K ctx) | 8.8–15.7 |

What the NVFP4 path is up against on SM_120, per vLLM's own startup log:

> *"Your GPU does not have native support for FP4 computation but FP4
> quantization is being used. Weight-only FP4 compression will be used
> leveraging the Marlin kernel. This may degrade performance for
> compute-heavy workloads."*

And this workload is compute-heavy (SM ~98%). Consumer Blackwell has FP4
tensor cores on silicon, but vLLM's native FP4 GEMM targets datacenter
Blackwell (SM_100) — on SM_120 the NVFP4 checkpoint runs through Marlin
weight-only *emulation*, required a hand-patch (`marlin_utils_fp4.py`) to load
at all, needs a separate nightly vLLM build, and couldn't afford CUDA graphs
at its deployed memory settings (graph capture OOM'd at GMU 0.90 on 16GB).

**Findings:**
- **Kernel-path tax at matched settings: 1.7×** (39.2 vs 23.2 tok/s, same
  weights, same parallelism, both with graphs, no spec on either).
- **Stack-maturity tax compounds it to 4×+ as deployed** (62 vs ~16): the INT4
  path gets CUDA graphs at GMU 0.90 and MTP speculation for free; the NVFP4
  path gets neither out of the box.
- Incidental win: dropping eager for graphs at GMU 0.85/65K raised the NVFP4
  backend's best known config by **+48%** (15.7 → 23.2).
- The "genesis outperforms every other quant we tried" observation is
  explained: it's not the model, it's landing on the one quant format whose
  kernel is actually native on consumer Blackwell. **On SM_120 today, INT4
  GPTQ-Marlin is the format to publish; NVFP4 is a datacenter format wearing
  a consumer badge until native SM_120 FP4 GEMM lands.**

## The tuning sweep: a clean negative result

Following the compute-bound finding, we made the obvious kernel launch
parameters env-tunable (vLLM's FLA `fused_recurrent` decode kernel — hardcoded
`num_warps=1, num_stages=3`, no autotune, runs 48 layers × every token;
`fused_sigmoid_gating` — `num_warps=4`; and Marlin's `USE_FP32_REDUCE_DEFAULT`)
and swept them end-to-end on the live model. Nine arms, fresh server load per
arm, 2×600-token benches each, baseline reproduced first (39.4 vs 39.2 the
day before — patched files behaviorally identical at defaults).

| Arm | tok/s |
|---|---:|
| baseline (warps=1, stages=3, gating=4, fp32_reduce=on) | 39.4 |
| FLA num_warps = 2 / 4 / 8 | 39.5 / 39.5 / 39.5 |
| FLA num_stages = 4 | 39.4 |
| FLA num_stages = 2 | 17.3 (unstable — 9.3 then 25.3; regression, not noise) |
| gating num_warps = 2 / 8 | 39.4 / 39.4 |
| Marlin fp32_reduce = off | 39.4 |

**Every Python-reachable launch config is flat.** The FLA authors' choices are
already right (or irrelevant) at decode shapes on SM_120, and Marlin's FP32
epilogue is free here. Two implications worth more than a positive result:

1. **Triton launch-config tuning is not where consumer-Blackwell milliseconds
   live** for this model class. The remaining decode time sits in the Marlin
   GEMM's C++ inner loop (thread-shape heuristic not reachable from Python),
   the all-reduce, and per-token kernel count — graph-level, not launch-level.
2. **The "compute-bound" reading needs a caveat we now understand:** NCCL's
   no-P2P all-reduce spin-waits on SM, inflating SM utilization. Part of the
   98% SM figure is communication wearing a compute costume. This moves the
   P2P/all-reduce project up the priority list and demotes kernel micro-tuning.

(The env hooks stay in the stack — zero cost at defaults, and they make the
next sweep a config change instead of a code patch.)

## Sizing the all-reduce prize directly (NCCL microbench)

Before considering any driver-level P2P work, we measured what a single all-reduce
actually costs on the current (no-P2P) path, at genesis's real TP=2 message shapes.
torch+NCCL, 2 ranks (one per GPU), 500 timed ops after warmup, current stock driver.

| Shape (msg = tokens × 5120 × bf16) | msg bytes | per-op latency | busbw |
|---|---:|---:|---:|
| decode b1 | 10 KB | **25.3 µs** | 0.41 GB/s |
| decode+MTP b4 | 40 KB | 29.5 µs | 1.39 GB/s |
| prefill 128 | 1.3 MB | 387 µs | 3.39 GB/s |
| prefill 512 | 5.2 MB | 1492 µs | 3.51 GB/s |
| prefill 2048 | 21 MB | 5783 µs | 3.63 GB/s |

**Decode is pure latency, not bandwidth** — a 10 KB all-reduce moves at 0.41 GB/s
because the 25 µs is almost all fixed overhead (host round-trip + kernel launch),
not transfer time. That is precisely the regime P2P attacks.

**Prize, quantified:** genesis does ~128 all-reduces per token (64 layers × 2).
At 25.3 µs that's **3.23 ms per token — 20.1% of the 16.1 ms token budget** at
62 tok/s. This independently confirms the ~20% figure the TP-vs-PP comparison
inferred. 20% is the *ceiling* (all-reduce made free); P2P recovers a fraction.

**Two findings that decide the driver question:**

1. **`NCCL_P2P_DISABLE=1` (production) vs `=0` are identical** — 25.3 vs 24.7 µs,
   within noise. NCCL *already cannot* use GPU-to-GPU P2P on these consumer cards;
   the config flag is a no-op because the driver blocks peer access
   (`torch.cuda.can_device_access_peer(0,1) == False`). Both paths stage through
   host shared memory. This is the mechanism the tinygrad patch would change.

2. **The real prize isn't "faster NCCL" — it's unlocking vLLM's own custom
   all-reduce.** genesis runs with `--disable-custom-all-reduce` *because* peer
   access is False. vLLM ships a one-shot GPU-side all-reduce kernel (no host hop,
   no NCCL launch) that for a 10 KB message would run in single-digit µs vs 25 —
   but it requires P2P. So the driver patch would flip `can_access_peer → True`,
   which both drops NCCL latency *and* re-enables the custom kernel path.
   Realistic recovery ≈ 60–70% of the 3.23 ms → **~12–14% throughput**
   (genesis no-spec 39 → ~44; with MTP 62 → ~70). Meaningful, not transformative,
   and bounded above by the 20% ceiling.

**Verdict:** the prize is real (~10–15%) and now has a hard number, but the
delivery cost is a hand-ported cross-major-version driver (tinygrad's newest P2P
branch is 570; we're pinned to 580 by CUDA 13), with a silent-memory-corruption
failure mode, installed via a sudo + module-reload/reboot on the production box.
That is a scheduled-maintenance-window decision, not a config tweak — correctly
gated on a human with console access. The measurement did its job: we know the
payout before betting the table.

## Where effort goes next (ranked by measured headroom)

1. **All-reduce latency (~20% of token budget, and part of the SM figure is
   NCCL spin):** P2P enablement experiments, fewer/fused sync points, or
   quantized all-reduce. Post-sweep, this is the clear #1.
2. **Marlin C++ thread-shape heuristic for SM_120:** the only kernel-tuning
   surface left after the launch-config sweep came back flat — requires
   rebuilding the extension, real CUDA work, bounded upside (mem ~72%).
3. **Spec decoding tuning:** draft-token count and acceptance monitoring —
   cheapest wins, partially exhausted (prod already runs MTP=3).
4. Eager-mode second-request pathology: worth a bug report upstream.
5. ~~Triton launch-config tuning~~ — ruled out empirically (see sweep above).
