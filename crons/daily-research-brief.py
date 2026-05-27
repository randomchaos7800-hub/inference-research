#!/usr/bin/env python3
"""Daily research brief — synthesize last 3 days of arXiv files into opinionated bullets. Runs 8AM."""

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

    for days_ago in range(3):
        d = (today - timedelta(days=days_ago)).isoformat()
        path = os.path.join(ARXIV_DIR, f"arxiv-{d}.md")
        if os.path.exists(path):
            combined.append(open(path).read())

    if not combined:
        print("No arxiv files in last 3 days — skipping")
        return

    content = "\n\n---\n\n".join(combined)

    system = (
        "You write for a solo operator who builds local AI agents. "
        "Direct, specific, skeptical of hype. Write like Dino: garage builder, not corporate."
    )
    prompt = (
        f"Today is {today.isoformat()}. Here are the arXiv summaries from the past 3 days:\n\n{content}\n\n"
        "Write 5-7 opinionated bullets about what's actually happening in AI research right now. "
        "Real opinions — not summaries. What matters for solo operators building agents? What's noise? "
        "No buzzwords. If there's nothing new worth saying, respond with exactly [SILENT]."
    )

    result = inference.ask(prompt, system=system, max_tokens=800, timeout=120)

    if "[SILENT]" in result:
        print("Nothing new — skipping")
        return

    msg = f"*🔬 Research Brief — {today.isoformat()}*\n\n{result}"
    slack.post(msg)
    print(f"Research brief posted — {today.isoformat()}")


if __name__ == "__main__":
    main()
