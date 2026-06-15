#!/usr/bin/env python3
"""
Karpathy-style autoresearch for Frank system prompt behavior.

Architecture notes (from program-frank.md):
  - Frank routes through local-proxy at :8010
  - Qwen needs tighter scaffolding than Claude — responds well to explicit rules
  - Negative examples ("don't do X") work well for Qwen-class models
  - Qwen over-calls tools when uncertain — needs explicit stop signals
  - System prompt loaded fresh per request from personas/interactive/system.md
  - Max turns: 10 | Stuck detection: STUCK_REPEAT=3, STUCK_WINDOW=4
  - Only ## Tool Use and ## GitHub sections are modified per experiment

Target: weighted average score 5.0/5.0 across 6 behavior-specific eval cases
Variable: ## Tool Use + ## GitHub sections of system.md
Loop: modify → eval → keep if delta ≥ 0.15 → revert otherwise → repeat
"""

import json, time, csv, subprocess, re
from datetime import datetime
from pathlib import Path
import requests

# ── Config ────────────────────────────────────────────────────────────────────

FRANK_API         = "http://100.94.10.36:8890"
OPENROUTER_API    = "https://openrouter.ai/api/v1"
JUDGE_MODEL       = "deepseek/deepseek-chat"
SYSTEM_PROMPT     = Path("/home/dino/frank/personas/interactive/system.md")
PROGRAM_DOC       = Path("/home/dino/inference-research/program-frank.md")
LOG_FILE          = Path("/home/dino/inference-research/autoresearch-frank-log.md")
RESULTS_TSV       = Path("/home/dino/inference-research/autoresearch-frank-results.tsv")
MAX_ITERS         = 60
IMPROVE_THRESHOLD = 0.10
REQUEST_TIMEOUT   = 180

OPENROUTER_KEY = subprocess.check_output(
    ["/bin/bash", "-c", "~/.vault/vault.sh get openrouter_api_key 2>/dev/null"],
    text=True
).strip()

if not OPENROUTER_KEY:
    raise RuntimeError("No openrouter_api_key in vault — check ~/.vault/")

# ── Eval suite (mirrors program-frank.md) ────────────────────────────────────

EVAL_SUITE = [
    {
        "id": "direct_knowledge",
        "weight": 1.0,
        "prompt": "What's the capital of Japan, and what's 144 divided by 12?",
        "ideal": "Answer directly: Tokyo, 12. Zero tool calls. No fetching.",
        "fail_signals": ["web_fetch", "web_search", "shell", "file_read", "wiki_search"],
    },
    {
        "id": "uncertain_fact",
        "weight": 2.0,
        "prompt": "What process is currently listening on port 8010?",
        "ideal": "Use shell once (ss -tlnp or lsof). Report actual result. Do not guess.",
        "fail_signals": ["answers without checking", "web_fetch", "web_search", "hallucinated"],
    },
    {
        "id": "think_before_acting",
        "weight": 2.0,
        "prompt": "I need a quick summary of what the frank repo does and whether the architecture is clean.",
        "ideal": "States a plan first. Uses shell/gh for file tree. Reads 3-5 key files. Real assessment. No web_fetch of github.com file URLs.",
        "fail_signals": ["web_fetch ×", "fetching URL ×", "no plan stated", "github.com raw"],
    },
    {
        "id": "minimal_search",
        "weight": 1.0,
        "prompt": "Any big AI releases this week?",
        "ideal": "web_search once, web_fetch 1-2 results max. Concise summary. Stops.",
        "fail_signals": ["more than 4 tool calls", "fetching URL ×[5-9]", "fetching URL ×[1-9][0-9]"],
    },
    {
        "id": "hard_stop",
        "weight": 2.0,
        "prompt": "Is the llama-server healthy? Give me the current gen speed.",
        "ideal": "shell once or twice (curl health + check logs). Reports actual numbers. Stops immediately after.",
        "fail_signals": ["more than 3 tool calls", "web_fetch", "keeps checking after getting answer"],
    },
    {
        "id": "no_tools_needed",
        "weight": 1.0,
        "prompt": "Explain the difference between MoE and dense transformer architectures in 3 sentences.",
        "ideal": "Answers directly from knowledge. No tools whatsoever.",
        "fail_signals": ["web_fetch", "web_search", "wiki_search", "shell"],
    },
]

JUDGE_SYSTEM = """\
You are evaluating an AI assistant called Frank on specific behavioral criteria.
Score on exactly 5 binary criteria (0 or 1 each):
1. Task completed correctly (right answer, right action)
2. Correct tool selection (right tool or no tool as appropriate)
3. Efficient (minimum tool calls — penalise anything beyond what's needed)
4. Planned before acting on multi-step tasks, OR answered directly on simple ones
5. Stopped at the right time (no over-fetching, no looping, no unnecessary verification)

Return JSON only, no other text:
{"scores": [0_or_1, 0_or_1, 0_or_1, 0_or_1, 0_or_1], "reasoning": "one concise sentence"}"""

HYPOTHESIS_SYSTEM = """\
You are optimizing a system prompt for Frank, an AI assistant running Qwen3.6-35B MoE.

Architecture facts that inform your suggestions:
- Qwen responds well to explicit, concrete rules — not vague principles
- Negative examples ("never do X") are effective for Qwen-class models
- Qwen over-calls tools when uncertain — explicit stop signals help
- The target behavior is: think first, act once with the right tool, stop

You will suggest ONE specific, targeted change to the ## Tool Use or ## GitHub section.
The change must be concrete text — exact wording to add, remove, or replace.
Do not rewrite the whole section. Change one thing.

Return JSON only:
{"name": "short_experiment_name", "instruction": "exactly what to change and where"}"""

APPLY_SYSTEM = """\
Apply the instruction to the system prompt.
Return the complete modified system prompt — nothing else, no explanation, no preamble."""

# ── API helpers ───────────────────────────────────────────────────────────────

def judge_complete(system: str, user: str, max_tokens: int = 400) -> str:
    r = requests.post(
        f"{OPENROUTER_API}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "HTTP-Referer": "https://vitale.systems",
            "X-Title": "Frank Autoresearch",
        },
        json={
            "model": JUDGE_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"] or ""


def frank_chat(prompt: str) -> tuple[str, str]:
    """
    Send prompt to Frank via streaming. Returns (full_response, tool_summary_line).
    Streaming is required to capture the ↳ tool summary that serve.py embeds in the
    SSE content — non-streaming responses don't include it.
    """
    try:
        r = requests.post(
            f"{FRANK_API}/v1/chat/completions",
            json={"model": "frank", "messages": [{"role": "user", "content": prompt}], "stream": True},
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        chunks: list[str] = []
        for raw_line in r.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload.strip() == "[DONE]":
                break
            try:
                obj = json.loads(payload)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                text = delta.get("content") or ""
                if text:
                    chunks.append(text)
            except json.JSONDecodeError:
                pass
        content = "".join(chunks)
        tool_line = next((l.strip() for l in content.split("\n") if "↳" in l), "")
        # Strip the tool summary line from content before passing to judge
        clean = "\n".join(l for l in content.split("\n") if "↳" not in l).strip()
        return clean, tool_line
    except Exception as e:
        return f"ERROR: {e}", ""


def extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])

# ── Eval ──────────────────────────────────────────────────────────────────────

def judge_response(case: dict, response: str, tool_line: str) -> tuple[float, str]:
    user = f"""Eval case: {case['id']}
Prompt: {case['prompt']}
Ideal behavior: {case['ideal']}
Failure signals: {', '.join(case['fail_signals'])}
Frank's tool summary: {tool_line or '(no tools used)'}
Frank's response (first 2000 chars):
{response[:2000]}"""
    try:
        raw = judge_complete(JUDGE_SYSTEM, user)
        result = extract_json(raw)
        return float(sum(result["scores"])), result["reasoning"]
    except Exception as e:
        return 0.0, f"judge error: {e}"


EVAL_RUNS = 3  # runs per case; averaged to reduce stochasticity noise


def run_eval() -> tuple[float, list[dict]]:
    results = []
    total_weight = sum(c["weight"] for c in EVAL_SUITE)
    weighted_sum = 0.0
    for case in EVAL_SUITE:
        log(f"  [{case['id']}] prompting Frank ({EVAL_RUNS}x)...", end="")
        run_scores = []
        run_reasonings = []
        best_tool_line = ""
        for _ in range(EVAL_RUNS):
            response, tool_line = frank_chat(case["prompt"])
            score, reasoning = judge_response(case, response, tool_line)
            run_scores.append(score)
            run_reasonings.append(reasoning)
            if tool_line:
                best_tool_line = tool_line
            time.sleep(2)
        avg_score = sum(run_scores) / len(run_scores)
        reasoning = run_reasonings[len(run_reasonings) // 2]  # median reasoning
        weighted_sum += avg_score * case["weight"]
        results.append({"id": case["id"], "score": avg_score, "weight": case["weight"],
                        "tool_line": best_tool_line, "reasoning": reasoning,
                        "runs": run_scores})
        log(f" {avg_score:.1f}/5 {run_scores} | {best_tool_line or 'no tools'} | {reasoning}")
        time.sleep(2)
    avg = weighted_sum / total_weight
    return avg, results

# ── Hypothesis ────────────────────────────────────────────────────────────────

def generate_hypothesis(eval_results: list[dict], history: list[dict],
                        tried: set) -> tuple[str, str]:
    weak = sorted([r for r in eval_results if r["score"] < 5.0],
                  key=lambda r: r["score"] * r["weight"])
    weak_text = "\n".join(
        f"- {r['id']} (weight {r['weight']}): {r['score']}/5 | {r['tool_line'] or 'no tools'} | {r['reasoning']}"
        for r in weak
    )
    history_text = "\n".join(
        f"- {h['name']}: {h['score_before']:.2f}→{h['score_after']:.2f} ({h['outcome']})"
        for h in history[-8:]
    ) or "none yet"
    tried_text = ", ".join(tried) if tried else "none"

    current_sections = _extract_variable_sections(SYSTEM_PROMPT.read_text())
    user = f"""Current ## Tool Use + ## GitHub sections:
{current_sections}

Weakest eval cases (highest priority first):
{weak_text}

Recent experiment history:
{history_text}

Already tried (do not repeat): {tried_text}

Suggest one targeted change that would most improve the weakest cases."""

    raw = judge_complete(HYPOTHESIS_SYSTEM, user, max_tokens=600)
    result = extract_json(raw)
    return result["name"], result["instruction"]


def apply_hypothesis(instruction: str) -> str:
    current = SYSTEM_PROMPT.read_text()
    return judge_complete(APPLY_SYSTEM,
                          f"System prompt:\n{current}\n\nInstruction: {instruction}",
                          max_tokens=3000)


def _extract_variable_sections(prompt: str) -> str:
    """Extract just the ## Tool Use and ## GitHub sections."""
    sections = []
    for section in ["## GitHub", "## Tool Use"]:
        start = prompt.find(section)
        if start == -1:
            continue
        end = prompt.find("\n## ", start + 4)
        sections.append(prompt[start:end if end != -1 else start + 2000])
    return "\n\n".join(sections)

# ── Logging ───────────────────────────────────────────────────────────────────

def log(text: str, end: str = "\n"):
    print(text, end=end, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(text + end)


def write_tsv(row: dict):
    is_new = not RESULTS_TSV.exists()
    with open(RESULTS_TSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=row.keys(), delimiter="\t")
        if is_new:
            w.writeheader()
        w.writerow(row)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    log(f"\n{'='*60}")
    log(f"autoresearch-frank  {datetime.now().isoformat()}")
    log(f"judge: {JUDGE_MODEL} | target: 5.0/5.0 | max_iters: {MAX_ITERS}")
    log(f"{'='*60}\n")

    best_prompt = SYSTEM_PROMPT.read_text()
    best_score = 0.0
    history: list[dict] = []
    tried: set[str] = set()

    # Baseline
    log("── BASELINE ──")
    best_score, baseline_results = run_eval()
    log(f"\nBaseline: {best_score:.2f}/5.0\n")
    write_tsv({"iter": 0, "name": "baseline", "score": best_score,
               "outcome": "BASELINE", "ts": datetime.now().isoformat()})

    if best_score >= 5.0:
        log("Already 5/5. Done.")
        return

    for i in range(1, MAX_ITERS + 1):
        log(f"\n── ITER {i}/{MAX_ITERS}  (best: {best_score:.2f}/5.0) ──")

        try:
            name, instruction = generate_hypothesis(baseline_results, history, tried)
        except Exception as e:
            log(f"Hypothesis failed: {e}")
            time.sleep(5)
            continue

        if name in tried:
            log(f"Already tried '{name}', skipping.")
            continue

        tried.add(name)
        log(f"Experiment: {name}")
        log(f"Change: {instruction[:300]}")

        try:
            new_prompt = apply_hypothesis(instruction)
            if len(new_prompt) < 200:
                raise ValueError(f"Apply returned suspiciously short prompt ({len(new_prompt)} chars)")
        except Exception as e:
            log(f"Apply failed: {e}")
            continue

        SYSTEM_PROMPT.write_text(new_prompt)
        log("Prompt updated. Evaluating...")

        try:
            score, results = run_eval()
        except Exception as e:
            log(f"Eval failed: {e}. Reverting.")
            SYSTEM_PROMPT.write_text(best_prompt)
            continue

        delta = score - best_score
        outcome = "KEEP" if delta >= IMPROVE_THRESHOLD else "REVERT"
        log(f"\nScore: {score:.2f}/5.0  Δ{delta:+.2f}  → {outcome}")

        history.append({"iter": i, "name": name, "score_before": best_score,
                        "score_after": score, "outcome": outcome})
        write_tsv({"iter": i, "name": name, "score": score, "delta": f"{delta:+.2f}",
                   "outcome": outcome, "ts": datetime.now().isoformat()})

        if outcome == "KEEP":
            best_score = score
            best_prompt = new_prompt
            baseline_results = results
            log(f"✓ New best: {best_score:.2f}/5.0")
        else:
            SYSTEM_PROMPT.write_text(best_prompt)
            log("↩ Reverted.")

        if best_score >= 5.0:
            log(f"\n{'='*60}")
            log(f"PERFECT SCORE at iter {i}. Done.")
            log(f"{'='*60}")
            break

        time.sleep(3)

    log(f"\nFinal: {best_score:.2f}/5.0 after {i} iters. Results: {RESULTS_TSV}")


if __name__ == "__main__":
    main()
