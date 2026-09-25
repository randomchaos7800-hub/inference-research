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

## What survives and what does not

- **Survives:** Sonnet and Opus search keywords with timestamps (bridge log); per-call message
  and prompt-character counts; everything in the public run folder.
- **Lost:** terra's 18 `search_memory` keywords, its 19 `run_shell` commands and 23 `read_file`
  paths. The agent's per-session tool log (which records tool inputs truncated to 200 chars) was
  written under the run's temp directory, and `runner.py` deletes that directory at the end of
  each run (`shutil.rmtree(run_tmp)`). Nothing else recorded tool inputs for the terra reader.
- **Never recorded anywhere:** tool outputs, and the exact reader request body. For this run both
  are reconstructible from code (mechanisms 1–2), not from a trace.

Terra's `read_file` calls went through an MCP filesystem server rooted at the agent's real code
and memory trees, not the test memory root. Those trees contain none of the dataset's facts, so
this cannot have produced a correct answer, but it is a contamination path the next harness must
close.

## Placement in the Failure Attribution Rubric

Using Guo's four axes for the September run:

- **Sonnet, Opus:** E1 from the public receipts alone; **E3 for the 22 searched cases** with this
  folder (query known, result known by construction); E4 derivable for all 25 (mechanism 1).
  Attribution moves from **A0 to A3** for the 15 misses: source present in history, absent from
  reader input, retrieval empty by construction, alternative retrieval path unreachable.
- **Terra:** **A2**. Same mechanisms apply and its hits match the Claude readers' minus
  `lme_0007`, but 42 tool inputs are unrecoverable and one of those tools was a shell.
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

1. Under `--no-extract`, route `search_memory` to the FTS archive (or expose `retrieve_sessions`
   as the primary search) and pass the case's user id.
2. Log tool inputs **and outputs** with the case id, to the results directory, not the temp root.
3. Log the reader request body (or a hash plus message list with ids) per call.
4. Point the MCP filesystem root at the test memory root, or disable it for the eval.
5. Keep `run_tmp`, or copy the session log out before deleting it.
6. Add a second rater before reporting hand-judged numbers.
