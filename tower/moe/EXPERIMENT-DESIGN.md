# MoE live test — experiment design

Companion to [README.md](README.md) (the pre-test literature research). This is
the actual test plan for when the session runs. Every phase uses
[tower-experiment-lock.py](../experiment-mode.md), not manual systemctl —
that tool already does the safe teardown/restore dance (mask service, force
proxy to openrouter, verify GPU clear) that was done by hand, repeatedly,
during today's dense-model testing.

**Design principles, enforced by tonight's own case-law additions:**
- Report each model on its own terms first. No comparison table introduces
  genesis's numbers until the explicit final synthesis step.
- One variable per test. Don't mix a new quant format, a new offload split,
  and a new quality check into a single run — isolate, like the prefix-cache
  cold/warm/control test.
- Speed AND quality, every time. Reuse the 15-scenario domain-suite rubric
  (`~/model-eval/domain-suite.json`) — a tok/s number alone doesn't answer
  whether offloading or quantization silently cost quality.
- If a research assumption doesn't hold in live testing, that's a finding —
  write it down, don't quietly correct and move on.
- **Check `~/inference-research/tower/` for an existing program on this exact
  model before adding it to the plan.** Missed for Nemotron on the first
  pass (2026-07-14) — a full research program already existed for it, with a
  proven-faster answer sitting right there, and it got planned as a fresh
  risky test anyway. Fixed in Phase 5 below; don't repeat the miss on the
  remaining candidates.

## Phase 0 — Pre-flight smoke test (run 2026-07-14, see live-testing-notes.md)

**Status: run.** Loaded `Qwen3-30B-A3B-NVFP4` on the 0.25.0 vLLM build. The
targeted question resolved clean: the confirmed SM120 NVFP4-MoE
FlashInfer-CUTLASS dispatch error is fixed in this build (kernels selected,
weights loaded in 32s, no crash). Worth knowing this model has an *older*,
separate, already-resolved failure on record too: a 2026-05-16 model-eval
run (`campaigns-2026-04-05/model-eval-2026-05-16.tsv`) failed this exact
model outright because NVFP4 needed CUDA≥12.9 and the box was on 12.8 at the
time — we're on CUDA 13.0 now, so that blocker is confirmed gone, not just
assumed gone. What Phase 0 found instead was a new problem: a post-load
TP/EP synchronization stall, not predicted by either the 2026-07-13 research
or the 2026-05-16 eval. Unblocks Phase 3.

## Phase 1 — Confirmation run, not fresh discovery: Qwen3-30B-A3B-GPTQ-Int4 (16G, vLLM)

**Status: run 2026-07-14.** 41.66-42.41 t/s (confirms archive). Quality
2.67/5 — worse than both dense models, specific confident-but-wrong error
pattern. See live-testing-notes.md.

**Correction (2026-07-14):** not an unknown either. The same 2026-05-16
model-eval sweep already measured this model: **41.33 tok/s median** (tight:
41.01-41.38 across runs), -43.7% vs. the genesis-class baseline of the day.
Real, usable number — about 2.6x nvidia-27B's no-MTP speed from 2026-07-13,
just well short of genesis. One thing worth carrying forward: the *first*
attempt at this exact model failed to come up healthy at all before a
working config was found (root cause not in the TSV, config file likely
gone) — so don't be surprised if the first launch attempt needs a retry:
that's already-observed behavior for this checkpoint, not a new red flag if
it happens again. This phase is a confirmation run (does 41.33 t/s still
hold, does it still need a retry to come up clean) plus the domain-suite
quality check research never covered, not first discovery. Still the
cleanest checkpoint-size test of whether the RAM-ceiling finding generalizes
to MoE — that specific question is still open.

## Phase 2 — Establish the offload lever: Qwen3-30B-A3B-Q3_K_M.gguf (14G, llama.cpp)

**Status: run 2026-07-14.** Curve: N=0→121.5 t/s, N=8→68.4, N=16→55.2,
N=24→50.0. Fastest MoE result of the session, beats genesis outright. Quality
at N=0: 1.87/5 — *worse* than Phase 1's GPTQ run despite the speed win, same
error pattern reproduces. First inversion of the whole session: fastest
config is also the worst-scoring one. See live-testing-notes.md.

The core new capability from research: sweep `--n-cpu-moe` across several
split points (e.g. 0 layers offloaded / light / moderate / heavy) on the
same model, holding everything else constant. Measure tok/s at each point to
characterize the actual speed-vs-VRAM curve on this hardware — the research
found the offload mechanism is real and mature, but found zero verified
numbers for this hardware class. This phase produces those numbers. Run the
domain-suite check at the offload split that looks best, to confirm CPU
offload isn't silently degrading output (a real risk if numerics differ
across the CPU/GPU boundary).

## Phase 3 — Second vLLM candidate, same model family: Qwen3-30B-A3B-NVFP4 (17G, vLLM)

**Status: run 2026-07-14, root cause found, speed/quality question still
open.** The Phase 0 "TP/EP stall" was misdiagnosed twice (NCCL P2P and
expert-parallel both refuted). Actual cause: uncapped FlashInfer JIT compile
storm (91 concurrent nvcc/cicc/ptxas, no AOT kernel for `fused_moe_120` on
SM120+fp8_uint4) drove the box into real RAM/swap thrashing. New case-law
entry filed. This quant-recipe-vs-GPTQ question is unresolved, not
answered — needs a retest with `MAX_JOBS` capped in the launch script and
budget for the one-time JIT compile. See live-testing-notes.md.

Same total/active params as Phase 1's GPTQ-Int4, different quantization
recipe. Gated by Phase 0's smoke test. This isolates a clean question: does
quantization recipe matter for MoE speed/quality the way it clearly did for
dense models today (genesis's INT4+MTP vs nvidia-27B's NVFP4 W4A16), or does
MoE's sparse activation make the quant-format choice matter less? That's a
genuinely new comparison — same architecture class, controlled for
everything except the quant recipe.

## Phase 4 — Load-safety re-check (not a speed re-run): Qwen3.6-35B-A3B-UD-Q4_K_M.gguf (21G, llama.cpp)

**Status: run 2026-07-14.** Loaded clean in 42s, no wedge (RAM never below
5.6GB free). Speed confirmed: 100.54 t/s. Quality: 2.87/5, but 10/15
responses truncated at max_tokens=1600 — real confound, fixed for later
phases by raising to 3000. traf1/traf4 reproduce, rest5 doesn't. See
live-testing-notes.md.

**Correction (2026-07-14):** this wasn't a one-off April number — a full
20-iteration autoresearch sweep already ran on this exact checkpoint
(`~/inference-research/tower/campaigns-2026-04-05/autoresearch-qwen36moe-log.md`),
found **100.24 tok/s, 0/22 experiments beat the baseline config** (already
optimal: `ctk/ctv=f16, ubatch=4096, batch=2048, threads=8, split=layer`),
and saved the winning flags to `~/inference-research/current-best-flags-qwen36moe.sh`.
**Don't re-run the speed sweep — it already happened and found nothing to
improve.** What this phase actually needs to check, since it's above the
18G wedge threshold and the sweep predates the RAM-ceiling finding: does the
proven-best config still *load* safely under current knowledge (external
ping monitor during load, predefined abort criteria)? That's a load-safety
question, not a speed question — the speed answer is already on file.

There's also a 131K-context variant already benchmarked
(`autoresearch-qwen36moe-131k-log.md`) — check it before assuming 131K
context needs fresh discovery too.

## Phase 5 — Confirm the known-good non-Qwen result: Nemotron-3-Nano-30B-A3B, llama.cpp Q4_K_M

**Status: run 2026-07-14.** Loaded clean (~2min, largest checkpoint tested
at 24.65GB, no thrash). Speed confirmed: 123.4 t/s. Quality: 2.80/5, flat
across domains. traf1/traf4 reproduce on a non-Qwen base model — first
evidence this is a model-size-class issue, not per-family. See
live-testing-notes.md.

**Correction (2026-07-14):** this was originally the NVFP4/vLLM path for
Nemotron, flagged as the riskiest phase in the plan. That was a miss —
`~/inference-research/tower/nemotron/` already proved the NVFP4/vLLM path is
a dead end for this model (89% Mamba/SSM layers can't be TP-sharded; a
2026-05-21 TRT-LLM attempt OOM'd even with official sharding config) and
already found the actual winner: **llama.cpp Q4_K_M, all layers on GPU,
117-123 t/s** — faster than genesis, 100% tool-calling pass validated
2026-05-28. No new risk here, no new test needed — this phase is just
re-running the proven command (`nemotron-shootout-results.md`) to confirm it
still holds under current conditions (RAM/VRAM state may have drifted since
May) and to fold a real non-Qwen data point into the final comparison
without inventing a new failure mode to chase.

## Phase 6 — Different size class: GPT-OSS-20B (needs acquiring first — not yet on disk)

**Status: run 2026-07-14.** Acquired `ggml-org/gpt-oss-20b-GGUF` native
MXFP4 (12.1GB). Speed: 133.05 t/s — fastest clean result of the session.
Quality: 2.20/5. traf1/traf4 reproduce a third time, more explicitly than
ever (flatly asserts the roundabout is rail-crossing-"independent"); also
surfaced a genuinely unsafe food-safety answer (rest3). Confirms the pattern
across three unrelated base-model families. ktransformers not attempted —
llama.cpp's native-MXFP4 path already worked cleanly, no unmet need to
chase it. See live-testing-notes.md.

Natively MXFP4-quantized, smallest total-param candidate (20B vs the 30-35B
of everything else) — a genuinely different axis: does a smaller-total MoE
trade quality for a bigger speed win than the 30B-class models get from
offloading? Also the natural ktransformers test subject if it turns out to
install/run on SM120 at all (open question from research) — worth a `pip
install`-and-see attempt here rather than earlier, since this is the model
the ktransformers community actually targets.

## Phase 7 — Custom-patch justification (only after 1-6 produce real profiles)

Resolves the research's other empty gap: does a specific, reproducible
bottleneck show up anywhere in phases 1-6 that would justify writing a
custom patch, the way genesis's 60+ patches were justified by measured
problems? Don't patch speculatively — only pursue this if a wall actually
shows up in the data above.

## Final synthesis (after all phases)

Only here does genesis enter any comparison table — against whichever MoE
candidate(s) actually performed best on their own terms, not against all six
individually. This is the explicit, asked-for comparison step tonight's
case-law entry says to keep separate from each model's own characterization.
