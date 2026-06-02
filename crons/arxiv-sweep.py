#!/usr/bin/env python3
"""arXiv sweep — fetch today's cs.AI + cs.CL papers, summarize top 5, post to Slack. Runs 7AM daily."""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import inference

ARXIV_DIR = os.path.expanduser("~/crons/data/arxiv")
MAX_PAPERS = 40  # fetch this many, model picks top 5


def fetch_arxiv(category, max_results=20):
    url = (
        f"http://export.arxiv.org/api/query?search_query=cat:{category}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode()


def parse_entries(xml):
    import re
    entries = []
    for entry in re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL):
        title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        link = re.search(r'<id>(.*?)</id>', entry)
        authors = re.findall(r"<name>(.*?)</name>", entry)
        if title and summary and link:
            entries.append({
                "title": title.group(1).strip().replace("\n", " "),
                "summary": summary.group(1).strip().replace("\n", " ")[:500],
                "url": link.group(1).strip(),
                "authors": ", ".join(authors[:3]),
            })
    return entries


def main():
    today = date.today().isoformat()

    # Fetch from both categories
    papers = []
    for cat in ("cs.AI", "cs.CL"):
        xml = fetch_arxiv(cat, max_results=20)
        papers.extend(parse_entries(xml))

    # Deduplicate by URL
    seen = set()
    unique = []
    for p in papers:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)

    if not unique:
        print("No papers fetched — skipping")
        return

    # Ask local inference to pick and summarize the most relevant
    paper_list = "\n\n".join(
        f"[{i+1}] {p['title']}\nAuthors: {p['authors']}\nURL: {p['url']}\nAbstract: {p['summary']}"
        for i, p in enumerate(unique[:MAX_PAPERS])
    )

    system = (
        "You are a research filter for a solo operator building local AI agents. "
        "Be direct and opinionated. No academic hedging."
    )
    prompt = (
        f"Today is {today}. Here are recent arXiv papers from cs.AI and cs.CL:\n\n{paper_list}\n\n"
        "Pick the 5 most relevant for someone building autonomous agents, memory systems, "
        "local inference, or applied AI infrastructure. For each:\n"
        "- Title and URL\n"
        "- One sentence: what it actually does\n"
        "- One sentence: why it matters for agent builders\n\n"
        "If nothing is genuinely interesting, say so in one line. No fluff."
    )

    result = inference.ask(prompt, system=system, max_tokens=1024, timeout=120)

    if "[SILENT]" in result or "nothing genuinely" in result.lower():
        print("Nothing interesting today — skipping")
        return

    # Save to disk for daily-research-brief to consume
    os.makedirs(ARXIV_DIR, exist_ok=True)
    out_file = os.path.join(ARXIV_DIR, f"arxiv-{today}.md")
    with open(out_file, "w") as f:
        f.write(f"---\nsource_agent: cron\ndate: {today}\ntags: [arxiv,research,{today}]\n---\n\n")
        f.write(result)

    # Write to ops dashboard
    html_lines = ['<div class="prose">']
    has_content = False
    for line in result.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        has_content = True
        if line.startswith(("- ", "• ", "* ")):
            html_lines.append(f'<p style="margin:5px 0 5px 0">{line[2:].strip()}</p>')
        else:
            html_lines.append(f'<p><strong>{line}</strong></p>')
    if not has_content:
        html_lines.append(f'<p style="color:var(--muted);font-style:italic">No notable papers today — {today}</p>')
    html_lines.append('</div>')
    html = "\n".join(html_lines)

    ops_write = os.path.join(os.path.dirname(__file__), "..", "scripts", "ops-write.py")
    subprocess.run([sys.executable, ops_write, "arxiv"], input=html, text=True, check=False)
    print(f"arXiv sweep done — {today}")


if __name__ == "__main__":
    main()
