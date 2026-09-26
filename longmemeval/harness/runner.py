#!/usr/bin/env python3
"""LongMemEval benchmark runner for Mike.

Tests Mike's long-term memory system against the LongMemEval dataset.

Dataset format (xiaowu0162/longmemeval-cleaned):
  - haystack_sessions: list of sessions, each a list of {role, content} turns
  - haystack_session_ids: IDs corresponding to each session
  - haystack_dates: date strings for each session
  - answer_session_ids: which sessions contain the answer facts
  - question: the evaluation query
  - answer: ground truth
  - question_type: single-session-user | multi-session | temporal-reasoning | etc.

Strategy per test case:
  1. Inject all haystack sessions into sessions.db with past timestamps
  2. Run extraction synchronously to populate the knowledge graph
  3. Ask the evaluation question through relay.respond()
  4. Score (exact match + LLM judge)
  5. Log everything to JSONL

Usage:
    cd ~/agent
    source venv/bin/activate
    source <(vault)
    python tests/longmemeval/runner.py [--limit 25] [--split s] [--tasks all]

Outputs (tests/longmemeval/results/):
    run_YYYYMMDD_HHMMSS.jsonl     streaming results
    summary_YYYYMMDD_HHMMSS.json  final summary
    run_YYYYMMDD_HHMMSS.log       full debug log
    tools_YYYYMMDD_HHMMSS.jsonl   every tool call: test_id, full input, full output, duration
    requests_YYYYMMDD_HHMMSS.jsonl  every reader request: model, messages as sent, tool names offered
    sessions_YYYYMMDD_HHMMSS/     copy of the relay session log from the run's temp root

--search-archive serves search_memory from the FTS session archive under the case's
user id. It is the intended setting for --no-extract runs: with extraction skipped the
fact store search_memory normally reads is empty, so every call returns "No memories".
MCP servers are disabled by default (--mcp to enable); the configured filesystem server
is rooted at the real code and memory trees, not the test memory root.
"""

import argparse
import json
import logging
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

MIKE_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MIKE_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("lme")

_CURRENT_TEST_ID: str | None = None

# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

DATA_DIR = Path("/tmp/longmemeval_data")
DATA_FILES = {
    "s": "longmemeval_s_cleaned.json",
    "oracle": "longmemeval_oracle.json",
}

def download_split(split: str) -> Path:
    """Download the dataset file if not already cached."""
    filename = DATA_FILES.get(split)
    if not filename:
        raise ValueError(f"Unknown split '{split}'. Options: {list(DATA_FILES)}")

    dest = DATA_DIR / filename
    if dest.exists():
        logger.info(f"Using cached dataset: {dest}")
        return dest

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading {filename} from HuggingFace Hub...")
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id="xiaowu0162/longmemeval-cleaned",
        filename=filename,
        repo_type="dataset",
        local_dir=str(DATA_DIR),
    )
    logger.info(f"Downloaded to {path}")
    return Path(path)


def load_examples(split: str, task_filter: set[str] | None, limit: int) -> list[dict]:
    """Load and filter examples from the dataset."""
    data_path = download_split(split)
    with open(data_path) as f:
        data = json.load(f)

    if task_filter:
        before = len(data)
        data = [d for d in data if d.get("question_type") in task_filter]
        logger.info(f"Task filter {task_filter}: {before} → {len(data)}")

    data = data[:limit]
    logger.info(f"Loaded {len(data)} examples (split={split})")
    return data


# ---------------------------------------------------------------------------
# Memory isolation
# ---------------------------------------------------------------------------

def patch_memory_paths(test_memory_root: Path) -> None:
    """Redirect all Mike memory I/O to test_memory_root (patch before any relay use)."""
    import memory.storage as storage
    import relay.session_log as session_log
    import relay.sessions as sessions_mod

    storage.MEMORY_ROOT = test_memory_root
    session_log.SESSIONS_DIR = test_memory_root / "sessions"
    session_log.INDEX_FILE = test_memory_root / "sessions" / "index.json"
    sessions_mod.DEFAULT_DB_PATH = test_memory_root / "sessions.db"

    (test_memory_root / "sessions").mkdir(parents=True, exist_ok=True)
    logger.info(f"Memory paths patched → {test_memory_root}")


# ---------------------------------------------------------------------------
# Tracing — tool I/O, reader requests, MCP isolation
# ---------------------------------------------------------------------------

def _append_jsonl(path: Path, record: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _archive_search(keyword: str, test_db: Path, user_id: str) -> str:
    from relay.sessions import SessionStore
    results = SessionStore(test_db).retrieve_relevant_sessions(keyword, user_id=user_id, top_k=3)
    if not results:
        return f"No memories found matching '{keyword}'."
    out = f"Found {len(results)} past session(s) matching '{keyword}':\n\n"
    for r in results:
        out += f"--- Session from {r['date']} (matched: {r['match_snippet']}) ---\n"
        out += r["text"] + "\n\n"
    return out.strip()


def patch_tool_logging(tools_log: Path, test_db: Path, search_archive: bool) -> None:
    """Wrap the execute_tool name relay.relay imported; every tool call goes through it."""
    import relay.relay as relay_mod
    orig = relay_mod.execute_tool

    def logged(tool_name, tool_input, *args, **kwargs):
        record = {
            "test_id": _CURRENT_TEST_ID,
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "input": tool_input,
        }
        t0 = time.monotonic()
        try:
            if search_archive and tool_name == "search_memory":
                record["routed"] = "archive"
                output = _archive_search(tool_input.get("keyword", ""), test_db, _CURRENT_TEST_ID)
            else:
                output = orig(tool_name, tool_input, *args, **kwargs)
        except Exception as e:
            record["error"] = repr(e)
            record["duration_s"] = round(time.monotonic() - t0, 3)
            _append_jsonl(tools_log, record)
            raise
        record["output"] = output
        record["duration_s"] = round(time.monotonic() - t0, 3)
        _append_jsonl(tools_log, record)
        return output

    relay_mod.execute_tool = logged


def patch_request_logging(requests_log: Path) -> None:
    # Class-level so it sees the final payload from every client: Switchboard rewrites
    # "model" after call(), and run_with_model.py swaps in its own OpenAI() instance.
    from openai.resources.chat.completions import Completions
    orig = Completions.create

    def logged(self, *args, **kwargs):
        if _CURRENT_TEST_ID is not None:
            _append_jsonl(requests_log, {
                "test_id": _CURRENT_TEST_ID,
                "ts": datetime.now(timezone.utc).isoformat(),
                "model": kwargs.get("model"),
                "n_messages": len(kwargs.get("messages") or []),
                "messages": kwargs.get("messages"),
                "tools": [t["function"]["name"] for t in kwargs.get("tools") or []],
            })
        return orig(self, *args, **kwargs)

    Completions.create = logged


def disable_mcp() -> None:
    # mcp_client starts its servers at import time, so CONFIG_PATH cannot be patched
    # first; a stub module satisfies `from . import mcp_client` in relay.tool_domains.
    import types
    sys.modules["relay.tool_domains.mcp_client"] = types.ModuleType("relay.tool_domains.mcp_client")
    logger.info("MCP disabled for eval (--no-mcp)")


# ---------------------------------------------------------------------------
# History injection
# ---------------------------------------------------------------------------

def _ensure_sessions_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            session_date TEXT NOT NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_user_date ON messages(user_id, session_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)"
    )


def _parse_haystack_date(date_str: str) -> datetime:
    """Parse dataset date format '2023/02/01 (Wed) 10:20' into a UTC datetime."""
    import re
    # Strip the weekday token: "2023/02/01 (Wed) 10:20" → "2023/02/01 10:20"
    clean = re.sub(r'\s*\([A-Za-z]+\)\s*', ' ', date_str).strip()
    return datetime.strptime(clean, "%Y/%m/%d %H:%M").replace(tzinfo=timezone.utc)


def inject_haystack(
    db_path: Path,
    user_id: str,
    sessions: list[list[dict]],
    session_dates: list[str],
) -> list[str]:
    """Write all haystack sessions into sessions.db using the real dataset timestamps.

    Uses actual haystack_dates so temporal questions ("X days ago") compute correctly
    when the question is asked relative to question_date.
    Returns a list of per-session conversation texts (for batched extraction).
    """
    if not sessions:
        return []

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    _ensure_sessions_table(conn)

    session_texts: list[str] = []

    for session, date_str in zip(sessions, session_dates):
        try:
            base_dt = _parse_haystack_date(date_str)
        except Exception:
            # Fallback: shouldn't happen, but be safe
            base_dt = datetime.now(timezone.utc) - timedelta(days=30)

        session_date = base_dt.strftime("%Y-%m-%d")
        n_turns = len(session)
        interval_s = 7200 / max(n_turns, 1)  # spread turns over 2 hours

        turn_lines: list[str] = []
        for turn_idx, turn in enumerate(session):
            role = str(turn.get("role", "user"))
            content = str(turn.get("content", "")).strip()
            if not content:
                continue

            # Prepend a date marker to the FIRST user turn of each session.
            # relay.py strips timestamps from context, so Mike can't see WHEN things
            # happened unless we embed the date in the message content itself.
            # This is essential for temporal questions ("how many days ago did X happen?").
            if turn_idx == 0 and role == "user":
                content = f"[{date_str}] {content}"

            ts = (base_dt + timedelta(seconds=turn_idx * interval_s)).isoformat()
            conn.execute(
                "INSERT INTO messages (user_id, role, content, timestamp, session_date) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, role, content, ts, session_date),
            )
            turn_lines.append(f"{role.upper()}: {content}")

        if turn_lines:
            header = f"--- Session ({date_str}) ---"
            session_texts.append(header + "\n\n" + "\n\n".join(turn_lines))

    conn.commit()
    conn.close()
    return session_texts


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Lowercase, strip markdown, remove punctuation for comparison."""
    import re
    text = re.sub(r'\*+', '', text)   # remove ** bold markers
    text = re.sub(r'_+', '', text)     # remove _ italics
    text = re.sub(r'[^\w\s]', ' ', text)  # punctuation → space
    return re.sub(r'\s+', ' ', text).lower().strip()


def _score_against(pred_clean: str, exp_clean: str) -> float:
    """Score a single cleaned predicted string against a single cleaned expected string."""
    if not exp_clean:
        return 0.0
    if exp_clean in pred_clean:
        return 1.0
    exp_words = set(exp_clean.split())
    pred_words = set(pred_clean.split())
    if not exp_words:
        return 0.0
    overlap = exp_words & pred_words
    ratio = len(overlap) / len(exp_words)
    if ratio >= 0.8:
        return 0.8
    if ratio >= 0.5:
        return 0.5
    return 0.0


def score_exact(predicted: str, expected: str) -> float:
    """Exact/substring/word-overlap scoring (0.0–1.0).

    Handles markdown and punctuation. For compound expected strings like
    "7 days. 8 days (including the last day) is also acceptable." it scores
    against each sentence and takes the best, so either valid answer passes.
    """
    pred = _clean(predicted)

    # Split expected on sentences — handles "X days. Y days (also acceptable)."
    import re
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', expected) if s.strip()]
    if not sentences:
        return 0.0

    # Score against each candidate sentence, take the best
    best = 0.0
    for sent in sentences:
        best = max(best, _score_against(pred, _clean(sent)))
        if best == 1.0:
            break

    # Also score against the full expected string (catches multi-sentence exact matches)
    best = max(best, _score_against(pred, _clean(expected)))
    return best


def score_llm_judge(
    predicted: str,
    expected: str,
    question: str,
    client,
) -> dict:
    """LLM-as-judge via OpenRouter. Returns {score_normalized, raw_score, reasoning}."""
    prompt = (
        "You are a strict but fair evaluator. Score this AI answer.\n\n"
        f"Question: {question}\n"
        f"Expected answer: {expected}\n"
        f"AI answer: {predicted}\n\n"
        "Score 0-3:\n"
        "  3 = Correct and complete\n"
        "  2 = Mostly correct, minor gaps\n"
        "  1 = Partially correct, key info present but incomplete\n"
        "  0 = Incorrect or off-topic\n\n"
        'Return JSON only: {"score": <0-3>, "reasoning": "<one sentence>"}'
    )
    try:
        resp = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.choices[0].message.content or ""
        # Strip markdown fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        data = json.loads(text.strip())
        raw = int(data.get("score", 0))
        return {
            "score_normalized": round(raw / 3.0, 4),
            "raw_score": raw,
            "reasoning": data.get("reasoning", ""),
        }
    except Exception as e:
        logger.warning(f"LLM judge failed: {e}")
        return {"score_normalized": None, "raw_score": None, "reasoning": f"error: {e}"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    global _CURRENT_TEST_ID
    parser = argparse.ArgumentParser(description="LongMemEval runner for Mike")
    parser.add_argument("--limit", type=int, default=25, help="Max test cases")
    parser.add_argument(
        "--split", default="s",
        choices=list(DATA_FILES),
        help="Dataset split: s (small, ~550 turns) | oracle (long)"
    )
    parser.add_argument(
        "--tasks", default="all",
        help=(
            "Comma-separated question types or 'all'. "
            "Options: single-session-user, single-session-assistant, "
            "single-session-preference, multi-session, "
            "temporal-reasoning, knowledge-update"
        ),
    )
    parser.add_argument("--no-extract", action="store_true", help="Skip extraction step")
    parser.add_argument("--no-llm-judge", action="store_true", help="Skip LLM judge")
    parser.add_argument("--out", default=None, help="Override output JSONL path")
    parser.add_argument(
        "--search-archive", action="store_true",
        help="Serve search_memory from the FTS session archive under the case's user id "
             "(intended for --no-extract runs, where the fact store is empty)",
    )
    parser.add_argument(
        "--mcp", action=argparse.BooleanOptionalAction, default=False,
        help="Start MCP servers from config/mcp_servers.yaml (default --no-mcp)",
    )
    parser.add_argument("--keep-tmp", action="store_true", help="Keep the run's temp root")
    args = parser.parse_args()

    # Output paths
    results_dir = MIKE_ROOT / "tests" / "longmemeval" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.out) if args.out else results_dir / f"run_{run_ts}.jsonl"
    log_path = results_dir / f"run_{run_ts}.log"
    summary_path = results_dir / f"summary_{run_ts}.json"
    tools_log = results_dir / f"tools_{run_ts}.jsonl"
    requests_log = results_dir / f"requests_{run_ts}.jsonl"
    sessions_out = results_dir / f"sessions_{run_ts}"

    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.getLogger().addHandler(fh)

    logger.info(f"=== LongMemEval {run_ts} | split={args.split} limit={args.limit} ===")

    # Set up isolated memory root BEFORE importing Mike relay modules
    run_tmp = Path(f"/tmp/longmemeval_{run_ts}")
    test_memory_root = run_tmp / "mike-memory"
    test_memory_root.mkdir(parents=True, exist_ok=True)

    import memory.storage as storage
    import relay.session_log as session_log
    import relay.sessions as sessions_mod

    patch_memory_paths(test_memory_root)
    storage.init_memory()

    # Load dataset
    task_filter = None if args.tasks == "all" else set(t.strip() for t in args.tasks.split(","))
    examples = load_examples(args.split, task_filter, args.limit)

    # OpenRouter client for LLM judge (only required if --no-llm-judge not set)
    from openai import OpenAI
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key and not args.no_llm_judge:
        logger.error("OPENROUTER_API_KEY not set — LLM judge will fail")
        print("ERROR: OPENROUTER_API_KEY not set. Use --no-llm-judge or source vault.")
        sys.exit(1)
    or_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key or "none")

    # Create relay (uses patched memory root)
    if not args.mcp:
        disable_mcp()
    logger.info("Initializing RelayV3...")
    from relay.relay import RelayV3
    relay_instance = RelayV3()

    test_db = test_memory_root / "sessions.db"
    patch_tool_logging(tools_log, test_db, args.search_archive)
    patch_request_logging(requests_log)

    results: list[dict] = []
    ok_count = 0
    total_exact = 0.0
    total_llm = 0.0
    llm_count = 0

    print(f"\nRunning {len(examples)} test cases — output: {out_path}\n")

    for idx, example in enumerate(examples):
        test_id = f"lme_{idx:04d}"
        question = str(example.get("question", "")).strip()
        expected = str(example.get("answer", "")).strip()
        question_type = str(example.get("question_type", "unknown"))
        question_date = str(example.get("question_date", "")).strip()
        haystack_sessions: list[list[dict]] = example.get("haystack_sessions", [])
        haystack_dates: list[str] = example.get("haystack_dates", [""] * len(haystack_sessions))
        answer_session_ids: list[str] = example.get("answer_session_ids", [])
        total_turns = sum(len(s) for s in haystack_sessions)

        logger.info(
            f"[{test_id}] {question_type} | {len(haystack_sessions)} sessions "
            f"({total_turns} turns) | Q: {question[:70]}..."
        )

        result: dict = {
            "test_id": test_id,
            "run_ts": run_ts,
            "question_type": question_type,
            "question": question,
            "question_date": question_date,
            "expected": expected,
            "total_turns": total_turns,
            "num_sessions": len(haystack_sessions),
            "answer_session_ids": answer_session_ids,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

        user_id = f"lme_{idx:04d}"

        try:
            # Step 1: Always inject haystack history into sessions.db
            if haystack_sessions:
                session_texts = inject_haystack(
                    test_db, user_id, haystack_sessions, haystack_dates
                )
                total_chars = sum(len(t) for t in session_texts)
                logger.info(
                    f"[{test_id}] Injected {total_turns} turns across "
                    f"{len(haystack_sessions)} sessions ({total_chars:,} chars)"
                )
            else:
                session_texts = []
                total_chars = 0

            # Step 1b: Backfill FTS index so retrieve_sessions tool works during eval
            if haystack_sessions:
                from relay.sessions import SessionStore
                store = SessionStore(test_db)
                n_indexed = store.fts_backfill(user_id)
                logger.info(f"[{test_id}] FTS backfill: {n_indexed} messages indexed")

            # Step 2: Batched extraction (optional — skip with --no-extract)
            # Extraction turns session text into searchable memory facts.
            # Without it, Mike answers from raw session context window (~500 msgs).
            if session_texts and not args.no_extract:
                from memory.extraction import run as extract_run
                BATCH_SIZE = 1  # per-session: matches real-world Mike, avoids truncation
                batches = [
                    session_texts[i: i + BATCH_SIZE]
                    for i in range(0, len(session_texts), BATCH_SIZE)
                ]
                logger.info(
                    f"[{test_id}] Running extraction: {len(batches)} batches "
                    f"of up to {BATCH_SIZE} sessions..."
                )
                t_ext = time.monotonic()
                total_facts = 0
                total_entities = 0
                for b_idx, batch in enumerate(batches):
                    batch_text = "\n\n".join(batch)[:60000]  # 60K chars ~= 15K tokens, well within 131K ctx
                    b_result = extract_run(batch_text)
                    total_facts += b_result.get("facts_saved", 0)
                    total_entities += b_result.get("entities_created", 0)
                    logger.debug(
                        f"[{test_id}] Batch {b_idx + 1}/{len(batches)}: "
                        f"{b_result.get('facts_saved', 0)} facts"
                    )
                ext_latency = round(time.monotonic() - t_ext, 2)
                result["extraction"] = {
                    "facts_saved": total_facts,
                    "entities_created": total_entities,
                    "batches": len(batches),
                    "latency_s": ext_latency,
                    "chars_total": total_chars,
                }
                logger.info(
                    f"[{test_id}] Extraction: {total_facts} facts, "
                    f"{total_entities} entities, {len(batches)} batches, {ext_latency}s"
                )
            else:
                result["extraction"] = {"skipped": True}

            # Step 3: Ask the eval question through relay.
            # Prepend question_date so Mike can anchor relative time calculations
            # ("X days ago", "how many weeks since") against the correct reference point.
            if question_date:
                full_question = f"[Today's date: {question_date}]\n\n{question}"
            else:
                full_question = question
            logger.info(f"[{test_id}] Asking (date={question_date}): {question}")
            t_q = time.monotonic()
            _CURRENT_TEST_ID = test_id
            answer = relay_instance.respond(
                full_question, user_id=user_id, interface="longmemeval"
            )
            _CURRENT_TEST_ID = None
            q_latency = round(time.monotonic() - t_q, 2)

            result["predicted"] = answer
            result["latency_s"] = q_latency
            result["status"] = "ok"

            # Step 4: Score
            exact = score_exact(answer, expected)
            result["score_exact"] = exact
            total_exact += exact
            ok_count += 1

            if not args.no_llm_judge:
                judge = score_llm_judge(answer, expected, question, or_client)
                result["score_llm"] = judge
                if judge.get("score_normalized") is not None:
                    total_llm += judge["score_normalized"]
                    llm_count += 1

            logger.info(
                f"[{test_id}] RESULT exact={exact:.2f} "
                f"llm={result.get('score_llm', {}).get('score_normalized', 'n/a')} "
                f"latency={q_latency}s"
            )
            logger.info(f"[{test_id}] Predicted: {answer[:120].replace(chr(10), ' ')}")
            logger.info(f"[{test_id}] Expected:  {expected}")

        except Exception as e:
            logger.exception(f"[{test_id}] FAILED: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        results.append(result)

        # Streaming write
        with open(out_path, "a") as f:
            f.write(json.dumps(result) + "\n")

        # Live progress line
        avg_e = total_exact / max(ok_count, 1)
        avg_l = total_llm / max(llm_count, 1) if llm_count else 0.0
        err_n = sum(1 for r in results if r["status"] == "error")
        score_str = f"{result.get('score_exact', 'ERR')}"
        print(
            f"[{idx + 1:>3}/{len(examples)}] {test_id} {question_type:<32} "
            f"exact={score_str:<6} avg_e={avg_e:.3f} avg_llm={avg_l:.3f} errs={err_n}"
        )

    # ---------------------------------------------------------------------------
    # Final summary
    # ---------------------------------------------------------------------------
    ok_r = [r for r in results if r["status"] == "ok"]
    err_r = [r for r in results if r["status"] == "error"]

    scores_e = [r["score_exact"] for r in ok_r]
    avg_e_final = sum(scores_e) / len(scores_e) if scores_e else 0.0

    scores_l = [
        r["score_llm"]["score_normalized"]
        for r in ok_r
        if r.get("score_llm", {}).get("score_normalized") is not None
    ]
    avg_l_final = sum(scores_l) / len(scores_l) if scores_l else None

    by_task: dict = {}
    for r in ok_r:
        qt = r["question_type"]
        if qt not in by_task:
            by_task[qt] = {"count": 0, "exact_sum": 0.0, "llm_sum": 0.0, "llm_n": 0}
        by_task[qt]["count"] += 1
        by_task[qt]["exact_sum"] += r.get("score_exact", 0.0)
        if r.get("score_llm", {}).get("score_normalized") is not None:
            by_task[qt]["llm_sum"] += r["score_llm"]["score_normalized"]
            by_task[qt]["llm_n"] += 1

    by_task_out = {}
    for qt, v in by_task.items():
        by_task_out[qt] = {
            "count": v["count"],
            "avg_score_exact": round(v["exact_sum"] / v["count"], 4),
        }
        if v["llm_n"]:
            by_task_out[qt]["avg_score_llm"] = round(v["llm_sum"] / v["llm_n"], 4)

    summary = {
        "run_ts": run_ts,
        "split": args.split,
        "tasks": args.tasks,
        "total": len(results),
        "ok": len(ok_r),
        "errors": len(err_r),
        "avg_score_exact": round(avg_e_final, 4),
        "avg_score_llm": round(avg_l_final, 4) if avg_l_final is not None else None,
        "by_question_type": by_task_out,
        "results_file": str(out_path),
        "log_file": str(log_path),
    }

    summary_path.write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 60)
    print(f"LONGMEMEVAL RESULTS  {run_ts}")
    print("=" * 60)
    print(json.dumps(summary, indent=2))
    print(f"\nResults:  {out_path}")
    print(f"Log:      {log_path}")
    print(f"Summary:  {summary_path}")
    print(f"Tools:    {tools_log}")
    print(f"Requests: {requests_log}")

    # Cleanup
    sessions_src = test_memory_root / "sessions"
    if sessions_src.exists():
        shutil.copytree(sessions_src, sessions_out)
        print(f"Sessions: {sessions_out}")
    if args.keep_tmp:
        print(f"Temp root kept: {run_tmp}")
    else:
        try:
            shutil.rmtree(run_tmp)
        except Exception:
            pass


if __name__ == "__main__":
    main()
