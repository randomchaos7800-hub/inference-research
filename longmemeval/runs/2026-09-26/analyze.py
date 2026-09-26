"""Post-run analysis for the 2026-09-26 rerun. Usage: python3 analyze.py <label>=<run_ts> ... 
Writes per_case.csv (one row per case x run: exact, searched, archive hit, answer-session returned, in_window, n_requests, max_msgs)
and blind_items.csv / blind_key.csv for judging. No hand labels are read or written."""
import os, sys, json, csv, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))
import runner
RES = Path(os.environ.get("LME_RESULTS", "~/agent/tests/longmemeval/results")).expanduser()
OUT = Path(__file__).parent
runs = dict(a.split("=") for a in sys.argv[1:])
data = json.load(open("/tmp/longmemeval_data/longmemeval_s_cleaned.json"))
data = [d for d in data if d.get("question_type") == "single-session-user"][:25]
ans_dates = {}
for i, ex in enumerate(data):
    ids = set(ex["answer_session_ids"])
    ans_dates[f"lme_{i:04d}"] = {runner._parse_haystack_date(d).strftime("%Y-%m-%d") for s, d in zip(ex["haystack_session_ids"], ex["haystack_dates"]) if s in ids}
pos = {r["test_id"]: int(r["answer_session_start_from_end"]) for r in csv.DictReader(open(str(Path(__file__).resolve().parent.parent / "2026-09-21" / "answer_position.csv")))}
rows, items = [], []
for label, ts in runs.items():
    preds = {json.loads(l)["test_id"]: json.loads(l) for l in open(RES / f"run_{ts}.jsonl")}
    tools = [json.loads(l) for l in open(RES / f"tools_{ts}.jsonl")] if (RES / f"tools_{ts}.jsonl").exists() else []
    reqs = [json.loads(l) for l in open(RES / f"requests_{ts}.jsonl")]
    for t in sorted(preds):
        p = preds[t]
        s = [x for x in tools if x["test_id"] == t and x["tool"] == "search_memory"]
        hit = any(x["output"].startswith("Found") for x in s)
        returned_ans = any(d in x["output"] for x in s for d in ans_dates[t] if x["output"].startswith("Found") and f"Session from {d}" in x["output"])
        rq = [r for r in reqs if r["test_id"] == t]
        rows.append(dict(run=label, test_id=t, expected=p["expected"], score_exact=p.get("score_exact"), searched=int(bool(s)),
                         keywords="|".join(str(x["input"].get("keyword", "")) for x in s), archive_hit=int(hit), answer_session_returned=int(returned_ans),
                         answer_session_start_from_end=pos[t], in_window=int(pos[t] <= 100), n_requests=len(rq), max_msgs=max([r["n_messages"] for r in rq] or [0])))
        items.append(dict(run=label, test_id=t, question=p["question"], expected=p["expected"], predicted=p.get("predicted") or ""))
w = csv.DictWriter(open(OUT / "per_case.csv", "w"), fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
# blind-set generation moved to make_blind.py so re-running analysis never renumbers existing labels
for label in runs:
    rr = [r for r in rows if r["run"] == label]
    print(f"{label}: exact_mean={sum(float(r['score_exact'] or 0) for r in rr)/len(rr):.2f} searched={sum(r['searched'] for r in rr)} archive_hit={sum(r['archive_hit'] for r in rr)} answer_session_returned={sum(r['answer_session_returned'] for r in rr)} out_of_window_cases_with_answer_returned={sum(1 for r in rr if not r['in_window'] and r['answer_session_returned'])}/15")
