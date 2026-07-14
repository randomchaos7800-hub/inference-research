# MoE playbook — pre-test research

**Status: literature review only. No live benchmarks run yet.** This is the prep
document for a future test session on the tower (2× RTX 5060 Ti 16GB, SM_120
consumer Blackwell, 32GB system RAM). Run under [experiment-mode.md](../experiment-mode.md)
when the session happens: production stopped and disabled, VRAM drained and
verified, one variable at a time — same discipline as every other program here.

Built via a 102-agent adversarially-verified research pass (20 sources fetched,
98 claims extracted, 25 claims put through 3-vote verification, 13 killed).
Full methodology and raw claim votes: see `sources.md` in this directory.

## The question

Genesis (dense, INT4 AutoRound + MTP) gets ~73 t/s. The one other dense model
tested this hardware cycle (nvidia's W4A16 NVFP4) only manages 15.9 t/s without
speculative decoding, or 38 t/s with MTP at a real, measured quality cost
(-0.27 on our own rubric). No dense config found gets both speed and quality —
you trade one for the other via how aggressively you quantize.

MoE's pitch is that you don't have to make that trade: a small slice of active
parameters per token gives you decode speed independent of total model size,
so a big, high-capacity MoE model could in theory match a small dense model's
speed while beating it on quality — no lossy quantization tricks required.

**Verdict: partially true, not a free lunch.** Sparse activation itself is
real and measured — under 5% of experts activate per request on ~100-expert
models, ~25% on Mixtral's 8. That's the genuine empirical seed of the pitch.
But the resulting speed advantage is hardware-dependent and **erodes under
memory/bandwidth pressure** — worse on more memory-constrained devices — and
the offloading techniques used to fit big MoE models onto constrained hardware
trade real, measured latency (2.6x in one benchmark) for the capacity win.
Confidence: high on both halves of this claim (3-0 verification on primary
sources).

## What's actually confirmed

**llama.cpp has the most mature tooling for this exact hardware's constraint
profile.** Two mechanisms, both verified against llama.cpp's own upstream PRs:

- `-ot "exps=CPU"` (`--override-tensor`, PR #11397) — regex-based pin of
  routed-expert FFN tensors (`ffn_gate_exps`, `ffn_up_exps`, `ffn_down_exps`)
  to CPU/system RAM, while attention, dense FFN, and shared-expert FFN stay
  on GPU every step.
- `--n-cpu-moe N` / `--cpu-moe` (PR #15077) — simplified convenience flag,
  offloads the first N layers' MoE weights to CPU without hand-written regex.
  Official server docs: *"keep the Mixture of Experts (MoE) weights of the
  first N layers in the CPU."*

This is the single most robustly corroborated finding in the whole pass — six
overlapping claims, five voted 3-0, one 2-1, all pointing at the identical
mechanism from independent sources. **This is the concrete lever for the live
session**: tune the GPU/CPU split directly against the VRAM budget, and it
directly addresses the 32GB system-RAM ceiling since it controls how much of
the checkpoint needs to be RAM-resident at once.

**vLLM has at least one confirmed SM120-specific MoE kernel gap.** The NVFP4
MoE FlashInfer-CUTLASS backend's device-capability check only recognized
SM9.0 (Hopper) and SM10.x (datacenter Blackwell) — not SM12.0 (the 5060 Ti's
compute capability) — causing a hard failure instead of a graceful fallback
(GitHub issue #33416, PR #33417, verified 3-0). **This was fixed and
cherry-picked to v0.15.1** — before assuming this still breaks on our built
0.25.0, smoke-test it directly: load an NVFP4 MoE model and watch for the
exact string `does not support the deployment configuration`. Several broader
claims trying to characterize vLLM's overall SM120 MoE maturity beyond this
one narrow bug were all rejected on verification — the honest state is "this
specific bug existed and was fixed," not "vLLM's MoE support on consumer
Blackwell is generally rough" or "generally fine."

**ktransformers is a legitimate second runner to evaluate, compatibility
unknown.** NUMA-aware hot/cold expert placement (frequent experts pinned GPU,
infrequent on CPU, dynamic reassignment from routing stats), validated in a
SOSP'25 paper, real runtime flags (`--kt-num-gpu-experts`,
`--kt-expert-placement-strategy`). But whether it runs on SM120 consumer
Blackwell at all is genuinely unestablished — a claim asserting it doesn't
support Blackwell was itself rejected (0-3) — and its NUMA design targets
were dual-socket servers, not this single-socket MSI Z890 board. **Needs
direct testing, not more literature review**, on both counts.

## What came back empty — the two real gaps

The research explicitly could not answer two of the four original questions.
Every claim that attempted to answer them was rejected on verification. This
is a genuine literature gap, not an omission:

1. **Does custom vLLM patching (the ~60-patch effort behind genesis) add real
   value for MoE specifically, or does stock tooling already saturate
   achievable throughput?** No surviving evidence either way. Recommended
   approach: profile stock vLLM/llama.cpp MoE throughput first in the live
   session; only invest in patches if a specific, reproducible bottleneck
   shows up — mirror how genesis's patches were justified by measured
   problems, not assumed need.

2. **Which specific MoE model is the best fit for this exact hardware?** No
   verified hardware-matched benchmark survived for any model on hardware
   resembling this rig. Two attempts were rejected: an RTX 3060 Qwen3.6-35B-A3B
   GGUF number (33-36 t/s claim, rejected 0-3) and a Qwen3-235B-A22B
   selective-offload claim (rejected 1-2). **This has to be settled by
   benchmarking, not read off a blog post.**

## Model candidates for the live session

Already on disk, all structurally within the safe load zone *if* the RAM-ceiling
finding from today's dense-model testing generalizes to MoE checkpoints the
same way — this is an inference from that finding, not a verified MoE-specific
result, and should be treated as a hypothesis to test, not a given:

| Model | Size on disk | Format | Runner |
|---|---|---|---|
| Qwen3-30B-A3B-GPTQ-Int4 | 16G | safetensors | vLLM |
| Qwen3-30B-A3B-NVFP4 | 17G | safetensors | vLLM |
| Nemotron-3-Nano-30B-A3B-NVFP4 | 19G | safetensors | vLLM (right at/over the ~18G wedge line — treat as risky) |
| Qwen3-30B-A3B-Q3_K_M.gguf | 14G | GGUF | llama.cpp |
| Qwen3.6-35B-A3B-UD-Q4_K_M.gguf | 21G | GGUF | llama.cpp (already got ~100 t/s once, back in April, before the RAM-ceiling finding existed — don't assume that holds without re-verifying) |

A sixth worth acquiring: **GPT-OSS-20B**, natively MXFP4-quantized, real and
well-regarded, came up repeatedly in research as a common CPU-offload test
subject. Its specific throughput claim from this research pass (319-424 t/s
on an RTX 5090) was rejected on verification — don't cite that number — but
the model itself and its native MXFP4 format are real and worth having in
the candidate pool.

## Citation hygiene

- The MoE-Infinity offloading-tradeoff paper is commonly cited as
  arXiv:2505.11415 — **that ID is a withdrawn duplicate submission.** The
  canonical, peer-reviewed version with identical data is **arXiv:2412.07067**
  (NeurIPS 2025 Datasets & Benchmarks Track). Use that ID going forward.
- The OLMoE memory-erosion study (arXiv:2606.21428) is very recent and
  self-limits its scope to one model (OLMoE) on two devices (a laptop and an
  8GB Jetson edge board) — it explicitly does not claim to generalize.
  Applying its "speed advantage erodes under memory pressure" finding to a
  dual-5060Ti 32GB-VRAM desktop is directionally reasonable given our own
  confirmed system-RAM ceiling, but is not a direct proof for this hardware
  class.

## Refuted — do not cite these as fact

Full list of claims that were proposed and killed on adversarial verification,
because they sound plausible enough to accidentally resurface later:

- vLLM's MXFP4 backend not recognizing SM120 and silently falling back to
  Marlin (1-2 — the actual confirmed bug is the narrower NVFP4/FlashInfer-CUTLASS
  one above, not this)
- SM120 NVFP4 MoE kernels already existing in-tree but gated off by dispatch
  logic (0-3)
- The SM120 NVFP4 MoE feature request being unresolved/unmerged as of the
  fetch (0-3 — it was fixed)
- The root cause being specifically an `is_device_capability_family(100)` /
  `120 // 10 = 12` integer-division bug (1-2 — plausible-sounding but
  unconfirmed)
- ktransformers having no documented Blackwell/SM120 support (0-3 — absence
  wasn't established, meaning presence is *also* not established; genuinely
  unknown either way)
- MoE routing overhead being negligible vs. memory/bandwidth being the real
  cost driver (1-2)
- Inference cost on constrained hardware tracking total params (not active
  params), directly refuting the sparse-activation pitch (0-3 — the erosion
  finding above is real, but this specific framing of it was rejected)
- A MoE model needing its full weight set resident regardless of routing,
  because routing can't be predicted ahead of time (1-2)
- MoE inherently facing an unavoidable three-way cost/accuracy/performance
  trade-off (1-2)
- MoE-Infinity claiming 3.1-16.7x latency improvement over vLLM/Ollama/DeepSpeed
  on a single commodity GPU (0-3)
- GPT-OSS-20B at 319-424 tok/s on an RTX 5090 at 8k context (1-2)
- Qwen3.6-35B-A3B GGUF at 33-36 tok/s on an RTX 3060 12GB (0-3)
- Selective FFN offload making Qwen3-235B-A22B usable on consumer GPUs (1-2)

## Open questions to resolve empirically, not by reading more

1. Does the confirmed (now-fixed) vLLM SM120 NVFP4-MoE bug actually affect our
   built 0.25.0, or is the fix already in? Smoke test before the session.
2. Which on-disk checkpoint actually gets the best tok/s-vs-quality tradeoff
   on this exact rig, using llama.cpp's `-ot`/`--n-cpu-moe` at various
   CPU/GPU split points? No verified numbers exist for this hardware class —
   this is the core of the actual test session.
3. Does ktransformers even install/run on SM120, and does its NUMA-aware
   design mean anything on a single-socket board? Direct test required.
4. Is there a genuine, reproducible bottleneck in stock vLLM/llama.cpp MoE
   serving that would justify custom patching — profile first, patch only if
   a specific wall shows up.

## Full source list

20 sources fetched across 5 search angles (runner/kernel maturity, memory-
constrained serving techniques, skeptical check on the sparse-activation
thesis, custom-patch value, practitioner model selection). Primary sources
carrying confirmed findings:

- https://github.com/vllm-project/vllm/issues/33416 — the confirmed, fixed SM120 NVFP4 MoE bug
- https://github.com/vllm-project/vllm/issues/31085 — broader SM120 MoE kernel feature request (claims from this source mostly rejected — read with caution)
- https://github.com/kvcache-ai/ktransformers — NUMA-aware hot/cold expert placement
- https://huggingface.co/blog/Doctor-Shotgun/llamacpp-moe-offload-guide — the `-ot`/`--override-tensor` mechanism
- https://gist.github.com/DocShotgun/a02a4c0c0a57e43ff4f038b46ca66ae0 — corroborating offload mechanism writeup
- https://knightli.com/en/2026/05/26/rtx-3060-llama-cpp-n-cpu-moe-local-35b/ — `--n-cpu-moe` flag confirmation (specific throughput number rejected)
- arxiv.org/pdf/2401.14361 — MoE-Infinity, sparse-activation trace study (<5% expert activation)
- arxiv.org/pdf/2606.21428 — OLMoE consumer/edge hardware empirical study (memory-pressure erosion)
- arxiv.org/pdf/2412.07067 (canonical ID, not 2505.11415) — offloading latency/cost tradeoff, 2.6x measured
- arxiv.org/html/2601.09527v1 — GPT-OSS-20B paper (mechanism confirmed, throughput number rejected)
