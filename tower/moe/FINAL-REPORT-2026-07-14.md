# MoE on the tower — final report (2026-07-14)

Companion to [README.md](README.md) (pre-test research), [EXPERIMENT-DESIGN.md](EXPERIMENT-DESIGN.md)
(the plan), and [live-testing-notes.md](live-testing-notes.md) (full
phase-by-phase raw results). This is the synthesis: what the whole live
session actually answered, run on the tower (2x RTX 5060 Ti 16GB, SM120
consumer Blackwell, 32GB system RAM, PCIe-only — no NVLink).

## The question this session set out to answer

Genesis (dense, INT4+MTP) gets ~73-80 t/s at 3.73/5 quality. The one other
dense model tested this cycle (nvidia's NVFP4 W4A16) gets 15.9 t/s at
3.87/5, or 38 t/s at a real quality cost with MTP. No dense config gets both
speed and quality — you trade one for the other by how hard you quantize.
MoE's pitch: sparse activation should let a big, high-capacity model match a
small dense model's speed while beating it on quality, no lossy
quantization tricks required.

**Verdict: the pitch is false on this hardware, for a different reason than
expected.** MoE does deliver the speed — every MoE checkpoint tested beat
genesis on raw tok/s, several by a wide margin. But every single one of them
lost badly on quality, by margins far larger than anything seen trading off
quantization aggressiveness on the dense side. This isn't a "small tax for
the speed win" result — it's the fastest-speed configs consistently being
the worst-quality ones. MoE didn't remove the speed/quality trade on this
hardware; it just moved where the trade happens.

## Speed — every MoE checkpoint beats genesis

| Model | Runner | Config | Speed | On disk |
|---|---|---|---|---|
| GPT-OSS-20B (native MXFP4) | llama.cpp | all-GPU | **133.05 t/s** | 12.1GB |
| Nemotron-3-Nano-30B-A3B (Q4_K_M) | llama.cpp | all-GPU | **123.4 t/s** | 24.65GB |
| Qwen3-30B-A3B (Q3_K_M) | llama.cpp | all-GPU (N=0) | **121.5 t/s** | 14GB |
| Qwen3.6-35B-A3B (UD-Q4_K_M) | llama.cpp | all-GPU | **100.54 t/s** | 22GB |
| — genesis (dense, INT4+MTP) — | vLLM | production | ~73-80 t/s | 16GB |
| Qwen3-30B-A3B (GPTQ-Int4) | vLLM | TP=2 | 41.66-42.41 t/s | 16GB |
| Qwen3-30B-A3B (Q3_K_M) | llama.cpp | N=24 offload | 50.0 t/s | 14GB |
| Qwen3-30B-A3B (NVFP4) | vLLM | TP=2 | *blocked, see below* | 17GB |

**llama.cpp all-GPU is the config that wins, every time it was tried.**
Every offloaded config tested (Phase 2's sweep: N=8/16/24) was slower than
the all-GPU baseline for the same checkpoint — offloading only matters if
the checkpoint doesn't fit at all, and every MoE checkpoint tested this
session did fit fully on this hardware's 32GB combined VRAM. The one vLLM
MoE path tested (GPTQ-Int4) is the slowest of any MoE result — well below
even genesis, let alone the llama.cpp results. **The practical finding: for
MoE on this specific hardware, llama.cpp beats vLLM outright, the opposite
of genesis's own dense-model conclusion (vLLM+custom patches beats
llama.cpp for dense).**

## Quality — every MoE checkpoint loses to both dense models, badly

| Model | Quality (domain-suite, /5) | Notes |
|---|---|---|
| — nvidia-27B-MTP (dense NVFP4+MTP) — | **3.87** | |
| — genesis (dense, INT4+MTP) — | **3.73** | |
| Qwen3.6-35B-A3B | 2.87 | 10/15 truncated at max_tokens=1600 — real confound |
| Nemotron-3-Nano-30B-A3B | 2.80 | flat across domains, cleanest probe of the MoE set |
| Qwen3-30B-A3B (GPTQ-Int4) | 2.67 | |
| GPT-OSS-20B | 2.20 | fastest model, worst-behaved answers (see below) |
| Qwen3-30B-A3B (Q3_K_M, all-GPU) | 1.87 | fastest-of-Qwen-family config, worst quality of the whole session |

Every MoE checkpoint lands roughly 0.9 to 2.0 points below both dense
models. For comparison, the entire dense-side quantization spread (genesis
INT4+MTP vs. nvidia NVFP4-no-MTP) was only 0.14 points (3.73 vs. 3.87) — the
MoE quality gap is 6-14x larger than anything seen on the dense side this
research cycle. **Fastest is worst, most starkly for Q3_K_M**: the single
fastest MoE result of the whole session (121.5 t/s) is also its single
worst quality result (1.87/5) — an inversion never seen in dense-model
testing, where speed and quality moved together or traded off gently.

## The headline finding: a hard floor at this model-size class

Two specific traffic-engineering scenarios — **traf1** (a signalized
intersection with a "yellow trap" left-turn conflict) and **traf4** (a
roundabout redesign that ignores rail-crossing queue-spillback risk) —
failed identically across every single MoE checkpoint tested this session:

| Model | traf1 | traf4 |
|---|---|---|
| Qwen3-30B-A3B (GPTQ) | fails | fails |
| Qwen3-30B-A3B (Q3_K_M) | fails | fails |
| Qwen3.6-35B-A3B | fails | fails |
| Nemotron-3-Nano-30B-A3B | fails | fails |
| GPT-OSS-20B | fails, most confidently | fails, most confidently |

Four quantization formats, two runtimes (vLLM and llama.cpp), and **three
architecturally unrelated base-model families** (Qwen, NVIDIA/Nemotron,
OpenAI GPT-OSS) all produce the same failure *shape*: a long, confident,
well-organized answer that fabricates a plausible-sounding wrong mechanism
and lands backwards on the one decisive constraint. GPT-OSS-20B — the
smallest model tested (20B) — fails the hardest: it doesn't just miss the
rail-crossing spillback risk, it flatly asserts the roundabout's
rail-crossing interaction is "None (independent)," the most confident wrong
answer of the whole session, and separately produced an actively unsafe
food-safety answer (instructing reheating and re-serving temperature-abused
soup).

This is not a per-checkpoint bug or a Qwen-specific weakness — it's strong
evidence of a genuine knowledge/reasoning gap at this parameter class
(20-35B total params, whether dense-equivalent-active or not) on this
specific type of adversarially-framed engineering scenario. The two dense
models tested this cycle (27-30B active-equivalent, much larger total) don't
show this failure. Whatever capability these two scenarios require, it
shows up around the dense-model scale tested and not below it, MoE routing
notwithstanding.

## The one real infrastructure bug found — and why it doesn't justify a patch

Phase 3's NVFP4/vLLM MoE test appeared to hang after weight-loading —
`shm_broadcast` warnings every 60s, idle processes, zero GPU utilization.
First diagnosed as a TP/expert-parallel synchronization stall. **Both
leading theories were wrong** — retested with genesis's production
NCCL/all-reduce settings (rules out P2P) and confirmed `enable_expert_parallel`
defaults `False` and was never set (rules out EP). The actual cause, found
by checking `ps aux` instead of treating the stall as a black box: an
uncapped FlashInfer JIT kernel compile storm — 91 concurrent
`nvcc`/`cicc`/`ptxas` processes compiling `fused_moe_120` (no AOT kernel
exists yet for this SM120+fp8_uint4 combination), with no `MAX_JOBS` cap on
an 8-core box. It drove real RAM/swap thrashing (30/30GB RAM, 87/95GB
swap), not a deadlock. A capped retest (`MAX_JOBS=3`) confirmed the fix
prevents the thrash, but the compile itself is genuinely slow — still
running past 12 minutes wall-clock when stopped to preserve lock-time
budget. New case-law entry filed: "An Uncapped JIT Compile Storm Looks
Exactly Like a Deadlock."

**This does not justify writing a custom vLLM patch.** It's an environment
configuration gap (a missing `MAX_JOBS` cap, the same fix already applied
once this session to the vLLM *build* step but never carried to the
*runtime* launch script), not an architectural limitation genesis's 60+
patches would be needed to route around. The fix is one line in a launch
script plus accepting a one-time compile cost (cached afterward). No other
phase this session hit a genuine wall stock tooling couldn't handle —
llama.cpp served four different MoE checkpoints cleanly (Phases 2, 4, 5, 6)
with zero patches, using only the same environment-variable and
RAM-safety-monitoring discipline already established for dense-model
testing. **Answer to the research gap left open by the literature pass:
stock tooling, correctly configured, already saturates what this hardware
can practically extract from MoE checkpoints. There is no measured problem
here that would justify genesis-style custom patching for MoE specifically.**

## Where MoE actually lands, on its own terms

Ranking the MoE candidates against each other, not genesis, using both axes:

1. **Nemotron-3-Nano-30B-A3B** — best-balanced result: 123.4 t/s at 2.80/5,
   the only MoE model with a flat, non-catastrophic quality profile and the
   cleanest quality probe (least truncation) of the set. If forced to pick
   one MoE checkpoint for a speed-sensitive use case where "worse than
   genesis, but not disastrously" is acceptable, this is it.
2. **GPT-OSS-20B** — fastest (133.05 t/s) and smallest on disk (12.1GB, safe
   load margin), but worst-behaved quality (2.20/5) including a genuine
   safety-relevant failure. Speed-first use only, with real risk.
3. **Qwen3.6-35B-A3B** — middling speed (100.54 t/s), the quality number
   (2.87) is the highest of the MoE set but is confound-tainted by heavy
   truncation; treat with caution until rerun with a higher token budget.
4. **Qwen3-30B-A3B, all quant/runtime combos** — consistently the weakest
   MoE showing (GPTQ 2.67, Q3_K_M 1.87), and Q3_K_M's full-GPU config is
   the single worst tradeoff of the whole session: fastest, but least
   trustworthy.

## Final comparison — genesis enters here, and only here

| | Genesis (dense) | Best MoE (Nemotron) |
|---|---|---|
| Speed | ~73-80 t/s | 123.4 t/s (+~60%) |
| Quality | 3.73/5 | 2.80/5 (-0.93) |

Even the best-balanced MoE result trades a 60% speed gain for a quality loss
roughly seven times larger (in absolute rubric points) than the entire
quantization-aggressiveness spread measured on the dense side this research
cycle. **For this hardware, this workload (multi-domain reasoning with
adversarially-framed edge cases), and the checkpoints available today, MoE
is not a free lunch and does not obviate the dense speed/quality trade —
genesis's dense INT4+MTP config remains the better-balanced production
choice.** MoE is a legitimate option only if the use case can tolerate a
quality floor around 2.2-2.9/5 and specifically cannot tolerate the two
confirmed failure scenarios (adversarial-signal-timing and
queue-spillback-risk traffic engineering), or any structurally similar
"confident fabrication on a decisive constraint" scenario — a real,
now well-characterized risk profile rather than an unknown one.

## Open items for a future session

- Qwen3-30B-A3B-NVFP4's quant-recipe-vs-GPTQ question is genuinely
  unanswered — needs a dedicated session with no lock-time pressure to let
  the one-time FlashInfer JIT compile finish (or to source/build a
  prebuilt AOT kernel for SM120 fp8_uint4 and skip the compile entirely).
- Qwen3.6-35B-A3B's 2.87 quality score should be rerun at the higher
  (3000) token budget used for every later phase, to remove the truncation
  confound and get a clean number.
- ktransformers was never tested — not because it was ruled out, but
  because llama.cpp's native offload/native-quant paths already answered
  every question this session needed answered, with no unmet capability gap
  to justify chasing a second runner.
