"""Replay the readers' own search_memory keywords through the FTS archive the harness built.

Standalone: needs only the public dataset and the harness's inject_haystack (runner.py).
Reproduces the exact table and query used by the agent's retrieve_sessions tool:
  FTS5 over user-role messages, tokenize='porter ascii', ORDER BY rank, dedupe by session_date, top 2.

Usage: python3 replay.py /path/to/longmemeval_s_cleaned.json
Writes retrieval_replay.csv next to this file.
"""
import csv, json, sqlite3, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent.parent / "harness"))
import runner  # public: inject_haystack, _parse_haystack_date


def build_fts(conn, user_id):
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5("
                 "user_id UNINDEXED, session_date UNINDEXED, role UNINDEXED, content, tokenize='porter ascii')")
    rows = conn.execute("SELECT user_id, session_date, role, content FROM messages WHERE user_id=? AND role='user'", (user_id,)).fetchall()
    conn.executemany("INSERT INTO messages_fts(user_id, session_date, role, content) VALUES (?,?,?,?)", rows)
    conn.commit()
    return len(rows)

def top_dates(conn, user_id, keyword, top_k=2):
    rows = conn.execute("SELECT session_date FROM messages_fts WHERE user_id=? AND messages_fts MATCH ? ORDER BY rank LIMIT ?",
                        (user_id, keyword, top_k * 3)).fetchall()
    seen = []
    for (d,) in rows:
        if d not in seen:
            seen.append(d)
    return len(rows), seen[:top_k]

def main():
    data = json.load(open(sys.argv[1]))

    data = [d for d in data if d.get("question_type") == "single-session-user"][:25]

    queries = {}
    for row in csv.DictReader(open(HERE / "search_queries.csv")):
        queries.setdefault(row["test_id"], {})[row["reader"]] = row["search_memory_keywords"].split("|")

    hj = {r["test_id"]: r for r in csv.DictReader(open(HERE.parent / "hand_judgments.csv"))}


    out = csv.writer(open(HERE / "retrieval_replay.csv", "w"))
    out.writerow(["test_id", "reader", "hand_judged", "answer_session_start_from_end", "keyword",
                  "fts_rows_matched", "answer_session_in_top2", "rows_matched_as_user_dino"])
    per_case = {}
    for idx, ex in enumerate(data):
        test_id = f"lme_{idx:04d}"
        assert ex["question_id"] == hj[test_id]["question_id"], test_id
        if test_id not in queries:
            continue
        db = HERE / f"_{test_id}.db"
        if db.exists():
            db.unlink()
        runner.inject_haystack(db, test_id, ex["haystack_sessions"], ex["haystack_dates"])
        conn = sqlite3.connect(db)
        build_fts(conn, test_id)
        ans_ids = set(ex["answer_session_ids"])
        ans_dates = {runner._parse_haystack_date(d).strftime("%Y-%m-%d")
                     for sid, d in zip(ex["haystack_session_ids"], ex["haystack_dates"]) if sid in ans_ids}
        for reader, kws in queries[test_id].items():
            for kw in kws:
                n, top = top_dates(conn, test_id, kw)
                n_dino, _ = top_dates(conn, "dino", kw)   # what retrieve_sessions would actually have queried
                hit = bool(ans_dates & set(top))
                out.writerow([test_id, reader, hj[test_id][reader + "_hand"], hj[test_id]["answer_session_start_from_end"],
                              kw, n, int(hit), n_dino])
                per_case.setdefault((reader, test_id), []).append(hit)
        conn.close()
        db.unlink()

    for reader in ("sonnet", "opus"):
        cases = [k for k in per_case if k[0] == reader]
        found = sum(any(per_case[k]) for k in cases)
        print(f"{reader}: searched on {len(cases)} cases, answer session in FTS top-2 for {found}")

if __name__ == "__main__":
    main()
