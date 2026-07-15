# MoE live testing notes

Actual results from running [EXPERIMENT-DESIGN.md](EXPERIMENT-DESIGN.md), phase
by phase. Companion to [README.md](README.md) (pre-test literature research).

## Phase 0 — SM120 NVFP4-MoE bug smoke test (2026-07-14)

**Method:** Locked via `tower-experiment-lock.py lock --minutes 30 --reason
moe-phase0-smoketest-sm120-nvfp4-moe-bug`. Loaded `Qwen3-30B-A3B-NVFP4`
(128 experts, 8 active/token, `modelopt` NVFP4 quant) on the built 0.25.0
vLLM, minimal config: TP=2, GMU 0.85, ctx 8192, enforce-eager, no MTP, no
offload. Watched for the confirmed error string
(`does not support the deployment configuration`).

**Result: the bug is fixed.** Confirmed via the actual dispatch logs, not
inference:
```
Using FlashInferCutlassNvFp4LinearKernel for NVFP4 GEMM
Using 'FLASHINFER_CUTLASS' NvFp4 MoE backend out of potential backends: [...]
Model loading took 8.44 GiB memory and 31.942870 seconds
```
No error, no fallback, both workers loaded cleanly. This resolves the open
question from the research pass and unblocks Phase 3 (same question, gates
that phase in the design doc).

**New finding, not predicted by the research pass:** after weight loading
succeeded, the engine stalled — `EngineCore` and both `Worker_TP{0,1}`
processes sat idle (1-7% CPU, 0% GPU utilization) for 4+ minutes, repeating
`shm_broadcast: No available shared memory broadcast block found in 60
seconds` every 60s. This is the same warning message seen repeatedly during
2026-07-13's dense-model testing, but a **different underlying situation**:
- 2026-07-13's occurrences were swap-thrashing under real RAM pressure
  (host RAM pinned near-zero, heavy swap I/O).
- This stall had **healthy RAM** (21GB available, no thrashing) and **idle
  processes** (low CPU, zero GPU compute) — not working slowly, genuinely
  stuck waiting on something.

One lead, not confirmed as root cause: the engine init log shows this MoE
model auto-enables Expert Parallel under TP=2 — `EP rank 0` alongside `TP
rank 0` in the rank assignment line, something the dense models tested
2026-07-13 never had (they're not MoE, no experts to parallelize). EP adds a
synchronization point dense-model testing never exercised. Worth checking
whether an explicit flag to disable EP (if one exists) avoids the stall,
before assuming it's fundamental to running this checkpoint at all.

**Action taken:** stopped the stalled process cleanly (VRAM confirmed
released: 118/15 MiB), unlocked via `tower-experiment-lock.py unlock`,
verified production genesis restored and actually serving (not just
reported healthy) before ending the session. Total lock time used: ~13 of
the requested 30 minutes.

**Open question added to the list:** does this TP/EP synchronization stall
affect all MoE checkpoints under vLLM 0.25.0 on this hardware, or is it
specific to this model/quant/config combination? Needs testing with EP
explicitly disabled (if possible) and/or a different MoE checkpoint before
Phase 1 proceeds, since if this is universal it changes the whole plan.

**Correction (Phase 3, below): the TP/EP theory was wrong.** Root cause
found — see Phase 3.

## Phase 1 — Qwen3-30B-A3B-GPTQ-Int4 confirmation (2026-07-14)

**Result:** 41.66-42.41 tok/s (matches the 2026-05-16 archive's 41.33 t/s
median — confirmed still holds). Domain-suite quality: **2.67/5**, driven by
a specific non-random error pattern — long, confident, well-organized answers
that land backwards on the one decisive constraint in three scenarios
(yellow-trap traffic signal, rail-crossing queue spillback, catering-contract
cancellation). Worse than both dense models tested 2026-07-13 (genesis 3.73,
nvidia-27B-MTP 3.87). First probe attempt hit the exact "Benchmark Truncation
Confound" already on file in case-law (missing `enable_thinking: false`) —
fixed and rerun clean per report at
`~/model-eval/results/domain-suite-qwen3-30b-a3b-gptq-20260714.md`.

## Phase 2 — Qwen3-30B-A3B-Q3_K_M offload sweep, llama.cpp (2026-07-14)

**Speed (the offload curve this hardware class never had a real number for):**

| N_CPU_MOE (layers offloaded to CPU) | tok/s | VRAM (GPU0) |
|---|---|---|
| 0 (full GPU) | 121.5 | 17.9GB total split across both cards (9.3+8.6GB) |
| 8 | 68.4 | ~15.5GB |
| 16 | 55.2 | ~13.3GB |
| 24 | 50.0 | ~11.2GB |

Clean monotonic curve — offloading trades speed for VRAM headroom exactly as
the mechanism research predicted, no surprises. Full-GPU (N=0) is both the
fastest MoE result of the whole session and beats genesis's ~73 t/s outright,
almost 3x the same base model's GPTQ/vLLM speed (Phase 1: 41-42 t/s).

**Quality at N=0 (the fast config): 1.87/5** — full report at
`~/model-eval/results/domain-suite-qwen3-30b-a3b-q3km-20260714.md`. This is
*worse* than Phase 1's GPTQ run on the same base model (2.67), despite Q3_K_M
being nearly 3x faster. The GPTQ run's exact error pattern reproduces
directly — same three scenarios (yellow-trap, rail-crossing, catering-
contract) score 1/5 with the identical failure shape in both runs, which
points at a base-model/fine-tune weakness rather than a quantization or
runtime artifact. Q3_K_M's additional quality loss on top of that (2.67→1.87)
tracks with 3-bit K-quant being meaningfully coarser than 4-bit GPTQ.

**First real point where the fastest config is also the worst-scoring one.**
Every prior phase this session (Phase 1, and Arc 1's dense-model work) had
speed and quality move together or trade off gently — this is the first
sharp inversion. Worth carrying into final synthesis as a caution against
reading "beats genesis on tok/s" as "beats genesis, period."

## Phase 3 — Qwen3-30B-A3B-NVFP4 stall investigation (2026-07-14)

**Both leading hypotheses from Phase 0 were wrong.** Relaunched the identical
Phase 0 config (TP=2, GMU 0.85, ctx 8192, enforce-eager, no MTP) plus genesis
production's PCIe-no-NVLink NCCL settings (`NCCL_P2P_DISABLE=1`,
`NCCL_BUFFSIZE=4194304`, `--disable-custom-all-reduce`) — the stall
reproduced identically. This also retroactively rules out the "auto-enabled
expert-parallel" theory: `enable_expert_parallel` defaults to `False` in
vLLM 0.25.0 and Phase 0 never set it; the "EP rank" field in the stall-time
log line is printed unconditionally as part of the DP/PP/PCP/TP/EP/EPLB rank
tuple, regardless of whether EP is actually active — misread as evidence of
EP being on when it never was.

**Actual root cause, found by checking `ps aux` during the "stall" instead of
reading the stall as a black box:** 91 concurrent `nvcc`/`cicc`/`ptxas`
processes. FlashInfer has no precompiled AOT kernel for `fused_moe_120`
(the NVFP4 MoE GEMM kernel) on SM120 + `fp8_uint4`, so it JIT-compiles on
first load — and the launch script never set `MAX_JOBS`, the same gap fixed
once already this session for the vLLM *build* step but never carried to
this runtime launch script. Load average hit 24.4, host RAM hit 30/30Gi used,
swap hit 87/95Gi — real thrashing, not a hang. This also explains a run of
"transient" SSH exit-255 errors trying to kill the test: the box was too
overloaded to service new sessions promptly, not a network blip. New case-law
entry written: "An Uncapped JIT Compile Storm Looks Exactly Like a Deadlock."

**Verdict for Phase 3's actual question (does quant recipe matter for MoE
speed/quality the way it did for dense):** still unanswered, but now for a
different, more specific reason. **Retest (same session, 2026-07-14):**
capped `MAX_JOBS=3` in the launch script and relaunched. Confirmed the fix
works as intended — RAM never thrashed this time (available RAM oscillated
healthily, swap topped out at 3/95GB vs. the uncapped run's 87/95GB, no SSH
exit-255 pattern during monitoring). But the compile itself is just
**genuinely slow**: still mid-compile at 12+ minutes wall-clock when the test
was stopped to stay inside the lock window, working through dozens of
per-shape CUTLASS GEMM template instantiations
(`cutlass_kernel_file_gemm_sm90_M*_group*.generated.cu`) for
`fused_moe_120`. This is a one-time cost — successful compiles are cached to
`~/.cache/flashinfer/0.6.13/120f/` and would make every subsequent load
instant — but 12+ minutes (likely 15-20+ to actually finish, based on
progress rate) is real, and makes this path impractical to casually retest
without either (a) a dedicated pre-warming run with a long, unsupervised
lock window, or (b) checking if a prebuilt FlashInfer AOT wheel exists for
SM120 fp8_uint4 to skip JIT entirely. **Final status: this model's
quant-recipe-vs-GPTQ speed/quality question remains open** — not because of
a bug, but because the honest cost of getting a first answer is a
multi-minute one-time compile this investigation didn't have lock-budget
left to fully pay. Worth revisiting in a dedicated session with no time
pressure, not worth forcing into this one.

## Phase 4 — Qwen3.6-35B-A3B-UD-Q4_K_M load-safety + quality, llama.cpp (2026-07-14)

Load-safety re-check only, per the design doc — speed was already proven
(100.24 t/s, 20-iteration autoresearch sweep, April 2026). Checkpoint is
22GB on disk, above the 18GB wedge threshold, so this was the real question:
does the proven config still load safely under current conditions. Ran with
an external ping monitor through the load window (mirroring the dense-model
protocol) plus continuous `free -h` sampling. **Loaded clean in 42s** — RAM
available never dropped below 5.6GB, no swap engagement, zero ping loss.
**Speed confirmed: 100.54 t/s**, matching the archived number exactly.

**Quality: 2.87/5** — best MoE quality score of the session at that point,
still ~0.9 below both dense models. **Real methodology flag**: 10 of 15
responses were truncated mid-sentence at max_tokens=1600 — this model burns
significant budget on visible self-correction ("Wait, let's re-read the
prompt...") even with the launch script's thinking-suppression flags, and
two logistics items never reached a final answer at all. Scored as a real
quality problem (an unfinished answer is a bad answer) but flagged as a
likely confound — max_tokens was raised to 3000 for every subsequent phase
as a direct result. Full report:
`~/model-eval/results/domain-suite-qwen36moe-a3b-20260714.md`.

**Error pattern check:** 2 of 3 known items reproduce. traf1 (yellow trap)
and traf4 (rail crossing, more explicitly — flatly asserts the roundabout is
"immune" to spillback) both fail the same way as every Qwen-family run
before it. rest5 does NOT reproduce here — this model correctly keeps both
commitments instead of canceling the contract.

## Phase 5 — Nemotron-3-Nano-30B-A3B-Q4_K_M confirmation + quality, llama.cpp (2026-07-14)

Confirmation run of an already-proven config (117-123 t/s, 100% tool-calling
pass, validated 2026-05-28) — the original `build-cuda128-clean` binary no
longer exists on disk (llama.cpp rebuilt 2026-06-13), so this ran on the
current single `build/` dir, the same one used cleanly in Phases 2 and 4
(no MMQ crash, unlike the old build-cuda13 failure mode on record).
Checkpoint is 24.65GB on disk, the largest tested this session — loaded
clean in ~2 minutes, RAM never thrashed (available stayed above 1.9GB
throughout, swap barely touched). **Speed confirmed: 123.4 t/s**, within the
archived 117-123 t/s range.

**Quality: 2.80/5** — an unusually flat split (Logistics 2.8, Traffic 2.8,
Restaurants 2.8, no domain standing out). Raised max_tokens to 3000 for this
probe (lesson from Phase 4's truncation); only 2 of 15 responses truncated
this time, both with the substantive content already delivered before the
cutoff. Full report:
`~/model-eval/results/domain-suite-nemotron-3-nano-20260714.md`.

**Most important finding of this phase:** traf1 and traf4 reproduce on
Nemotron too — a base model from a completely different lineage (NVIDIA,
not Qwen-derived). Same failure *shape* (confident fabrication of a
plausible-sounding wrong mechanism), different specific fabrication each
time. rest5 does not reproduce (matches Phase 4). Seeing the identical
failure shape survive a change of base-model family, not just quantization
or runtime, is the first strong evidence this is a **model-size-class
issue, not a per-model or per-family weakness**.

## Phase 6 — GPT-OSS-20B, native MXFP4, llama.cpp (2026-07-14)

Acquired fresh: `ggml-org/gpt-oss-20b-GGUF`'s single-file native MXFP4
conversion (12.1GB on disk, well under the wedge threshold — loaded in ~6.5s,
no risk). All-GPU, `reasoning_effort: low`. **Speed: 133.05 t/s** — the
fastest clean (non-quality-compromised) result of the whole session, ahead
of Nemotron (123.4) and Qwen3.6-35B-A3B (100.54), consistent with it being
the smallest total-param candidate tested and benefiting from this build's
native `BLACKWELL_NATIVE_FP4` kernel path (confirmed present in the
system_info log line).

**Quality: 2.20/5** — the second-lowest score of the session (only Q3_K_M's
1.87 is lower), over 1.5 points behind both dense models. All 15 responses
completed cleanly, no truncation.

**The cross-family pattern holds a third time, in its starkest form yet:**
traf1 (yellow trap) reproduces — fabricated mechanism, no FYA mention.
traf4 (rail-crossing spillback) reproduces **more explicitly than any prior
run**: this model doesn't just miss the risk, it flatly states the
roundabout's rail-crossing interaction is "None (independent)" and
recommends it with the highest confidence seen this session — a directly
falsifiable, stated-backwards claim, not just an omission. rest5 (catering
contract) does not reproduce, consistent with 2 of the 3 prior runs.

**New, more severe finding than anything in the Qwen/Nemotron runs:** this
model also produced an actively unsafe answer on rest3 — instructing
reheating and re-serving temperature-abused soup, a real food-safety
violation, not just an incomplete answer — plus backwards central-constraint
errors on log1 (assigns produce to a reefer that would freeze it) and log2
(fabricates a fictitious axle-weight regulation while missing the real
violation). Full report:
`~/model-eval/results/domain-suite-gptoss-20b-20260714.md`.

**Capstone finding for the whole quality investigation:** traf1 and traf4 now
fail identically across three architecturally unrelated base-model families
(Qwen, Nemotron/NVIDIA, OpenAI GPT-OSS), four quantization formats, and two
runtimes (vLLM and llama.cpp), at every total-param size tested (20B through
35B). This is not a per-checkpoint quirk — it's a hard floor for this whole
class of MoE model at this scale on these two specific traffic-engineering
scenarios, and GPT-OSS-20B additionally suggests the floor gets *worse*, not
better, at the smaller end of the size range tested.
