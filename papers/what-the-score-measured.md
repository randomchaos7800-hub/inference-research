# What the Score Measured: Failure Attribution in an Agent Memory Evaluation

**Dino Vitale**  
Boundary Labs, Airway Heights, WA  
research@boundarylabs.org  
ORCID: 0009-0001-5590-3296

**Baixin Guo**  
Independent researcher

*Preprint — DRAFT, pending co-author review of this text*  
*September 2026*  
*License: CC BY 4.0*

---

## Abstract

We ran a memory benchmark against a deployed AI agent with three different reader models and got 36%, 40% and 40%. The natural reading is that the reader model barely matters for memory recall. It was wrong.

An external collaborator, given only the public artifacts, audited what those artifacts could support and concluded that the evaluation could not distinguish a retrieval failure from a memory failure from a reader failure, because the harness logged that a search tool ran but not what it asked or returned. That audit was correct, and it prompted us to reconstruct the intermediate states from the agent's source code. The reconstruction found that both of the agent's retrieval paths were structurally inert under the tested condition: the search tool the readers called queried an extracted-fact store that was empty by construction, and the only tool that could read the session archive was never called and carried a hardcoded user identifier the harness did not use. No reader could reach a fact outside its context window. The evaluation had been measuring context-window membership for all three readers, which is why they agreed.

We instrumented the harness, fixed both defects, and reran the same 25 cases across six conditions with controls. Without retrieval, two readers score identically at 40%. With retrieval reachable, they diverge to 48% and 76%. A single-variable comparison — same reader, byte-identical prompt, the same eleven cases searched — moves one reader from 40% to 76% by changing only whether its search reached the archive.

We decompose the outcome into three gates: deciding to search, writing a query that retrieves, and using the retrieved fact. The readers are near-identical at the second gate and diverge by a factor of four at the third. One reader made zero search calls across two full runs despite an explicit instruction to search, on a prompt byte-identical to one that produced eleven searches from a different reader. And one reader, given working retrieval, converted abstentions into fabrications on exactly the cases where retrieval succeeded.

The contributions are: a case in which a null result was an artifact of an unengaged mechanism; a four-axis rubric separating outcome, evidence availability, attribution confidence and judge reliability; a four-rater blind judging protocol over 150 predictions; and a specification of what an agent memory evaluation must log to make failure attribution possible at all.

All artifacts, including per-case tool traces and every rater's raw labels, are public.

---

## 1. Introduction

Agent memory evaluations report a score. An agent is given a history, asked a question whose answer lies somewhere in that history, and scored on whether it produces the answer. The score is an end-to-end measurement: it summarises everything between the stored fact and the emitted token.

A wrong answer can arise because the fact was never stored, because retrieval was never attempted, because retrieval was attempted and returned nothing, because it returned the fact but the fact never entered the model's input, or because it entered the input and the model did not use it. A score cannot distinguish these. Neither can a score that is stable across conditions.

In September 2026 we ran a 25-question subset of LongMemEval against a deployed agent, holding the agent, its memory and the question set fixed, and varying only the reader model. The three readers scored within four points of each other. We published that as evidence that the reader mattered little, which was a claim about mechanism drawn from a pattern in outcomes.

An independent collaborator, working only from the published artifacts, told us that claim was not identifiable from the evidence. He was right. **When every arm of an evaluation agrees, the first hypothesis should be that the mechanism under test was not engaged.** Agreement across conditions is weak evidence that a variable does not matter, and a reason to test whether something upstream of it stayed constant. Separating those two explanations requires logging the intermediate states. Ours did not.

---

## 2. Setup

### 2.1 The system under test

The agent is a deployed, always-on assistant with persistent memory, running continuously since February 2026. Its memory layer has two parts: a SQLite store of raw conversation history with a full-text index, and a store of facts extracted from that history into per-entity JSON files. It exposes several memory tools to the reader model, of which two matter here: `search_memory`, which searches the extracted-fact store, and `retrieve_sessions`, which runs a BM25 query against the full-text index over raw history.

The reader model is swappable. The rest of the system — memory, prompt documents, tool definitions, retrieval code — is held fixed when the reader changes.

### 2.2 The benchmark

We use 25 `single-session-user` questions from the cleaned LongMemEval `s` split. For each case the harness writes that case's haystack sessions into an isolated database using the dataset's own timestamps, backfills the full-text index, and asks the question through the agent's normal response path. Runs reported here use `--no-extract`, which skips the extraction step, so the agent answers from raw session history plus retrieval tools rather than from extracted facts.

Each case's haystack is roughly 45 to 57 sessions, 470 to 620 turns. The answer to each question lies in one identified session somewhere in that history.

### 2.3 Scoring

Two measures are recorded and kept separate. `score_exact` is a deterministic text comparison: after normalisation it awards 1.0 for the expected answer appearing as a substring and partial credit for word overlap. Hand judgment is binary under a stated rule: correct if and only if the answer states the expected fact; an "I don't have that" is a miss regardless of what the scorer says.

The two disagree, in both directions. In the September run `lme_0014` received exact scores of 1.0 from two readers whose answers were hand-judged wrong, because the string "10%" appeared inside an answer denying any knowledge of the fact. We report both measures throughout and never reconcile them into one number.

---

## 3. The September run and what it appeared to show

Three readers, same agent, same memory, same 25 questions.

| Reader | Harness exact | Hand-judged |
|---|---|---|
| gpt-5.6-terra | 0.34 | 9/25 (36%) |
| claude-sonnet-5 | 0.48 | 10/25 (40%) |
| claude-opus-5 | 0.44 | 10/25 (40%) |

The same 15 cases are misses for both Claude readers. Terra misses those 15 plus one more.

We also recorded where each case's answer session sits in the injected history, as the number of turns from the end of that history to where the session starts. Every case answered correctly by at least one reader has its answer session starting no more than 97 turns from the end, and every case missed by all three has it starting at least 160 turns from the end. The logs show each reader call carrying 102 to 114 messages, and record that a memory search tool ran 58 times across the three runs.

From this we wrote that the result was the context window rather than retrieval, and that the search tool never surfaced a fact from beyond the window.

Both of those are causal claims. The receipts support neither. The position pattern is an association across 25 cases, consistent with several mechanisms. And "never surfaced a fact" is a statement about what a tool returned, which the logs do not record: they record that the tool ran, as a bare line with a timestamp and a name.

---

## 4. The observability audit

In late September an early-career researcher, Baixin Guo, contacted the lab after reading its collaboration page. We scoped a two-week deliverable: a written critique of the evaluation, a rubric, a test matrix and a judge-reliability plan, working from public artifacts only — the harness, the runs, the per-case outputs, the debug logs and the hand judgments. No access to the agent's memory or to lab machines.

His first document mapped the observability boundary. Its finding, in his terms: the artifacts expose evaluation inputs, expected answers, generated responses, automated scores, human judgments, answer-session locations and execution-level tool events; they do not expose retrieval queries, retrieval candidates, retrieval outputs, memory provenance or the exact reader context. Therefore the evidence supports conclusions about whether an agent succeeded or failed under a condition, but does not determine which internal stage is responsible.

That finding contradicts what we had published. He declined to infer a mechanism from the outcome pattern, and said so explicitly. We corrected the README the same day and credited the audit in the commit.

The constraint that made the audit useful was the one that looked most limiting. He could not see the code, which forced him to state precisely what the artifacts supported. An author of those artifacts is badly positioned to assess that boundary.

---

## 5. A rubric for failure attribution

His second document proposed a four-axis annotation applied per case, alongside the existing scores rather than in place of them.

**Outcome correctness** classifies the answer: correct, incorrect, disagreement between available measures, or unrated. It does not explain the cause.

**Evidence availability** describes the strongest case-linked evidence about the path from source history to answer. E0 is outcome only. E1 documents that the source session was in the injected history and where. E2 shows a retrieval tool was invoked, by name, without its query or result. E3 exposes the retrieval input and returned items. E4 establishes the relevant content in the actual model input.

**Attribution confidence** describes what the evidence licenses. A0 is not identifiable. A1 is a suggestive association consistent with several mechanisms. A2 localises a failure to one stage while adjacent stages remain unobserved. A3 covers source availability, retrieval, reader exposure and outcome well enough to rule out material alternatives for that case.

**Judge confidence** describes confidence in the correctness label itself: J0 no usable judgment, J1 single-pass with no second rater, J2 corroborated with no unresolved disagreement, J3 replicated with high agreement and documented resolution.

Aggregate tool counts do not justify assigning E2 to an individual case unless a specific event can be linked to that case; our September log lines carry no case identifier, so they cannot. And agreement between the exact scorer and a human label does not raise judge confidence, because the scorer is not an independent rater and the two demonstrably disagree.

Under this rubric the September run is E1 and A0 per case, with the cross-case position pattern annotatable as A1, and J1 throughout.

---

## 6. Reconstruction

We hold the source code, so we asked what the code paths determine, regardless of what was logged.

**The reader's input was the last 100 messages by timestamp.** The context loader first requests "today's" messages. The injected history carries its original 2023 dataset dates, so that set is empty and the loader falls through to a branch that selects the 100 most recent rows. This explains the 97/160 boundary: an answer session beginning within 100 turns of the end is in the reader's input, one beginning beyond it is not. For this condition, "inside the context window" and "present in the reader's input" are the same statement.

**The search tool the readers called never searched the injected history.** `search_memory` queries the extracted-fact store. The harness pointed that store at a fresh directory and ran with extraction skipped, so it was empty for the entire run. All 58 calls returned "No memories found", by construction, not by search failure.

**The tool that reads the history index was never called, and could not have worked.** The `FTS backfill` line in every run builds an index that only `retrieve_sessions` reads. No reader invoked it. Separately, that tool passed a hardcoded user identifier while the harness injects each case under its own per-case identifier, so it would have matched zero rows had it been called.

Neither retrieval path reached the store that held the facts, so these misses are not retrieval failures.

### 6.1 Recovering the queries

One private log survived that the public folder did not have. Two of the three readers ran through a local bridge, and that bridge recorded every tool call with its arguments. From it we recovered every search keyword those two readers issued, timestamp-linked to cases.

Sonnet searched on 14 of its 15 misses and on none of its hits. Opus searched on 8 of 15.

We then rebuilt each case's database from the public dataset, constructed the same full-text index, and replayed the readers' own keywords through the query that `retrieve_sessions` uses, under the correct per-case identifier. The answer-bearing session ranked in the top two results for 20 of the 22 searched misses. Under the hardcoded identifier, zero of 40 queries matched anything.

The readers had formed usable queries. No tool they could call queried the index that held the answer: one searched a different store, the other used an identifier the harness never assigned.

### 6.2 What this does to the attribution

For the two Claude readers this moves the 15 misses from A0 to A3: the fact was present in the history, absent from the reader's input, the only search used was empty by construction, and the alternative retrieval path was unreachable. For the third reader the same mechanisms apply, but 42 of its tool inputs were unrecoverable because the harness deleted the temporary directory holding its tool log at the end of each run.

That reader's attribution was subsequently also resolved to A3, for a reason that emerged only from the instrumented rerun described below: the agent's capability gate treats the evaluation interface as untrusted and refuses every tool outside a memory-read allowlist. The unlogged calls were refusals. Their inputs are lost; their outputs are determined.

---

## 7. The instrumented rerun

### 7.1 Changes

We repaired two defects and added instrumentation.

In the agent: `retrieve_sessions` now passes the caller's user identifier rather than a hardcoded one. Behaviour in production is unchanged, since there the identifier is always the same value.

In the harness: every tool call is logged with its full input, full output, duration and case identifier; every reader request is logged as the message list actually sent; a `--search-archive` flag serves `search_memory` from the full-text session archive under the case's own identifier, which is the correct wiring for an extraction-skipped run; the model-context-protocol servers are disabled during evaluation, closing a path that had pointed at the operator's real filesystem; and the session log is preserved rather than deleted.

### 7.2 Design

Six runs over the same 25 cases. Two readers were run in both conditions. The third made no search call, and archive routing only fires on a search call, so its archive run is its own control.

| Label | Reader | Archive routing |
|---|---|---|
| terra control | gpt-5.6-terra | off |
| terra archive | gpt-5.6-terra | on |
| opus control | claude-opus-5 | off |
| opus archive | claude-opus-5 | on |
| sonnet archive | claude-sonnet-5 | on |
| sonnet repeat | claude-sonnet-5 | on |

### 7.3 Results

Hand column is the majority of four blind raters. "Delivered" counts how many of the 15 cases whose answer session lies outside the reader's input window had that session returned by a search. "Converted" is how many of the delivered cases were then answered correctly.

| Run | Hand | Exact | Searched (of 15) | Delivered | Converted | In-window |
|---|---|---|---|---|---|---|
| terra control | 10/25 (40%) | 0.42 | 9 | 0 | — | 10/10 |
| terra archive | 12/25 (48%) | 0.48 | 10 | 9 | 2 | 10/10 |
| opus control | 10/25 (40%) | 0.42 | 11 | 0 | — | 10/10 |
| **opus archive** | **19/25 (76%)** | 0.73 | 11 | 10 | **9** | 10/10 |
| sonnet archive | 9/25 (36%) | 0.38 | 0 | 0 | — | 9/10 |
| sonnet repeat | 9/25 (36%) | 0.38 | 0 | 0 | — | 9/10 |

### 7.4 The control pair

Without retrieval, terra and Opus both score 40%, both at 0.42 exact, both 10 of 10 on in-window cases. This reproduces the September result and explains it: both readers are equally capable of reading a fact out of their context window, and that is all the September evaluation measured.

With retrieval reachable they separate to 48% and 76%.

The two Opus runs differ in exactly one variable: the system prompt is byte-identical between them, the reader and question set are the same, and Opus chose to search on the same eleven cases in both. In the control, all 24 of its search calls returned nothing; with routing on, the same search behaviour returned the answer-bearing session ten times. The outcome moves from 40% to 76%.

The September number is no longer load-bearing for the comparison. The agent's prompt documents change over time, and the September prompt was never recorded.

### 7.5 Three gates

Decomposing by stage, over the 15 out-of-window cases:

**Gate one, deciding to search.** Terra searched 9 in the control and 10 with routing on; Opus searched 11 in both; Sonnet searched 0 in two full runs. The split is close to bimodal.

**Gate two, writing a query that retrieves.** Terra issued 11 queries across its 10 searched cases, a mean of 1.1, typically a single keyword. Opus issued 40 across its 11, a mean of 3.6 and a maximum of 8, including attempts to guess the phrasing the source would use. Despite that difference their retrieval success is nearly equal: 9 of 10 and 10 of 11. Query style mattered much less than we expected. The single case neither reaches, a question about a previous occupation, is the same case the offline keyword replay could not reach.

**Gate three, using the fact.** Terra converted 2 of 9 delivered facts. Opus converted 9 of 10.

Retrieval was effectively equalised, and conversion of delivered facts diverged by a factor of four.

### 7.6 Failure modes with the fact present

Of terra's seven failures on delivered facts, five are abstentions with the answer session in context — it had the text describing a daily commute and replied that it had no commute recorded. Two are fabrications: it answered "Tennis Warehouse" where the history says the sports store downtown, and "Chill Vibes" where the playlist is Summer Vibes.

Both fabrications occur only on cases where retrieval succeeded. Terra's own control run contains none, and none appear across the 75 September predictions. Giving terra working retrieval converted abstentions into fabrications.

Under binary scoring, "I don't know" and a fabricated store name are both misses. Operationally an abstention and a fabricated store name are different failures, and the intervention that improved the aggregate score also introduced the worse of the two.

Opus's single failure with the fact present is the other kind: asked for a bike count, it reported the one bike it could identify and stated plainly that it had no inventory and would not give a number.

### 7.7 An observation we cannot explain

Sonnet made zero tool calls across two full runs and across a direct replay of its own recorded request payload against the bridge. A control probe with a short prompt does produce a tool call through the same bridge, so this is not a transport failure. In September, the same reader on the same cases searched 30 times.

Its September 26 system prompt is byte-identical to the one Opus received, and contains an explicit mandatory directive to call the memory tools before answering about any person, project or event. The directive was in the prompt. The reader did not act on it, in either run.

September's request bodies were never recorded, so the two prompts cannot be compared and this is not diagnosable after the fact. From this run forward the prompt is captured per call.

---

## 8. Judge reliability

Guo's fourth deliverable specified a judging protocol: identical written criterion for every rater, independent labels recorded before any comparison, blinding to reader identity and automated score, randomised item order, raw labels and rationales preserved separately, disagreements retained and classified, adjudication by an uninvolved third party, and raw agreement reported before adjudication.

We applied it to all 150 predictions from the six rerun conditions. Four raters: the original human judge; and three language models from three different providers, added deliberately so that no rater shares a model family with more than one reader under test. Items were shuffled with a fixed seed and relabelled. Raters saw the question, the expected fact and the answer, and nothing else.

| Pack | Items | Unanimous | Pairwise Cohen's κ |
|---|---|---|---|
| Five-run pack | 125 | 122 | 0.952 – 1.000 |
| Control pack | 25 | 25 | 1.000 |

Three disagreements in 150, all in one class: an answer that states the expected fact while explicitly disclaiming confidence in it.

### 8.1 An unscorable item

The sharpest of the three is a defect in the benchmark item rather than in any reader.

The question asks where a $5 coffee creamer coupon was redeemed. The gold answer is "Target". The source session does not say that. It says three things in sequence: that the user uses Target's coupon app, that they redeemed a $5 coffee creamer coupon last Sunday, and that they shop at Target every other week. The gold label is itself an inference from adjacency.

In the archive run, Opus answered that Target was the likely answer and explicitly flagged that it was inferring rather than recalling. The human rater scored this a miss; all three model raters scored it correct. In the control run, the same reader with the same in-window evidence stated "Target" flat, with no basis offered, and every rater scored it correct.

For the same reader on identical evidence, the human rater's labels rewarded the confident phrasing and penalised the accurate one. Under Guo's ambiguity handling this item does not support a stable binary judgment and should be marked unscorable rather than forced. Excluding the item for all six runs gives 18/24, 11/24, 9/24, 9/24, 9/24 and 9/24; the pattern is unchanged.

We keep the human rater's label as recorded, with the disagreement and its reasoning in the published log. A rater stricter than the written rule, with a documented reason, is the outcome the protocol is designed to surface.

---

## 9. What a memory evaluation must log

The following is the minimum needed to distinguish the failure modes this paper separates. Each item exists because its absence cost us something concrete.

1. **Tool inputs and outputs, per case, with a case identifier.** Tool names alone cannot distinguish a dead retrieval path from a live one that found nothing. This is the defect that produced the original error.
2. **The reader request body, per call.** Without it, "the fact was in the history" cannot be upgraded to "the fact reached the model", and prompt changes between runs are undetectable.
3. **Retrieval results, not just retrieval calls.** A returned result set is the difference between E2 and E3, and between A0 and A2.
4. **A negative control per condition.** The comparison that carries this paper is the pair that differs in one variable. Without the control, its headline number would rest on a measurement taken five days earlier under an unrecorded prompt.
5. **Logs written outside the run's temporary state.** Our harness deleted the directory holding one reader's tool log at the end of each run, permanently losing 42 tool inputs.
6. **An isolated filesystem surface.** The evaluation ran with a file server rooted at the operator's real code and memory trees. Nothing came of it, but it is a contamination path.
7. **At least two independent raters before any hand-judged number is reported.** Single-pass judging is one rater's label, and the disagreements are where the benchmark's ambiguous items show up.

One further trap: the agent assembles two always-on prompt directives by iterating an unordered set, and language runtimes that randomise string hashing per process emit them in a different order each run. Content identical, hash different. Anything comparing prompts across runs must canonicalise first or it will read ordering noise as drift. We spent an hour on this before recognising it.

---

## 10. Limitations

**Scale.** Twenty-five questions of one type, from one split, against one agent. Every number here is a statement about these cases. The three-gate decomposition is a description of what happened in this run, not an established distribution.

**One agent architecture.** The window mechanism, the two-store memory design and the tool surface are properties of this system. The finding that a null result concealed an inactive mechanism generalises; the specific mechanism does not.

**Judge composition.** Three of four raters are language models. Blinding and independent labelling were enforced, but this is not a panel of human raters, and κ near 1.0 on 150 short factual items indicates the rule is unambiguous on this item type; it does not establish judge reliability generally. Harder question types will not behave this way.

**One unexplained result.** The Sonnet behaviour is reported, not explained, and the evidence needed to explain it was never recorded.

**No fixed-transcript reader comparison.** The cleanest test of gate three — freeze one transcript containing a retrieved fact and vary only the reader — is specified in Guo's test matrix and has not been run. Everything required to build it is in the published artifacts.

**Provenance of this document.** The reconstruction, the harness changes, the rerun and this text were produced by the first author working with a coding agent; the audit, rubric, test matrix and judging protocol are the second author's. The disagreement that started it was between the two of us and is recorded in the repository history.

---

## 11. Conclusion

We published a score that was stable across three reader models and read that stability as evidence about the models. It was evidence about the harness. Both retrieval paths were inert, so the benchmark measured which facts fell inside a 100-message window. Two readers scored 10 of 10 on those; the third scored 9.

With retrieval repaired, the same three readers score 36%, 48% and 76% on the same questions. One reader goes from 40% to 76% because its search reached the archive, with the system prompt byte-identical across the two runs. Another declines to search at all, against an explicit instruction. A third, with working retrieval, fabricated on precisely the cases where retrieval succeeded.

Persistent memory raised one reader from 40% to 76% and left another at 36%. Neither "the model doesn't matter" nor "the model is what matters" holds for these results. The unit of evaluation is the system, and the reader decides whether the rest of the system is consulted at all.

The methodological claim is narrower. A null result in an agent evaluation is not evidence that a variable is unimportant until you can show the mechanism it acts on was engaged. Showing that requires logging the middle of the pipeline. Ours did not, until an outside reader pointed out that the conclusion did not follow from the receipts.

---

## Artifacts

All data, code and rater labels are public.

- Rerun, six conditions, per-case tool traces, request metadata, both blind judging packs with every rater's raw labels: `longmemeval/runs/2026-09-26/`
- September run, offline retrieval replay, the reconstruction, judge reliability pass, per-case rubric annotations: `longmemeval/runs/2026-09-21/`
- Harness: `longmemeval/harness/`
- Repository: https://github.com/randomchaos7800-hub/inference-research

Reader request bodies are published as metadata with hashed system prompts. The raw logs contain the agent's private prompt document and roughly 34 MB of dataset content reproducible from the public split and the harness. Paths in logs and tool arguments are rewritten to a neutral convention; every question, expected answer, prediction and score is byte-identical to the originals, verified record by record.
