# Retrieval replay — what the September logs could not show, reconstructed

**Written 2026-09-25 in response to Baixin Guo's observability audit** (his finding: the public
receipts record that `search_memory` ran, not what it asked or returned, so retrieval-miss vs
memory-miss is not identifiable). This folder closes most of that gap from two sources the
public run folder did not have: the agent's code paths, and a private log from the Claude
reader bridge that recorded every search keyword.

## Files

| File | What it is |
|---|---|
| `bridge_search_calls.log` | Filtered extract of the Claude bridge (`:8020`) log for the Sonnet and Opus runs: one `start` line per reader call (message count, tool count, prompt characters) and one line per `search_memory` call with its arguments. Answer text and cost removed; everything else verbatim. The first two calls are warm-up probes, not eval cases. |
| `search_queries.csv` | The same keywords mapped to cases by timestamp against the run log's `[lme_NNNN] Asking` lines. |
| `replay.py` | Rebuilds each case's SQLite history from the public dataset with the harness's own `inject_haystack`, builds the same FTS5 index (`porter ascii`, user-role messages only), and runs each logged keyword through the same query `retrieve_sessions` uses. Standalone; needs only the dataset and `harness/runner.py`. |
| `retrieval_replay.csv` | Output of `replay.py`: per keyword, how many rows matched and whether the answer session was in the top-2 deduped session dates. |
| `oracle.py` | Guo's T1 and T2 oracle arm across all 25 cases: rebuilds each case, checks that the answer-bearing session's user turns are in the FTS index (T1), then queries the index with the expected answer's wording under the case's user id (T2 oracle). |
| `oracle_replay.csv` | Output of `oracle.py`. |

## Mechanism — determined by code, not inferred from outcomes

Three facts about the agent under the `--no-extract` condition, each readable from the code the
harness exercised:

1. **Reader input was the last 100 messages by timestamp.** The context loader first asks for
   "today's" messages. The injected history carries its 2023 dataset dates, so that set is empty
   and the loader falls through to `ORDER BY timestamp DESC LIMIT 100`. The reader call therefore
   carried those 100 messages plus system and question (the 102–113 `msgs=` values in the bridge
   log; extra messages are tool-call turns). This is the origin of the 97-turn / 160-turn
   boundary in `answer_position.csv`: an answer session that starts ≤100 turns from the end is in
   the reader's input, one that starts ≥101 is not. For this run, "in the window" and "in the
   reader input" are the same statement (E4 in Guo's rubric is derivable per case).

2. **`search_memory` never searched the injected history.** It searches the agent's extracted-fact
   store (`facts.json` files under the memory root). The harness pointed that root at a fresh
   directory and ran with extraction skipped (`"extraction": {"skipped": true}` in every JSONL
   row), so the store was empty for the whole run. Every one of the 58 `search_memory` calls
   across the three readers returned `No memories found matching '<keyword>'`, by construction.

3. **The tool that does search the history was never called, and could not have worked.** The
   `FTS backfill: N messages indexed` log line builds an index that only `retrieve_sessions`
   reads. No reader called it in any run (tool tallies from the public logs: terra used
   `read_file`, `read_memory`, `read_tacit`, `read_timeline`, `review_own_conversations`,
   `search_memory`, `run_shell`; Sonnet and Opus used only `search_memory`). Separately,
   `retrieve_sessions` hardcodes `user_id="dino"` while the harness injects each case under its
   own `lme_NNNN` user id, so it would have matched zero rows had it been called. The last column
   of `retrieval_replay.csv` shows this: 0 matches for every keyword as user `dino`.

**Consequence.** The 15 shared misses are not retrieval misses in the usual sense. Retrieval was
never engaged with the store that held the facts. The fact was absent from the reader's input
(mechanism 1), the only search the readers used was empty by construction (mechanism 2), and the
search that could have found it was unreachable (mechanism 3).

## What the readers searched for, and what it would have found

Sonnet called `search_memory` on 14 of its 15 misses and on none of its 10 hits. Opus called it on
8 of 15 misses and on none of its hits. Terra made 18 calls; its keywords are lost (see below).

Replaying the logged keywords through the FTS index under the correct user id:

| Reader | Cases searched | Answer session ranked in top 2 by at least one keyword |
|---|---|---|
| Sonnet | 14 | 13 |
| Opus | 8 | 7 |

The one case neither reader's keywords reach is `lme_0010` ("occupation", "ATD", "previous job";
the session text uses none of those words). Per-keyword detail is in `retrieval_replay.csv`.

So: the readers formed usable queries for 13 of 15 misses. Had `search_memory` been wired to the
FTS archive under `--no-extract`, or had `retrieve_sessions` used the case's user id and been
called, the retrieval stage would have surfaced the answer session in 13 of 15 misses. Whether
the reader would then have answered correctly is a separate, untested stage.

## Guo's test matrix, run against the September data where possible

The Failure Attribution Test Matrix (2026-09-26) defines T1–T5. This folder already executes or
derives three of them for the September run:

| Test | Status here | Result |
|---|---|---|
| T1 source availability | run (`oracle.py`) | answer-bearing session indexed in **25/25** cases |
| T2 normal arm | run (`replay.py`) | readers' own keywords rank the answer session top-2 in 20/22 searched misses |
| T2 oracle arm | run (`oracle.py`) | expected-answer wording ranks it top-2 in **22/25**; the 3 misses (`lme_0008` "February 14th", `lme_0014` "10%", `lme_0024` "12") are weak oracle strings, not index failures |
| T3 reader exposure | derived, not traced | reader input = last 100 messages (mechanism 1), so exposure is `answer_session_start_from_end ≤ 100`: true for all 10 hits, false for all 15 misses |
| T4 fixed-transcript replay | not run | needs the request body, which was never captured |
| T5 blind second judge | not run | needs a second rater |

One correction to T2 as written: its "normal agent-issued retrieval request" must be pointed at the
FTS archive. In September the agent's request went to the extracted-fact store, which was empty,
so the normal arm as literally executed would compare an empty result against the oracle every time
and tell you nothing about retrieval.

## What survives and what does not

- **Survives:** Sonnet and Opus search keywords with timestamps (bridge log); per-call message
  and prompt-character counts; everything in the public run folder.
- **Lost:** terra's 18 `search_memory` keywords, its 19 `run_shell` commands and 23 `read_file`
  paths. The agent's per-session tool log (which records tool inputs truncated to 200 chars) was
  written under the run's temp directory, and `runner.py` deletes that directory at the end of
  each run (`shutil.rmtree(run_tmp)`). Nothing else recorded tool inputs for the terra reader.
- **Never recorded anywhere:** tool outputs, and the exact reader request body. For this run both
  are reconstructible from code (mechanisms 1–2), not from a trace.

Correction (2026-09-26): an earlier version of this note said terra's `read_file` calls went
through the MCP filesystem server rooted at the real code and memory trees. They did not. The
calls were to the agent's native `read_file`, which the capability gate refused for the eval
interface; the MCP tools were likewise not on the untrusted allowlist. The MCP server was
started during eval, which is still wrong, and the revised harness no longer starts it.

## Placement in the Failure Attribution Rubric

Using Guo's four axes for the September run:

- **Sonnet, Opus:** E1 from the public receipts alone; **E3 for the 22 searched cases** with this
  folder (query known, result known by construction); E4 derivable for all 25 (mechanism 1).
  Attribution moves from **A0 to A3** for the 15 misses: source present in history, absent from
  reader input, retrieval empty by construction, alternative retrieval path unreachable.
- **Terra:** **A3** as well (revised 2026-09-26; first written A2). Its 42 unlogged calls to
  `read_file`, `run_shell` and `review_own_conversations` could not have returned anything: the
  relay's capability gate (`relay/capabilities.py`, live since 2026-08-07) treats the eval interface
  `longmemeval` as untrusted and refuses every tool outside a memory-read allowlist. The 2026-09-26
  smoke run with full tool logging shows exactly those refusals. The remaining allowed tools
  (`read_memory`, `read_tacit`, `read_timeline`) read the empty test root. So terra's inputs are
  lost but every output is determined: refusal or empty.
- **Judge:** unchanged, J1. Nothing here touches the correctness labels.

## Wrong turns this should prevent

- Do not read the 58 `search_memory` events as evidence retrieval was attempted against the
  history. It was attempted against an empty fact store.
- Do not read "the fact was in the injected database" as "the fact was available to a retrieval
  call". The FTS index held it; nothing the readers called could read that index.
- Do not treat the 97/160 boundary as a soft association. Under this loader it is the hard edge
  of the reader's input.
- Do not expect terra-side tool inputs to appear. They are gone.

## What the next run must change

1. Under `--no-extract`, route `search_memory` to the FTS archive and pass the case's user id.
   **Done 2026-09-26:** `runner.py --search-archive` serves `search_memory` from
   `SessionStore.retrieve_relevant_sessions` under the case user, ahead of the tool dispatcher. The
   `retrieve_sessions` user-id hardcode is also fixed in the agent, but note that tool is not on the
   untrusted allowlist, so under the eval interface the routing in the harness is what makes
   retrieval reachable.
2. Log tool inputs **and outputs** with the case id, to the results directory, not the temp root.
   **Done:** `tools_<ts>.jsonl`.
3. Log the reader request body per call. **Done:** `requests_<ts>.jsonl`, the exact messages list
   as sent.
4. Disable MCP for the eval. **Done:** default `--no-mcp`.
5. Keep the session log. **Done:** copied to `sessions_<ts>/`; `--keep-tmp` keeps the whole root.
6. Add a second rater before reporting hand-judged numbers.
