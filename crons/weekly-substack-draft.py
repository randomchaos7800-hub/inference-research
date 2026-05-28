#!/usr/bin/env python3
"""Generate a weekly Substack draft from recent research and save it directly to Substack."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import inference

ROOT = Path("/home/dino")
ARXIV_DIR = ROOT / "crons" / "data" / "arxiv"
POSTS_JSON = ROOT / "www" / "dinovitale.com" / "posts" / "posts.json"
BACKUP_DIR = ROOT / "mike-memory" / "substack_drafts"
VAULT = ROOT / ".vault" / "vault.sh"
PUBLICATION_ID = 8122889
AUTHOR_ID = 465904164
SUBSTACK_BASE = "https://dinoxvitale.substack.com"
LOG_PREFIX = "weekly-substack-draft"


def vault_get(key: str) -> str:
    result = subprocess.run(
        [str(VAULT), "get", key],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def read_recent_arxiv(days: int = 10) -> str:
    chunks = []
    today = date.today()
    for days_ago in range(days):
        d = (today - timedelta(days=days_ago)).isoformat()
        path = ARXIV_DIR / f"arxiv-{d}.md"
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(chunks)


def read_recent_briefs(days: int = 10) -> str:
    brief_dir = ROOT / "crons" / "data" / "briefs"
    if not brief_dir.exists():
        return ""

    chunks = []
    today = date.today()
    for days_ago in range(days):
        d = (today - timedelta(days=days_ago)).isoformat()
        for path in sorted(brief_dir.glob(f"*{d}*.md")):
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(chunks)


def read_recent_context(limit: int = 7) -> str:
    notes_dir = ROOT / "mike-memory" / "notes"
    if not notes_dir.exists():
        return ""

    recent_paths = sorted(
        [path for path in notes_dir.glob("*.md") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:limit]
    chunks = []
    for path in recent_paths:
        chunks.append(f"## {path.name}\n{path.read_text(encoding='utf-8')}")
    return "\n\n---\n\n".join(chunks)


def read_recent_titles(limit: int = 12) -> str:
    if not POSTS_JSON.exists():
        return ""
    data = json.loads(POSTS_JSON.read_text(encoding="utf-8"))
    lines = []
    for item in data[:limit]:
        title = item.get("title", "").strip()
        display_date = item.get("display_date") or item.get("date", "")
        if title:
            lines.append(f"- {display_date}: {title}")
    return "\n".join(lines)


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "untitled"


def split_title_and_body(text: str) -> tuple[str, str]:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    if not lines:
        return "Untitled Draft", ""

    first = lines[0].strip()
    if first.startswith("# "):
        return first[2:].strip(), "\n".join(lines[1:]).strip()
    if len(first) <= 120:
        return first, "\n".join(lines[1:]).strip()
    return "Untitled Draft", "\n".join(lines).strip()


def build_prompt(topic: str | None = None) -> str:
    arxiv = read_recent_arxiv()
    briefs = read_recent_briefs()
    context = read_recent_context()
    titles = read_recent_titles()
    today = date.today().isoformat()
    topic_block = ""
    if topic:
        topic_block = (
            "\nRequested topic override:\n"
            f"- Center the article on: {topic}\n"
            "- Treat this as the primary thesis, while still grounding it in the recent materials below.\n"
        )

    return f"""Today is {today}.

You are drafting Dino's weekly Substack article.

Your job:
1. Pick the strongest topic from the past 7-10 days of research, local lab work, and public writing.
2. Avoid repeating the recent published pieces.
3. Write a full working draft Dino can revise and publish.

{topic_block}

Hard requirements:
- Return plain Markdown only.
- First line must be the title, as a Markdown H1.
- Target 1000-1600 words.
- Sharp lede. No generic AI-intro filler.
- Use concrete observations, technical specifics, and real-world implications.
- Write like a practiced independent operator, not a corporate content team.
- Do not invent benchmarks, quotes, or external facts not supported by the material below.
- If you use a claim from the research inputs, keep it at a level Dino can stand behind after review.
- Do not name a mechanism, architecture, or result unless it is explicitly supported by the provided materials.
- If a paper seems suggestive but not fully clear, describe it cautiously as an exploration or signal, not as an established result.
- Prefer themes, constraints, and operational implications over speculative technical detail.
- Do not present any single preprint as production-ready unless the provided material directly supports that conclusion.
- End with a short `Revision Notes` section listing 3-5 things Dino should verify, tighten, or personalize before publishing.

Recent published titles to avoid repeating directly:
{titles or "(none found)"}

Recent research briefs:
{briefs or "(none found)"}

Recent arXiv / research summaries:
{arxiv or "(none found)"}

Recent local context and notes:
{context or "(none found)"}
"""


def markdown_to_plaintext(markdown_text: str) -> str:
    text = markdown_text
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "- ", text, flags=re.MULTILINE)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def substack_request(method: str, path: str, payload: dict | None = None) -> dict:
    sid = vault_get("substack_sid")
    cookies = vault_get("substack_cookies")
    headers = {
        "user-agent": "Mozilla/5.0",
        "accept": "application/json",
        "cookie": f"substack.sid={sid}; {cookies}",
    }
    data = None
    if payload is not None:
        headers["content-type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(f"{SUBSTACK_BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def create_substack_draft() -> dict:
    return substack_request(
        "POST",
        "/api/v1/drafts",
        {"draft_bylines": [{"id": AUTHOR_ID, "name": "Dino X Vitale"}]},
    )


def update_substack_draft(draft_id: int, title: str, body_text: str) -> dict:
    subtitle = "Weekly draft generated from recent Boundary Labs research and notes."
    return substack_request(
        "PUT",
        f"/api/v1/drafts/{draft_id}",
        {
            "draft_title": title,
            "draft_subtitle": subtitle,
            "draft_body": body_text,
            "should_send_email": False,
            "audience": "everyone",
            "write_comment_permissions": "everyone",
        },
    )


def save_local_backup(title: str, article_markdown: str, draft_id: int) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"{ts}_{slugify(title)}.md"
    footer = (
        f"\n\n---\n"
        f"substack_draft_id: {draft_id}\n"
        f"substack_edit_url: {SUBSTACK_BASE}/publish/post/{draft_id}\n"
    )
    path.write_text(article_markdown.rstrip() + footer, encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--topic",
        help="Optional topic override for a one-off Substack draft",
    )
    args = parser.parse_args()

    prompt = build_prompt(topic=args.topic)
    system = (
        "You write for a technically serious solo operator. "
        "The voice is direct, specific, and evidence-driven. "
        "This is a draft for Dino X Vitale's Substack about AI systems, local inference, "
        "agent memory, alignment, or operating an independent lab."
    )
    draft_markdown = inference.ask(prompt, system=system, max_tokens=2200, temperature=0.75, timeout=300).strip()
    title, body_markdown = split_title_and_body(draft_markdown)
    body_text = markdown_to_plaintext(body_markdown)

    created = create_substack_draft()
    draft_id = created["id"]
    updated = update_substack_draft(draft_id, title, body_text)

    article_markdown = f"# {title}\n\n{body_markdown.strip()}\n"
    backup_path = save_local_backup(title, article_markdown, draft_id)

    word_count = len(re.findall(r"\b\w+\b", body_markdown))
    print(f"{LOG_PREFIX}: saved Substack draft {draft_id}")
    print(f"{LOG_PREFIX}: title={updated.get('draft_title')!r} words={word_count}")
    print(f"{LOG_PREFIX}: edit_url={SUBSTACK_BASE}/publish/post/{draft_id}")
    print(f"{LOG_PREFIX}: backup={backup_path}")


if __name__ == "__main__":
    main()
