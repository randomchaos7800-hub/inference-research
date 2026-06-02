#!/usr/bin/env python3
"""Weekly essay brief — rank article ideas from last 7 days of arXiv. Runs Sunday 6PM."""

import os
import subprocess
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
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
    print(f"Essay brief — {today.isoformat()}\n\n{result}")

    html_lines = [f'<div class="prose"><p style="color:var(--muted);margin-bottom:10px">Week ending {today.isoformat()}</p>']
    for line in result.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line[0].isdigit() and line[1:3] in ('. ', ') '):
            html_lines.append(f'<p style="margin:8px 0"><strong>{line}</strong></p>')
        elif line.startswith(('- ', '• ')):
            html_lines.append(f'<p style="margin:3px 0 3px 16px">{line[2:].strip()}</p>')
        else:
            html_lines.append(f'<p>{line}</p>')
    html_lines.append('</div>')

    ops_write = os.path.join(os.path.dirname(__file__), "..", "scripts", "ops-write.py")
    subprocess.run([sys.executable, ops_write, "weekly"], input="\n".join(html_lines), text=True, check=False)
    print(f"Essay brief written — {today.isoformat()}")


if __name__ == "__main__":
    main()
