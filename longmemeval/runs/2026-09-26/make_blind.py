"""Generate a blind judging pack for one run. Prefix keeps item ids disjoint from earlier packs.
Usage: python3 make_blind.py <run_label> <prefix> <out_dir>"""
import csv, json, os, random, sys
from pathlib import Path
run, prefix, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
RES = Path(os.environ.get("LME_RESULTS", "~/agent/tests/longmemeval/results")).expanduser()
ts = dict(l.split("=") for l in [sys.argv[4]])[run]
items = [json.loads(l) for l in open(RES / f"run_{ts}.jsonl")]
rows = [dict(item=None, run=run, test_id=d["test_id"], question=d["question"], expected=d["expected"], predicted=d.get("predicted") or "") for d in items]
random.Random(20260926).shuffle(rows)
for i, r in enumerate(rows, 1): r["item"] = f"{prefix}{i:03d}"
csv.writer(open(out / "blind_key.csv", "w")).writerows([["item","run","test_id"]] + [[r["item"], r["run"], r["test_id"]] for r in rows])
w = csv.DictWriter(open(out / "blind_items.csv", "w"), fieldnames=["item","question","expected","predicted"]); w.writeheader()
w.writerows([{k: r[k] for k in ("item","question","expected","predicted")} for r in rows])
print(f"{len(rows)} items -> {out}/blind_items.csv (prefix {prefix})")
