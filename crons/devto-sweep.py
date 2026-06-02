#!/usr/bin/env python3
"""Dev.to sweep — fetch fresh AI/LLM/agents articles, pick 5 via local inference, post to ops dashboard. Runs 9:30AM daily."""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import inference

OPS_WRITE = "/home/dino/scripts/ops-write.py"
SECTION = "devto"

ENDPOINTS = [
    "https://dev.to/api/articles?tag=ai&per_page=30&state=fresh",
    "https://dev.to/api/articles?tag=llm&per_page=20&state=fresh",
    "https://dev.to/api/articles?tag=agents&per_page=20&state=fresh",
]

MIN_REACTIONS = 5
MAX_TO_MODEL = 20


def fetch_articles(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"ERROR fetching {url}: {e}", file=sys.stderr)
        return []


def main():
    today = date.today().isoformat()

    # Fetch and deduplicate
    all_articles = []
    seen_ids = set()
    for url in ENDPOINTS:
        for article in fetch_articles(url):
            aid = article.get("id")
            if aid and aid not in seen_ids:
                seen_ids.add(aid)
                all_articles.append(article)

    # Filter by reactions
    filtered = [a for a in all_articles if (a.get("positive_reactions_count") or 0) >= MIN_REACTIONS]
    filtered.sort(key=lambda a: a.get("positive_reactions_count", 0), reverse=True)

    if not filtered:
        html = (
            '<div class="prose">'
            '<p style="color:var(--muted);font-style:italic">Nothing surfaced today</p>'
            '</div>'
        )
        subprocess.run([sys.executable, OPS_WRITE, SECTION], input=html, text=True, check=False)
        print(f"Dev.to sweep done — {today} — no articles passed filter")
        return

    # Build article list for model
    candidates = filtered[:MAX_TO_MODEL]
    article_list = "\n\n".join(
        f"[{i+1}] {a.get('title', '(no title)')}\n"
        f"Reactions: {a.get('positive_reactions_count', 0)}\n"
        f"Tags: {', '.join(a.get('tag_list', []))}\n"
        f"URL: {a.get('canonical_url') or a.get('url', '')}\n"
        f"Description: {(a.get('description') or '')[:200]}"
        for i, a in enumerate(candidates)
    )

    system = (
        "You are a signal filter for a solo operator building local AI agents, memory systems, "
        "and sovereign compute. Be direct and opinionated. No hedging, no fluff."
    )
    prompt = (
        f"Today is {today}. Here are fresh Dev.to articles:\n\n{article_list}\n\n"
        "Pick the 5 most relevant for a solo operator building local AI agents, memory systems, "
        "and sovereign compute. For each, reply with EXACTLY this format — one block per article, "
        "no extra text before or after:\n\n"
        "TITLE: <exact title>\n"
        "URL: <canonical URL>\n"
        "REACTIONS: <number>\n"
        "WHY: <one sentence why it matters>\n\n"
        "Output exactly 5 blocks separated by a blank line. If fewer than 5 articles are genuinely "
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
            items.append({
                "title": fields["TITLE"],
                "url": fields.get("URL", "#"),
                "reactions": fields.get("REACTIONS", "?"),
                "why": fields["WHY"],
            })

    # Build HTML
    html_lines = ['<div class="prose">']
    if items:
        for item in items:
            html_lines.append(
                f'<p>'
                f'<a href="{item["url"]}" style="color:var(--accent)">{item["title"]}</a>'
                f' <span style="color:var(--muted)">· {item["reactions"]} ♥</span>'
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
    print(f"Dev.to sweep done — {today} — {len(filtered)} articles fetched, {len(items)} selected")
    for item in items:
        print(f"  · {item['title']} ({item['reactions']} ♥)")


if __name__ == "__main__":
    main()
