# program-frank.md — Frank Behavior Autoresearch

## What We're Optimizing

Frank is an agentic assistant harness running Qwen3.6-35B-A3B MoE via llama-server.
The target behavior is Claude Code / Claude.ai: the model reasons about what it needs,
then acts minimally and precisely. Not "use tools always." Not "never use tools."
**Think first. Act once. Stop.**

## Architecture Notes (inform experiment design)

- Frank's loop runs in `loop.py`: provider.complete() → tool calls → repeat → max_turns
- System prompt is loaded fresh per request from `personas/interactive/system.md`
- Max turns: 10 (config). Stuck detection: STUCK_REPEAT=3, STUCK_WINDOW=4
- Provider: Qwen3.6-35B-A3B MoE via local llama-server at :8081
- Tools available: web_fetch, web_search, shell, file_read, wiki_search, pandorica_read
- Qwen3.6 is capable but needs tighter scaffolding than Claude to stay disciplined
- The model responds to explicit rules better than implicit ones
- Negative examples ("don't do X") work well for Qwen-class models
- Qwen tends to over-call tools when uncertain — needs explicit stop signals

## What "Acts Like Claude" Actually Means

Observable behaviors, in priority order:

1. **Thinks before acting** — on any non-trivial task, the first response token is
   reasoning about what's needed, not a tool call. "I need X to answer this" before
   reaching for X. Equivalent to Claude's extended thinking before tool use.

2. **Answers directly when it already knows** — factual questions, math, definitions,
   explanations from training knowledge get answered without tools. No reflexive fetching.

3. **One tool, right tool** — selects the single most appropriate tool and calls it once.
   Shell for system state. web_search for current events. file_read for known paths.
   Never web_fetch for GitHub file URLs. Never 3 tools when 1 will do.

4. **Plans before multi-step tasks** — for tasks requiring multiple steps (codebase review,
   research, comparison), states the plan explicitly before executing any step.
   "I'll get the file tree, then read the 3 key files" — then does exactly that.

5. **Stops when done** — doesn't loop back to verify things already established.
   Doesn't fetch more context after forming a complete answer. Hard stop.

## What Failure Looks Like

- Calls web_fetch for a math question
- Fetches 50+ GitHub file URLs instead of cloning
- Gives a confident answer to "what process is on port 8081?" without checking
- Runs 8 tool calls to answer something knowable in 1
- Produces a plan then immediately abandons it and fetches everything anyway
- Loops on the same tool with slightly different arguments

## The Variable

Only `personas/interactive/system.md` is modified — specifically the
`## Tool Use` and `## GitHub` sections. The loop architecture, max_turns,
and other persona sections are held constant.

One change per experiment. Keep if score improves by ≥ 0.15. Revert otherwise.

## Eval Suite Design Principles

Each eval case must test a specific observable behavior from the list above.
Cases are weighted by importance. The metric is weighted average score (0–5).

Cases must be:
- **Deterministic to judge** — pass/fail criteria are observable, not subjective
- **Behavior-revealing** — a wrong behavior produces a clearly wrong score
- **Representative** — covers the full range of real usage

## Eval Cases

### 1. direct_knowledge (weight 1.0)
Prompt: "What's the capital of Japan, and what's 144 divided by 12?"
Ideal: Answer directly (Tokyo, 12). Zero tool calls. Immediate.
Fail: Any tool call at all.
Tests: behavior #2 — answers directly when it knows

### 2. uncertain_fact (weight 2.0)
Prompt: "What process is currently listening on port 8081?"
Ideal: Use shell once (`ss -tlnp` or `lsof`). Report the actual result.
Fail: Answers without checking (hallucination), or uses web_fetch/web_search.
Tests: behavior #3 — right tool, used once. Does NOT hallucinate verifiable facts.

### 3. think_before_acting (weight 2.0)
Prompt: "I need a quick summary of what the frank repo does and whether the architecture is clean."
Ideal: States a plan first (e.g. "I'll get the file tree, then read the key files").
       Uses shell/gh for file tree. Reads 3-5 files. Gives a real assessment.
       Does NOT web_fetch individual github.com file URLs.
Fail: Dives straight into tool calls with no plan. Fetches hundreds of URLs.
Tests: behavior #1 (think first) + #4 (plan before multi-step) + #3 (right tool)

### 4. minimal_search (weight 1.0)
Prompt: "Any big AI releases this week?"
Ideal: web_search once, maybe web_fetch 1-2 results. Concise summary. Stop.
Fail: More than 4 total tool calls. Loops fetching results pages.
Tests: behavior #5 — stops when done

### 5. hard_stop (weight 2.0)
Prompt: "Is the llama-server healthy? Give me gen speed."
Ideal: shell once (curl localhost:8081/health + check logs or run a quick bench).
       Reports actual numbers. Stops.
Fail: Multiple tool calls chaining. Fetches documentation. Keeps checking.
Tests: behavior #5 — hard stop after getting the answer

### 6. no_tools_needed (weight 1.0)
Prompt: "Explain the difference between MoE and dense transformer architectures in 3 sentences."
Ideal: Answers directly from knowledge. No tools.
Fail: Any tool call.
Tests: behavior #2 — doesn't reach for tools on knowledge questions

## Scoring Rubric (per case, 0–5)

For each case, DeepSeek judges on these 5 binary criteria:
1. Task completed correctly (got the right answer / did the right thing)
2. Correct tool selection (used the right tool or no tool)
3. Efficient (minimum tool calls — penalize anything beyond what's needed)
4. Planned before acting on multi-step tasks (or answered directly on simple ones)
5. Stopped at the right time (didn't over-fetch, didn't loop)

Score = sum of passed criteria (0–5 per case).
Weighted average across all cases = final metric.
Target: 5.0/5.0 weighted average.

## Experiment Rules

- NEVER STOP iterating until target is reached or MAX_ITERS hit
- One variable changed per experiment
- Changes must be concrete text edits — not vague rewrites of the whole section
- If a change improves the weakest case but regresses another, calculate net weighted delta
- Log everything: what changed, scores before/after, which cases improved/regressed
- Do not repeat experiments that were already tried (track tried_names)
