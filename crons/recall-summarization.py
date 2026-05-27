#!/usr/bin/env python3
"""Recall summarization — review today's ops logs, surface patterns, post to #ops-log. Runs 2:30AM."""

import os
import subprocess
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import slack
import inference

LOG_DIR = os.path.expanduser("~/.logs")
DAILY_LOG_DIR = os.path.expanduser("~/.claude/daily-logs")


def tail_log(path, lines=30):
    if not os.path.exists(path):
        return ""
    try:
        r = subprocess.run(["tail", "-n", str(lines), path], capture_output=True, text=True)
        return r.stdout.strip()
    except Exception:
        return ""


def main():
    today = date.today().isoformat()
    since = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

    # Collect relevant logs
    sections = {}

    # Agent smoke log (shows what's passing/failing)
    smoke = tail_log(os.path.join(LOG_DIR, "agent-smoke.log"), 40)
    if smoke:
        sections["agent-smoke"] = smoke

    # Inference status
    inf_status = tail_log(os.path.join(LOG_DIR, "inference-status.log"), 20)
    if inf_status:
        sections["inference-status"] = inf_status

    # Today's claude daily log if it exists
    claude_log = os.path.join(DAILY_LOG_DIR, f"{today}.md")
    if os.path.exists(claude_log):
        sections["session-log"] = open(claude_log).read()[:2000]

    # Any recent journal errors
    j_errors = subprocess.run(
        f'journalctl --since "{since}" -p err --no-pager --output=short 2>/dev/null | tail -20',
        shell=True, capture_output=True, text=True
    ).stdout.strip()
    if j_errors:
        sections["journal-errors"] = j_errors

    if not sections:
        print("Nothing to summarize — skipping")
        return

    combined = "\n\n".join(f"=== {k} ===\n{v}" for k, v in sections.items())

    system = "You write brief, direct ops summaries. Flag real issues, skip noise."
    prompt = (
        f"Today is {today}. Here are the last 24h of operational logs:\n\n{combined}\n\n"
        "Write a brief summary (3-5 bullets) covering:\n"
        "1. What worked or failed in agent/inference tasks\n"
        "2. Any infrastructure issues worth noting\n"
        "3. Anything Dino should know\n"
        "If everything is clean, say so in one line. No fluff."
    )

    result = inference.ask(prompt, system=system, max_tokens=500, timeout=90)
    msg = f"*🔄 Recall Summary — {today}*\n\n{result}"
    slack.post(msg)
    print(f"Recall summary posted — {today}")


if __name__ == "__main__":
    main()
