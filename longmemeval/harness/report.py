#!/usr/bin/env python3
"""View LongMemEval results from a JSONL results file.

Usage:
    python tests/longmemeval/report.py [results/run_YYYYMMDD_HHMMSS.jsonl]
    python tests/longmemeval/report.py --latest
    python tests/longmemeval/report.py --all
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def load_results(path: Path) -> list[dict]:
    results = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return results


def fmt_score(s) -> str:
    if s is None:
        return "  N/A"
    return f"{s:.3f}"


def print_report(results: list[dict], title: str = "") -> None:
    ok = [r for r in results if r.get("status") == "ok"]
    err = [r for r in results if r.get("status") == "error"]

    if title:
        print(f"\n{'=' * 64}")
        print(f"  {title}")
        print(f"{'=' * 64}")

    print(f"\n{'─' * 64}")
    print(f"  SUMMARY: {len(ok)} ok / {len(err)} errors / {len(results)} total")
    print(f"{'─' * 64}")

    if not ok:
        print("  No completed results yet.")
        return

    scores_e = [r["score_exact"] for r in ok]
    avg_e = sum(scores_e) / len(scores_e)
    print(f"  Avg exact-match score:  {avg_e:.4f}  ({avg_e * 100:.1f}%)")

    scores_l = [
        r["score_llm"]["score_normalized"]
        for r in ok
        if r.get("score_llm", {}).get("score_normalized") is not None
    ]
    if scores_l:
        avg_l = sum(scores_l) / len(scores_l)
        print(f"  Avg LLM-judge score:    {avg_l:.4f}  ({avg_l * 100:.1f}%)")

    latencies = [r["latency_s"] for r in ok if "latency_s" in r]
    if latencies:
        print(f"  Avg query latency:      {sum(latencies) / len(latencies):.1f}s")

    # By question type
    by_type: dict = defaultdict(lambda: {"n": 0, "exact": 0.0})
    for r in ok:
        qt = r.get("question_type", "unknown")
        by_type[qt]["n"] += 1
        by_type[qt]["exact"] += r["score_exact"]

    print(f"\n  {'Question Type':<35} {'N':>4}  {'Exact Score':>11}")
    print(f"  {'─' * 55}")
    for qt, v in sorted(by_type.items()):
        avg = v["exact"] / v["n"]
        bar = "█" * int(avg * 20)
        print(f"  {qt:<35} {v['n']:>4}  {avg:.4f} ({avg*100:>5.1f}%) {bar}")

    # Per-result table
    print(f"\n  {'ID':<10} {'Type':<30} {'Exact':>6}  {'Question (truncated)':<40}")
    print(f"  {'─' * 90}")
    for r in results:
        if r.get("status") == "error":
            print(f"  {r['test_id']:<10} {'ERROR':<30} {'ERR':>6}  {r.get('error', '')[:40]}")
            continue
        score = r.get("score_exact")
        score_str = f"{score:.3f}" if score is not None else "N/A"
        mark = "✓" if score and score >= 0.8 else ("~" if score and score >= 0.5 else "✗")
        q = r.get("question", "")[:40]
        print(f"  {r['test_id']:<10} {r.get('question_type','?'):<30} {mark}{score_str:>5}  {q}")

    # Failure analysis
    failures = [r for r in ok if r.get("score_exact", 1) < 0.5]
    if failures:
        print(f"\n  {'─' * 64}")
        print(f"  FAILURES ({len(failures)} cases with score < 0.5):")
        print(f"  {'─' * 64}")
        for r in failures:
            print(f"\n  [{r['test_id']}] {r.get('question_type')}")
            print(f"  Q: {r.get('question', '')[:80]}")
            print(f"  Expected:  {r.get('expected', '')[:80]}")
            pred = r.get("predicted", "")
            print(f"  Got:       {pred[:80].replace(chr(10), ' ')}")
            if r.get("score_llm"):
                print(f"  LLM judge: {r['score_llm'].get('reasoning', '')[:80]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="View LongMemEval results")
    parser.add_argument("file", nargs="?", help="JSONL results file path")
    parser.add_argument("--latest", action="store_true", help="Load most recent run")
    parser.add_argument("--all", action="store_true", help="Show all runs")
    args = parser.parse_args()

    if args.all:
        files = sorted(RESULTS_DIR.glob("run_*.jsonl"))
        if not files:
            print("No result files found in", RESULTS_DIR)
            sys.exit(1)
        for f in files:
            results = load_results(f)
            print_report(results, title=f.name)
        return

    if args.latest or not args.file:
        files = sorted(RESULTS_DIR.glob("run_*.jsonl"))
        if not files:
            print("No result files found in", RESULTS_DIR)
            sys.exit(1)
        path = files[-1]
        print(f"Loading: {path}")
    else:
        path = Path(args.file)
        if not path.exists():
            # Try relative to results dir
            path = RESULTS_DIR / args.file
        if not path.exists():
            print(f"File not found: {args.file}")
            sys.exit(1)

    results = load_results(path)
    if not results:
        print("No results in file (may still be running)")
        sys.exit(0)

    run_ts = results[0].get("run_ts", path.stem)
    print_report(results, title=f"LongMemEval Run — {run_ts}")


if __name__ == "__main__":
    main()
