#!/usr/bin/env python3
"""Weekly essay brief — rank article ideas from last 7 days of arXiv. Runs Sunday 6PM."""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import slack
import inference

ARXIV_DIR = os.path.expanduser("~/crons/data/arxiv")


def main():
    today = date.today()
    combined = []

    for days_ago in range(7):
        d = (today - timedelta(days=days_ago)).isoformat()
        path = os.path.join(ARXIV_DIR, f"arxiv-{d}.md")
        if os.path.exists(path):
            combined.append(open(path).read())

    if not combined:
        print("No arxiv files in last 7 days — skipping")
        slack.post(f"*📝 Weekly Essay Brief — {today.isoformat()}*\n\nNo arxiv files found this week.")
        return

    content = "\n\n---\n\n".join(combined)

    system = "You write for a solo operator: local AI, agents, sovereign compute. Garage builder, not corporate."
    prompt = (
        f"Week ending {today.isoformat()}. Here are the week's arXiv research summaries:\n\n{content}\n\n"
        "Generate 3-5 ranked article ideas for Substack, HN, or dev.to. "
        "For each: title, platform, why now, what angle, estimated word count. "
        "Rank by: 1) engagement/revenue potential, 2) Dino's unique credibility. "
        "Real opinions. What would actually drive readers? "
        "Only use the content provided — no external sources."
    )

    result = inference.ask(prompt, system=system, max_tokens=900, timeout=120)
    msg = f"*📝 Weekly Essay Brief — {today.isoformat()}*\n\n{result}"
    slack.post(msg)
    print(f"Essay brief posted — {today.isoformat()}")


if __name__ == "__main__":
    main()
