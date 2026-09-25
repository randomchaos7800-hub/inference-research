"""T2 oracle arm (Guo, Failure Attribution Test Matrix): for every case, query the rebuilt FTS index
with wording taken from the expected answer, under the case's user id. Normal arm = replay.py.
Oracle query = expected answer as a quoted phrase; if that matches nothing, the answer's words AND-ed.
Usage: python3 oracle.py /path/to/longmemeval_s_cleaned.json  -> oracle_replay.csv
"""
import csv, json, re, sqlite3, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent.parent / "harness"))
import runner
from replay import build_fts, top_dates

data = json.load(open(sys.argv[1]))
data = [d for d in data if d.get("question_type") == "single-session-user"][:25]
hj = {r["test_id"]: r for r in csv.DictReader(open(HERE.parent / "hand_judgments.csv"))}
out = csv.writer(open(HERE / "oracle_replay.csv", "w"))
out.writerow(["test_id", "expected", "answer_session_start_from_end", "any_reader_correct",
              "source_turn_indexed", "oracle_query", "oracle_rows_matched", "oracle_answer_session_in_top2"])
found = indexed = 0
for idx, ex in enumerate(data):
    test_id = f"lme_{idx:04d}"
    db = HERE / f"_{test_id}.db"
    if db.exists(): db.unlink()
    runner.inject_haystack(db, test_id, ex["haystack_sessions"], ex["haystack_dates"])
    conn = sqlite3.connect(db); build_fts(conn, test_id)
    ans_ids = set(ex["answer_session_ids"])
    ans_dates = {runner._parse_haystack_date(d).strftime("%Y-%m-%d")
                 for sid, d in zip(ex["haystack_session_ids"], ex["haystack_dates"]) if sid in ans_ids}
    # T1: is the answer-bearing session's user text in the index at all?
    n_idx = conn.execute("SELECT count(*) FROM messages_fts WHERE user_id=? AND session_date IN (%s)" % ",".join("?"*len(ans_dates)),
                         (test_id, *ans_dates)).fetchone()[0]
    indexed += n_idx > 0
    expected = ex["answer"]
    phrase = '"' + re.sub(r'[^A-Za-z0-9 ]+', ' ', expected).strip() + '"'
    n, top = top_dates(conn, test_id, phrase)
    q = phrase
    if n == 0:
        words = [w for w in re.findall(r"[A-Za-z0-9]+", expected) if len(w) > 2]
        q = " AND ".join(words) if words else phrase
        n, top = top_dates(conn, test_id, q)
    hit = bool(ans_dates & set(top)); found += hit
    anyc = int(any(hj[test_id][r + "_hand"] == "1" for r in ("terra", "sonnet", "opus")))
    out.writerow([test_id, expected, hj[test_id]["answer_session_start_from_end"], anyc, int(n_idx > 0), q, n, int(hit)])
    conn.close(); db.unlink()
print(f"T1 source turn indexed: {indexed}/25   T2 oracle finds answer session top-2: {found}/25")
