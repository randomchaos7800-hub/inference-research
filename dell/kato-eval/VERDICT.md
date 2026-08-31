# CPU Agent-Fitness Eval — Qwen3-30B-A3B (MoE) vs Ornith-1.5-9B (dense) — 2026-08-24

**Question:** can a RAM-bound, CPU-only laptop run a *usable* local agent — and if so,
does a sparse MoE (30B total / ~3B active) or a dense 9B serve it better?

**Verdict: Qwen3-30B-A3B-Instruct-2507 wins on both axes.** Cleaner tool discipline
(7/7 tool tasks vs 6/7) and 2.2× faster end-to-end on the same 15-task suite
(300 s vs 658 s wall-clock; median task latency 14.5 s vs 34.3 s). On RAM-bound CPU
hardware the GPU-era MoE finding inverts: total parameters buy quality, active
parameters set speed, so the MoE gets you both. Adopted as the emergency local
fallback for the workstation agent.

## Hardware / serving

- Dell XPS 15 9570 — i7-8750H (6C/12T Coffee Lake, **no AVX-VNNI**), 32 GB DDR4, CPU-only
- llama.cpp `llama-server`, 6 threads, `n_ctx_slot` 4096, both models Q4_K_M GGUF
- Models: `Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf` (MoE, ~3.3B active) and
  `Ornith-1.5-9B-Q4_K_M.gguf` (dense)
- The GTX 1050 Ti (4 GB) is irrelevant at these sizes; nothing was offloaded

## Method

15 single-shot tasks ([tasks.jsonl](tasks.jsonl)) across four dimensions — tool-call
reliability (7, the gate), persona adherence (3), general capability (3), groundedness
(2) — run by [run_eval.py](run_eval.py) with 5 declared tools ([tools.json](tools.json))
against the agent's real system prompt ([system-prompt.txt](system-prompt.txt), tailnet
IPs redacted). Each record captures the model's **first response** — text and/or tool
call — plus latency and completion tokens; rubric expectations are embedded per task and
were judged manually in-session (no automated scorer). Temperature 0.2, max_tokens 512.

Separately, 3 passes of a 5-scenario **multi-turn** emergency suite
([emergency_run.py](emergency_run.py), Qwen only) tested offline/degraded operation with
tool results fed back, up to 9 turns.

## Results — 15-task suite

| | Qwen3-30B-A3B (MoE) | Ornith-1.5-9B (dense) |
|---|---|---|
| Tool tasks passed (strict rubric) | **7/7** | 6/7 |
| Suite wall-clock | **300 s** | 658 s |
| Median task latency | **14.5 s** | 34.3 s |
| Completion tokens (whole suite) | **673** | 2,445 |
| Decode median (server timings) | **5.7 tok/s** | 4.1 tok/s |
| Prompt eval median | 8.9 tok/s | 11.0 tok/s |

Receipts: [results-qwen3-30b-a3b.json](results-qwen3-30b-a3b.json) ·
[results-ornith-1.5-9b.json](results-ornith-1.5-9b.json) · raw server logs
([qwen](server-qwen.log), [ornith](server-ornith.log)).

Both models resisted the over-call trap (no tool on a thank-you message), the
under-call trap (ran `date` instead of inventing a time), picked correct tools with
correct arguments, and used a provided tool result instead of re-calling or ignoring
it. Neither hallucinated a tool result anywhere in the suite.

Ornith's one strict miss (`tool_rightpick`) was principled, not broken: asked to
message that a backup finished, it ran a shell check first — "I shouldn't claim it
finished cleanly without verifying" — where the rubric demanded the messaging tool.
Defensible behavior, but combined with 3.6× the tokens and 2.2× the wall-clock, the
dense 9B loses on the axis that matters for an interactive agent: time to a correct
action.

Where the speed comes from: raw decode is only ~1.4× apart (5.7 vs 4.1 tok/s — both
models stream from system RAM, and ~3.3B active vs 9B dense params sets that gap).
The rest is discipline: the MoE answered in 673 tokens what the dense model took
2,445 to say. Conciseness is a latency feature on 4-tok/s hardware.

## What the eval surfaced beyond the A/B

- **A prompt gap, not a model gap:** the finance-boundary task expected deference to
  the fleet's finance agent, but the system prompt under test never named it. Both
  models improvised (Qwen declined and gave generic advice; Ornith went hunting in
  memory). Fix was made in the agent's prompt/roster after the eval — the eval's
  most actionable output wasn't a score.
- **Multi-turn diagnosis is NOT viable** ([emergency runs](emergency-qwen3-30b-a3b.json),
  3 passes): in the "inference down" scenario the recovery path was stated *in the
  model's own system prompt*, and it still burned 6–9 turns hunting the service
  locally. Single-action judgment tasks (offline capture, refusing to store sensitive
  data) were 1-turn clean in every pass. Conclusion: use a small local model for
  narrow, already-cornered judgment calls; keep diagnosis deterministic.
- **Cold prompt processing is the tax:** first Qwen task ate a 1,018-token system
  prompt at ~16 tok/s prefill (64 s before the first output token). With the prompt
  cached, subsequent tasks ran 2–9 s. A CPU agent wants a warm server, not per-call
  model load.

## Relation to the GPU MoE finding (2026-07-14)

The [tower MoE report](../../tower/moe/FINAL-REPORT-2026-07-14.md) found every MoE
checkpoint beat the dense 27B production model on speed and lost badly on quality —
on dual-GPU hardware where the dense model already ran at ~97 tok/s. This eval is the
other end of the envelope: when the constraint is RAM bandwidth and the dense
alternative that *fits usably* is 9B, the 30B-total MoE is the smarter model **and**
the faster one. Same architecture, opposite verdict, because the binding constraint
moved. (Different checkpoint and task type too — Instruct-2507 on agent fitness here
vs the older checkpoint on domain-expert depth there; this is an envelope claim, not
a rehabilitation of the July quality scores.)

## Notes

- Eval cases here are **not** counted toward the public benchmark-run total
  (capability receipts, not throughput runs — same policy as the LangChain suites,
  see [COUNT.md](../../COUNT.md)).
- Tailnet IPs and the tailnet DNS name are redacted (`REDACTED-*`) uniformly across
  all receipts; no other edits were made to the captured data.
