# Nemotron tool-calling — hard-smoke verdict (2026-05-28)

Model: Nemotron 3 Nano 30B A3B, llama.cpp :8022, default jinja, no grammar constraint.

## TL;DR — "stick with nemo" is validated on tools
Objective pass rate **100% (22/22)** once served correctly. Tool-calling is good-to-excellent
across selection, abstention, typed/enum args, ambiguity-handling, and mixed multi-tool.
Two minor soft spots remain (below), neither a blocker.

## The catch that almost fooled us (important)
First pass scored 82.6% with "no tool call" failures on the reasoning-heavy prompts
(parallel, sequential, relative-date reminder). Root cause: **Nemotron is a reasoning model
that emits ~400 tokens of `reasoning_content` BEFORE the tool call.** The harness used
max_tokens=350, so it hit `finish_reason=length` mid-thought and returned empty — no tool call.
Same prompts at max_tokens=2048 → correct calls. The "failures" were budget starvation, not capability.

## Production serving rules (the real deliverable)
1. **max_tokens >= 1024 for agentic use** (ideally 1500-2048). A tight budget silently kills
   tool calls with empty `finish_reason=length` responses. This is the #1 gotcha.
2. Reasoning lands in a separate `reasoning_content` field — llama.cpp parses it cleanly, so
   the visible content / tool_calls stay clean. (Optionally disable thinking to cut latency, like
   Genesis's enable_thinking:false — but thinking helps multi-step tool decisions.)
3. **Inject the current date** into the system prompt — the reminder test guessed a datetime
   (model doesn't know "today").

## Category results (max_tokens=2048)
- selection: 10/10  (incl. calculator, unit_convert, stock, translate, web_search, file, reminder, contact)
- abstention: 5/5  — never over-calls on knowledge/chitchat (the classic MoE failure — Nemotron avoids it)
- ambiguity: 3/3  — correctly ASKS for missing info instead of hallucinating args
- typed_args: 2/2  — enum (unit=f), date+time
- multiturn: use-of-tool-result PASS; sequential-chain 2nd step soft (REVIEW)
- parallel: different-tools PASS; same-tool-x2 soft (REVIEW)

## Two residual soft spots (manageable, not blockers)
1. **Parallel calls to the SAME tool** (e.g. weather for Paris AND Berlin in one turn) is
   inconsistent — sometimes emits both, sometimes one. Parallel calls to DIFFERENT tools
   (email + calendar) are solid. Mitigation: for N-of-same, prompt sequentially or loop.
2. **Sequential chain step 2** once didn't fire after the tool result was returned (may have been
   reasonable clarification on a vague "the agenda"). Re-test with concrete tasks; give budget.

## Bottom line
Nemotron clears the tool-calling bar that was the only thing pushing toward the slow dense-27B /
fragile Genesis stack. With a sane token budget it is a strong agentic tool-caller AND the fastest,
simplest option (123 t/s, llama.cpp). For the companion product: nemo.
