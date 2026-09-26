# LongMemEval — does agent memory survive a model change?

Receipts for the memory study on [boundarylabs.org/partners](https://boundarylabs.org/partners.html):
one persistent agent, one memory, three different reader models, same 25 questions,
same harness, same afternoon. Everything a claim below rests on is in this directory.

## Layout

| Path | What it is |
|---|---|
| [`harness/`](harness/) | The harness as run: `runner.py` (inject → ask → score), `run_with_model.py` (pin every turn to another OpenAI-compatible endpoint), `report.py`, `setup.sh` |
| [`runs/2026-09-26/`](runs/2026-09-26/) | **The rerun with retrieval reachable** — six runs, controls, full tool and request traces, four-rater blind judging. Start here. |
| [`runs/2026-09-21/`](runs/2026-09-21/) | The three-way run: per-case JSONL, full debug log and summary for each reader, plus `hand_judgments.csv` and `answer_position.csv` |
| [`runs/2026-04-07/`](runs/2026-04-07/) | The April context-window run the Zenodo preprint cites (different mode, different reader — see below) |

## Setup

- **Dataset:** `xiaowu0162/longmemeval-cleaned`, split `s` (~500 turns across ~50 sessions per case). The 25 cases are the first 25 `single-session-user` questions in dataset order; `question_id` is in the CSVs.
- **Agent:** a persistent companion agent (private codebase, RelayV3). For every case the harness writes the whole haystack into a fresh, isolated `sessions.db` with the dataset's real timestamps, backfills the FTS index, then asks the question through the agent's normal `respond()` path. The agent sees a rolling window of roughly the last 100 messages of that history plus its tools: `search_memory`, `read_memory`, `read_tacit`, `read_timeline`, `retrieve_sessions` (FTS over the injected history).
- **`--no-extract`:** the extraction pipeline that turns sessions into memory-graph facts was **off**. The only place the answer existed was the injected session history. "Memory" in this run therefore means *session history + retrieval tools*, not the extracted knowledge graph.
- **Readers:** the same agent, same prompt, same tools, with primary inference pointed at
  - `gpt-5.6-terra` (OpenAI API through the lab's gateway) — the agent's normal reader for this user lane
  - `claude-sonnet-5` and `claude-opus-5` through a Claude Code subscription bridge on `:8020` (OpenAI-compatible shim; `run_with_model.py` disables the OpenRouter fallback so no turn silently changes model)
- **Scoring:** the harness's exact/substring/word-overlap scorer (`score_exact` in `runner.py`), then one hand-judging pass. The LLM judge in the harness was not used: its model (`google/gemini-2.0-flash-001`) is gone from OpenRouter.

## Results

**Read this first.** The September 21 numbers below were produced by a harness in which no reader
could reach a fact outside its context window: `search_memory` read an extracted-fact store that
was empty under `--no-extract`, and the tool that reads the session archive was never called.
The [2026-09-26 rerun](runs/2026-09-26/) fixes that and repeats the same 25 cases with controls:

| Reader | No retrieval | Retrieval reachable |
|---|---|---|
| gpt-5.6-terra | 40% | 48% |
| claude-opus-5 | 40% | **76%** |
| claude-sonnet-5 | — | 36% (made zero search calls) |

Without retrieval terra and Opus are indistinguishable, which is what September measured. With it
they are 28 points apart. The readers were never equivalent; the evaluation could not see the
difference. Mechanism, per-case traces and judging are in
[`runs/2026-09-26/README.md`](runs/2026-09-26/README.md).

### September 21 run (retrieval unreachable)

| Reader | Run | Harness exact | Hand-judged |
|---|---|---|---|
| gpt-5.6-terra | `run_20260921_134224` | 34% | **9/25 = 36%** |
| claude-sonnet-5 | `run_20260921_135525` | 48% | **10/25 = 40%** |
| claude-opus-5 | `run_20260921_135842` | 44% | **10/25 = 40%** |

Hand-judging rule: correct iff the answer states the expected fact. An "I don't have that" is a miss no matter what the scorer says. One judge, one pass, no second rater — that is the known weak spot of this evaluation. **Closed 2026-09-25:** two blind raters (Claude, gpt-5.6-luna) re-judged all 75 predictions and agreed with the hand column on every item, κ = 1.0 — see [`runs/2026-09-21/judge_reliability/`](runs/2026-09-21/judge_reliability/). Per-case rubric profile (Guo's four axes) in [`runs/2026-09-21/rubric_annotations.csv`](runs/2026-09-21/rubric_annotations.csv).

The same 15 cases are misses on both Claude readers. terra misses those 15 plus `lme_0007`, and returned an empty string on three of them (`0004`, `0007`, `0009`). Per-case verdicts and notes: [`hand_judgments.csv`](runs/2026-09-21/hand_judgments.csv).

## What the receipts show

**The outcome tracks the context window.** [`answer_position.csv`](runs/2026-09-21/answer_position.csv) locates each case's answer session inside the injected history (`answer_session_start_from_end` = how many injected turns from the end the answer session begins). Every correct answer has its answer session starting ≤ 97 turns from the end. Every miss has it starting ≥ 160 turns from the end. The logs show each reader call carrying 102–113 messages. That is an association across 25 cases, not a causal decomposition: the logs record that `search_memory` ran 58 times across the three runs but not what it asked or what it returned, so whether retrieval ever reached beyond the window is not observable from these receipts. (Wording corrected 2026-09-25 after Baixin Guo's observability audit.)

**Update 2026-09-25 — the mechanism, reconstructed:** [`runs/2026-09-21/retrieval_replay/`](runs/2026-09-21/retrieval_replay/) recovers what the logs left out. The reader's input was the last 100 messages by timestamp (the loader's fallback branch, since the injected 2023 dates never match "today"), which is exactly the 97/160 boundary. `search_memory` searches the extracted-fact store, which was empty under `--no-extract`, so all 58 calls returned nothing by construction; the tool that reads the FTS archive was never called and hardcodes a user id the harness does not use. The Claude bridge log preserved every Sonnet/Opus search keyword; replayed through the FTS index under the right user id, they rank the answer session top-2 in 20 of the 22 searched misses. The misses are memory-availability misses at the reader input, not retrieval misses, because retrieval never touched the history.

**Retrieval miss vs. memory miss cannot be separated from these logs.** The harness logs *that* a tool ran (`Tool (read,parallel): search_memory`), not the query it sent or what came back. So for the 15 shared misses we can say the fact was in the database and the agent answered "I don't have that"; we cannot say whether the search was never issued for the right term, issued and returned nothing, or returned the passage and the reader ignored it. Closing that gap is the first job of the next harness revision.

**The exact scorer has false positives and noise.** `lme_0014`: sonnet/opus score 1.0 because "10%" appears inside an "I don't have that" answer. `lme_0009`, `lme_0017`: 0.5 from word overlap on an "I don't know". `lme_0008`: 0.5 on two readers for "Valentine's Day, February 14" against expected "February 14th". Treat `score_exact` as a first pass only.

**Reader texture differs, outcome barely does.** Claude answers cite where a fact came from and what they searched; terra answers are one line. On recall the difference is one case (`lme_0007`, gray walls).

**Two opus answers carry a leak.** `lme_0004` and `lme_0023` end with a connector-authorization notice from the bridge host's own tooling. Bug in the bridge, fixed after this run (`strict_mcp_config=True`); left in the receipts as-is.

## The April run (different protocol)

[`runs/2026-04-07/`](runs/2026-04-07/) is the run the Zenodo preprint cites: same 25 questions, `--no-extract`, but the agent then ran a **500-message** context window (the whole haystack fit) and the reader was `google/gemma-4-31b-it` via OpenRouter. The summary file says 88% (22/25) after a scorer fix for markdown; the paper's table says 84% (21/25), written before the fix. Both numbers are here. It has not been hand-judged, and its `score_exact` column has the same defects noted above. It is not comparable to the September run except as evidence that the same facts are answerable when they are in the window.

## Running the harness

`runner.py` imports the agent's private modules (`memory.storage`, `relay.session_log`, `relay.sessions`, `relay.relay.RelayV3`, `memory.extraction`, `relay.switchboard`), which are not published. To run it against another agent you need: a `respond(question, user_id=...)` entry point, a `messages(user_id, role, content, timestamp, session_date)` table the agent reads its history from, and an FTS backfill for that table. The injection, date handling, scoring and output format are all in the file and need nothing private.

Not included, by policy: the agent's system prompt, its memory contents, and anything running on lab machines. Public artifacts only.
