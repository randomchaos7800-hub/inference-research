#!/usr/bin/env python3
"""HN sweep — fetch top AI/agent stories from Algolia HN API, pick 5 via local inference, post to ops dashboard. Runs 9AM daily."""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import inference

OPS_WRITE = "/home/dino/scripts/ops-write.py"
SECTION = "hn"

QUERIES = [
    "https://hn.algolia.com/api/v1/search?query=AI+agents+LLM+local+inference&tags=story&hitsPerPage=30",
    "https://hn.algolia.com/api/v1/search?query=autonomous+agents+self+hosted+AI&tags=story&hitsPerPage=20",
]

MIN_POINTS = 30
MAX_TO_MODEL = 20


def fetch_hits(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data.get("hits", [])
    except Exception as e:
        print(f"ERROR fetching {url}: {e}", file=sys.stderr)
        return []


def main():
    today = date.today().isoformat()

    # Fetch and deduplicate
    all_hits = []
    seen_ids = set()
    for url in QUERIES:
        for hit in fetch_hits(url):
            oid = hit.get("objectID")
            if oid and oid not in seen_ids:
                seen_ids.add(oid)
                all_hits.append(hit)

    # Filter by points
    filtered = [h for h in all_hits if (h.get("points") or 0) >= MIN_POINTS]
    filtered.sort(key=lambda h: h.get("points", 0), reverse=True)

    if not filtered:
        html = (
            '<div class="prose">'
            '<p style="color:var(--muted);font-style:italic">Nothing surfaced today</p>'
            '</div>'
        )
        subprocess.run([sys.executable, OPS_WRITE, SECTION], input=html, text=True, check=False)
        print(f"HN sweep done — {today} — no stories passed filter")
        return

    # Build story list for model
    candidates = filtered[:MAX_TO_MODEL]
    story_list = "\n\n".join(
        f"[{i+1}] {h.get('title', '(no title)')}\n"
        f"Points: {h.get('points', 0)}\n"
        f"URL: {h.get('url') or 'https://news.ycombinator.com/item?id=' + h.get('objectID', '')}\n"
        f"HN: https://news.ycombinator.com/item?id={h.get('objectID', '')}"
        for i, h in enumerate(candidates)
    )

    system = (
        "You are a signal filter for a solo operator building local AI agents, memory systems, "
        "and sovereign compute. Be direct and opinionated. No hedging, no fluff."
    )
    prompt = (
        f"Today is {today}. Here are top HN stories:\n\n{story_list}\n\n"
        "Pick the 5 most relevant for a solo operator building local AI agents, memory systems, "
        "and sovereign compute. For each, reply with EXACTLY this format — one block per story, "
        "no extra text before or after:\n\n"
        "TITLE: <exact title>\n"
        "HN_URL: <HN link>\n"
        "STORY_URL: <original article URL, or same as HN_URL if no article>\n"
        "POINTS: <number>\n"
        "WHY: <one sentence why it matters>\n\n"
        "Output exactly 5 blocks separated by a blank line. If fewer than 5 stories are genuinely "
        "relevant, output only the relevant ones."
    )

    try:
        result = inference.ask(prompt, system=system, max_tokens=3000, timeout=180)
    except Exception as e:
        print(f"ERROR calling inference: {e}", file=sys.stderr)
        sys.exit(0)

    # Parse model output
    items = []
    for block in result.strip().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        fields = {}
        for line in block.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                fields[key.strip()] = val.strip()
        if "TITLE" in fields and "WHY" in fields:
            hn_url = fields.get("HN_URL", "#")
            story_url = fields.get("STORY_URL", hn_url)
            items.append({
                "title": fields["TITLE"],
                "hn_url": hn_url,
                "story_url": story_url,
                "points": fields.get("POINTS", "?"),
                "why": fields["WHY"],
            })

    # Build HTML
    html_lines = ['<div class="prose">']
    if items:
        for item in items:
            link_url = item["story_url"] if item["story_url"] != "#" else item["hn_url"]
            html_lines.append(
                f'<p>'
                f'<a href="{link_url}" style="color:var(--accent)">{item["title"]}</a>'
                f' <span style="color:var(--muted)">· {item["points"]} pts</span>'
                f'<br><span style="font-size:12px">{item["why"]}</span>'
                f'</p>'
            )
    else:
        html_lines.append(
            '<p style="color:var(--muted);font-style:italic">Nothing surfaced today</p>'
        )
    html_lines.append('</div>')
    html = "\n".join(html_lines)

    subprocess.run([sys.executable, OPS_WRITE, SECTION], input=html, text=True, check=False)
    print(f"HN sweep done — {today} — {len(filtered)} stories fetched, {len(items)} selected")
    for item in items:
        print(f"  · {item['title']} ({item['points']} pts)")


if __name__ == "__main__":
    main()
