#!/usr/bin/env python3
"""Wiki growth — write new articles from last 7 days of arXiv files, trigger compile. Runs Monday 6AM."""

import os
import subprocess
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import slack
import inference

ARXIV_DIR = os.path.expanduser("~/crons/data/arxiv")
WIKI_RAW   = os.path.expanduser("~/cha0tikwiki/raw/incoming")
WIKI_INDEX = os.path.expanduser("~/cha0tikwiki/wiki/_index.md")


def get_existing_topics():
    if not os.path.exists(WIKI_INDEX):
        return set()
    content = open(WIKI_INDEX).read()
    import re
    return set(re.findall(r'\[\[([^\]]+)\]\]|^#+\s+(.+)$', content, re.MULTILINE))


def main():
    today = date.today()
    combined = []
    for days_ago in range(7):
        d = (today - timedelta(days=days_ago)).isoformat()
        path = os.path.join(ARXIV_DIR, f"arxiv-{d}.md")
        if os.path.exists(path):
            combined.append(open(path).read())

    if not combined:
        slack.post(f"*📖 Wiki Growth — {today.isoformat()}*\n\nNo arXiv files this week — skipped.", channel=slack.BRIEF)
        return

    content = "\n\n---\n\n".join(combined)

    # Check index
    index_sample = ""
    if os.path.exists(WIKI_INDEX):
        index_sample = open(WIKI_INDEX).read()[:3000]

    system = "You write structured knowledge-base articles for an agent builder. Precise, no fluff."
    prompt = (
        f"Today is {today.isoformat()}. Here are this week's arXiv research summaries:\n\n{content}\n\n"
        f"Existing wiki index (do not duplicate):\n{index_sample}\n\n"
        "Write 3-5 NEW wiki articles on genuinely different topics. "
        "Each article must use EXACTLY this format:\n\n"
        "=== ARTICLE ===\n"
        "SLUG: kebab-case-slug\n"
        "TOPIC: Full Topic Name\n"
        "TAGS: tag1, tag2, tag3\n"
        "SUMMARY: One clear sentence.\n\n"
        "## Core Concept\n[2-3 sentences]\n\n"
        "## Key Claims\n- [Specific claim] (source)\n\n"
        "## Architecture/Approach\n[Technical details]\n\n"
        "## Connections\n[Related slugs]\n\n"
        "## Sources\n- [Title](URL)\n"
        "=== END ===\n\n"
        "Only topics genuinely new to the index. Focus on agent architecture, memory, local inference."
    )

    result = inference.ask(prompt, system=system, max_tokens=2000, timeout=180)

    # Parse and write articles
    os.makedirs(WIKI_RAW, exist_ok=True)
    import re
    articles = re.findall(r"=== ARTICLE ===(.*?)=== END ===", result, re.DOTALL)
    written = []

    for article in articles:
        slug_m = re.search(r"SLUG:\s*(.+)", article)
        topic_m = re.search(r"TOPIC:\s*(.+)", article)
        tags_m  = re.search(r"TAGS:\s*(.+)", article)
        summary_m = re.search(r"SUMMARY:\s*(.+)", article)

        if not slug_m or not topic_m:
            continue

        slug = slug_m.group(1).strip()
        topic = topic_m.group(1).strip()
        tags = tags_m.group(1).strip() if tags_m else "agent,research"
        summary = summary_m.group(1).strip() if summary_m else ""

        body = article.split("SUMMARY:", 1)[-1].split("\n", 1)[-1].strip() if "SUMMARY:" in article else article.strip()

        filename = f"{slug}-{today.isoformat()}.md"
        filepath = os.path.join(WIKI_RAW, filename)
        with open(filepath, "w") as f:
            f.write(f"---\nsource_agent: cron\ndate: {today.isoformat()}\n")
            f.write(f"topic: {topic}\ntags: [{tags}]\nsummary: {summary}\n---\n\n")
            f.write(body)

        written.append(topic)

    if not written:
        slack.post(f"*📖 Wiki Growth — {today.isoformat()}*\n\nNo new articles generated.", channel=slack.BRIEF)
        return

    # Trigger compile in background
    compile_script = os.path.expanduser("~/cha0tikwiki/tools/compile-notify.sh")
    if os.path.exists(compile_script):
        subprocess.Popen(
            ["bash", compile_script, "weekly"],
            stdout=open("/tmp/wiki-compile.log", "w"),
            stderr=subprocess.STDOUT
        )

    msg = (
        f"*📖 Wiki Growth — {today.isoformat()}*\n"
        f"Wrote {len(written)} articles:\n"
        + "\n".join(f"  • {t}" for t in written)
        + "\nCompile running in background."
    )
    slack.post(msg, channel=slack.BRIEF)
    print(f"Wiki growth done — {len(written)} articles — {today.isoformat()}")


if __name__ == "__main__":
    main()
