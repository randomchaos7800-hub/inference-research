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

## Phase 0 — Pre-flight smoke test (cheap, resolves a gating question)

Load `Qwen3-30B-A3B-NVFP4` on the current 0.25.0 vLLM build just long enough
to see whether it throws the confirmed SM120 NVFP4-MoE FlashInfer-CUTLASS
error (`does not support the deployment configuration`). This was fixed
upstream and cherry-picked to v0.15.1 — resolves whether that fix is present
in our build before Phase 3 depends on it. Fast, low-risk (small checkpoint,
immediate abort if the known error appears).

## Phase 1 — Safest baseline: Qwen3-30B-A3B-GPTQ-Int4 (16G, vLLM)

Smallest checkpoint, safely under the 18G wedge line, same quant family
(INT4) as genesis's own dense model — the cleanest possible same-format
dense-vs-MoE comparison exists here, but don't run it yet; just establish
this model's own numbers first (single-stream tok/s, domain-suite score).
This phase also answers the first open empirical question: does the RAM-ceiling
finding (checkpoint size on disk, not final VRAM, is what wedges the box)
apply to MoE checkpoints the same way it did to dense ones today? A clean
16G load with no drama is the expected/hoped-for result — note if it isn't.

## Phase 2 — Establish the offload lever: Qwen3-30B-A3B-Q3_K_M.gguf (14G, llama.cpp)

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

Same total/active params as Phase 1's GPTQ-Int4, different quantization
recipe. Gated by Phase 0's smoke test. This isolates a clean question: does
quantization recipe matter for MoE speed/quality the way it clearly did for
dense models today (genesis's INT4+MTP vs nvidia-27B's NVFP4 W4A16), or does
MoE's sparse activation make the quant-format choice matter less? That's a
genuinely new comparison — same architecture class, controlled for
everything except the quant recipe.

## Phase 4 — Re-verify the April result: Qwen3.6-35B-A3B-UD-Q4_K_M.gguf (21G, llama.cpp)

Above the 18G threshold — treat with today's caution (external ping monitor
during load, predefined abort criteria, same as the risky dense-model loads
today). This checkpoint got ~100 t/s once, back in April, before the
RAM-ceiling finding existed — that number needs re-verification under
current knowledge, not blind trust. Also test whether `--n-cpu-moe` offload
reduces the *load-time* host-RAM spike, not just runtime VRAM — the research
didn't answer whether expert offloading helps the RAM-ceiling wedge risk
itself, and this is the best-sized candidate to find out.

## Phase 5 — Riskiest candidate: Nemotron-3-Nano-30B-A3B-NVFP4 (19G, vLLM)

Right at/over the wedge line, single model, heaviest monitoring of the whole
plan (predefined abort criteria, ping-based wedge detection like today's
compile-storm incident). Also the only non-Qwen model family in the set —
broadens the test beyond one architecture. Run this last and alone, not
stacked with any other new variable.

## Phase 6 — Different size class: GPT-OSS-20B (needs acquiring first — not yet on disk)

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
