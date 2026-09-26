# 2026-09-26 rerun — what happens when retrieval actually reaches the history

The [2026-09-21 three-reader run](../2026-09-21/) scored 36%, 40% and 40% and looked like
evidence that the reader model barely matters for memory recall. The
[retrieval replay](../2026-09-21/retrieval_replay/) later showed why those numbers were so
close: under `--no-extract` the agent's `search_memory` tool read an extracted-fact store that
was empty by construction, and the tool that reads the FTS session archive was never called and
carried a user id the harness does not use. No reader could reach a fact outside its context
window, so the evaluation was measuring context-window membership for all three.

This run fixes the harness and repeats the same 25 `single-session-user` cases. It is the first
LongMemEval run here where retrieval is reachable.

## What changed in the harness

`harness/runner.py` (mirrored from the live copy) now logs every tool call with its full input
and output per case, logs every reader request, keeps the relay session log, disables MCP during
eval, and adds `--search-archive`, which serves `search_memory` from the FTS session archive
under the case's own user id. The agent-side user-id hardcode in `retrieve_sessions` was fixed
separately. `--search-archive` is the intended setting for `--no-extract` runs.

## Runs

| Label | Run ts | Reader | Archive routing |
|---|---|---|---|
| terra control | `20260926_072644` | gpt-5.6-terra (lab gateway) | off |
| terra archive | `20260926_072806` | gpt-5.6-terra | on |
| opus control | `20260926_082620` | claude-opus-5 (subscription bridge) | off |
| opus archive | `20260926_073203` | claude-opus-5 | on |
| sonnet archive | `20260926_072940` | claude-sonnet-5 (subscription bridge) | on |
| sonnet repeat | `20260926_073727` | claude-sonnet-5 | on |

Sonnet needs no separate control: archive routing only fires on a `search_memory` call, and
Sonnet made none, so its archive run **is** its control.

## Results

Hand column is the majority of four blind raters (see Judging). "Fact reached reader" counts the
15 cases whose answer session sits outside the reader's input window; "converted" is how many of
those were then answered correctly.

| Run | Hand | Exact | Cases searched | Fact reached reader | Converted | In-window |
|---|---|---|---|---|---|---|
| terra control | 10/25 (40%) | 0.42 | 14 | 0/15 | — | 10/10 |
| terra archive | 12/25 (48%) | 0.48 | 18 | 9/15 | 2/9 | 10/10 |
| opus control | 10/25 (40%) | 0.42 | 11 | 0/15 | — | 10/10 |
| **opus archive** | **19/25 (76%)** | 0.73 | 11 | 10/15 | **9/10** | 10/10 |
| sonnet archive | 9/25 (36%) | 0.38 | 0 | 0/15 | — | 9/10 |
| sonnet repeat | 9/25 (36%) | 0.38 | 0 | 0/15 | — | 9/10 |

### The control pair

Without retrieval, terra and Opus both score 40%, both at 0.42 exact, both 10/10 in-window. They
are indistinguishable, which reproduces the September result and explains it: both readers are
equally good at reading a fact out of their context window, and that is all September measured.
With retrieval reachable they separate to 48% and 76%.

The two Opus runs differ in one variable. Same reader, byte-identical system prompt, same 25
questions, and Opus chose to search on the same 11 cases in both. In the control every one of its
24 `search_memory` calls returned `No memories found`; with routing on, the same behaviour
returned the answer-bearing session 10 times. 40% → 76%.

### Three gates, not one

1. **Deciding to search.** Out of the 15 out-of-window cases: terra searched 10, Opus 11,
   Sonnet 0. This is reader behaviour, and it is close to bimodal.
2. **Writing a query that hits.** Terra issued 11 queries across its 10 searched cases (mean 1.1,
   single keywords). Opus issued 40 across 11 (mean 3.6, up to 8, including guesses at the
   source's phrasing). Despite the gap their retrieval hit rates are nearly the same, 9/10 and
   10/11. Query style mattered less than expected. The one case neither reaches, `lme_0010`
   (previous occupation), is the same case the September keyword replay could not reach.
3. **Using the fact once it arrives.** Terra converted 2 of 9. Opus converted 9 of 10. This is
   where the readers diverge, and it is the finding.

### Failure modes with the fact present

Terra's seven failures on delivered facts: five are abstentions with the answer session in
context (it had the commute text and said it had no commute recorded), and two are fabrications —
`lme_0009` answered "Tennis Warehouse" where the history says the sports store downtown, and
`lme_0004` answered "Chill Vibes" where the playlist is Summer Vibes. Both fabrications occur
only on cases where retrieval succeeded. Terra's control run and all 75 September predictions
contain none. Giving a weak reader working retrieval converted honest abstentions into confident
wrong answers.

Opus's single failure with the fact present (`lme_0022`, bike count) is the other kind: it
reported the one bike it could identify and said plainly it had no inventory and would not give a
count.

### Sonnet: observed, not explained

Sonnet made zero tool calls across two full runs and a direct replay of its own recorded request
payload against the bridge. A control probe with a short prompt does produce a tool call through
the same bridge, so this is not a bridge failure. On 2026-09-21 the same reader on the same cases
searched 30 times. Its 2026-09-26 system prompt is byte-identical to the one Opus received, and
contains an explicit mandatory directive to call `read_memory` and `search_memory` before
answering about any person, project or event.

September's request bodies were never recorded, so the September prompt cannot be compared and
this is not diagnosable after the fact. It is reported as an observation with an explicit unknown.
From this run forward the prompt is captured per call.

## Prompt stability

`requests_meta_*.jsonl` carries `system_sha256` and `system_sha256_canonical` per call. The raw
hashes differ between the first run and the rest; the canonical ones show why. The agent assembles
two always-on directives from a `frozenset`, and Python randomises string hashing per process, so
the two paragraphs are emitted in a different order in each process. Content is identical in every
run. Anyone comparing prompts across runs of this agent must canonicalise first or they will read
ordering noise as drift.

## Judging

Four independent raters, blind to reader identity, run label, `score_exact` and each other:
Dino Vitale (the original hand judge) via a web form, Claude (Fable 5.1), gpt-5.6-luna via the lab
gateway, and Grok. Items were shuffled with a fixed seed and relabelled; the rule is the one in the
[2026-09-21 README](../../README.md), and majority of four adjudicates.

Two packs, because the Opus control was run after the first five had been judged:
`judging/rerun_5runs/` (125 items) and `judging/opus_control/` (25 items). Each holds the blinded
items, the key, every rater's raw labels and the per-item agreement table.

| Pack | Items | Unanimous | Pairwise kappa |
|---|---|---|---|
| rerun_5runs | 125 | 122 | 0.952 – 1.000 |
| opus_control | 25 | 25 | 1.000 |

All three disagreements fall in one class: an answer that states the expected fact while
disclaiming confidence in it. The sharpest is `lme_0002` ("where did I redeem a $5 coupon on
coffee creamer", gold answer Target). The source session never says the coupon was redeemed at
Target; it says the user uses Target's Cartwheel app, redeemed a $5 coffee creamer coupon, and
shops at Target every other week. The gold label is itself an inference from adjacency. In the
archive run Opus said Target was the likely answer and explicitly flagged that it was inferring,
and was scored a miss by the human rater and correct by all three model raters. In the control
run the same reader on the same in-window evidence stated "Target" flat and was scored correct by
everyone. The item does not support a stable binary judgment and the rule as written rewards
unhedged confidence. Under Guo's framework it should be marked unscorable rather than forced.
Dropping it for all readers gives opus archive 18/24, terra archive 11/24, terra control 9/24,
opus control 9/24, sonnet 9/24 — the pattern is unchanged.

## What is here

| Path | Contents |
|---|---|
| `run_<ts>.jsonl` / `.log` / `summary_<ts>.json` | per-case results, full debug log, summary |
| `tools_<ts>.jsonl` | every tool call: case id, full input, full output, duration, `routed` |
| `requests_meta_<ts>.jsonl` | per reader request: model, message count, role sequence, tool names, system-prompt hashes |
| `sessions_<ts>/` | the relay session log preserved from the run's temp root |
| `per_case.csv` | one row per case × run: exact, searched, keywords, archive hit, answer session returned, position, request count |
| `judging/` | both blind packs: items, key, four rater files, agreement |
| `analyze.py`, `make_blind.py`, `requests_meta.py` | the scripts that produced the above |
| `sanitize.py` | the path convention applied to these artifacts before publishing |

`requests_meta_*.jsonl` replaces the raw request logs deliberately. Those hold the agent's private
system prompt in full, plus ~100 dataset messages per call — 34 MB of LongMemEval content anyone
can regenerate from the dataset and `harness/runner.py`. The metadata keeps every claim in this
README checkable: window size, tool surface, and prompt stability across runs.

Sonnet has no `tools_<ts>.jsonl`: the file is created on first tool call and it made none.

Paths in the logs and tool arguments are rewritten by `sanitize.py` to the convention the
2026-09-21 logs already use: the agent's tree is `~/agent` / `~/agent-memory`, the reasoning
journal is `JOURNAL`, and the operator's username is `operator`. Only paths and names are
touched. Every question, expected answer, prediction and score is byte-identical to the private
originals, which is checked by comparing the two copies record by record.
