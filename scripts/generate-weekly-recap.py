#!/usr/bin/env python3
"""Weekly recap generator — runs Monday 7am via cron.
Fetches SUMMARY.md from GitHub, generates recap via Claude, publishes to /weekly only.
Does NOT touch posts.json or the writing section."""

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

REAL_HOME = Path(os.environ.get("REAL_HOME") or os.environ.get("DINO_HOME") or "/home/dino")
VAULT = REAL_HOME / ".vault/vault.sh"
SITE_DIR = REAL_HOME / "www/dinovitale.com"
WEEKLY_HTML = SITE_DIR / "weekly.html"

GITHUB_SUMMARY_URL = "https://api.github.com/repos/randomchaos7800-hub/operator-context/contents/SUMMARY.md"


def vault_get(key: str) -> str:
    result = subprocess.run([str(VAULT), "get", key], capture_output=True, text=True)
    return result.stdout.strip()


def fetch_summary(github_token: str) -> str:
    req = urllib.request.Request(
        GITHUB_SUMMARY_URL,
        headers={
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3.raw",
            "User-Agent": "vitale-dynamics-weekly-recap",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8")


def extract_recent_sessions(summary: str, days: int = 7) -> str:
    """Pull session blocks from the last N days out of SUMMARY.md."""
    cutoff = datetime.now() - timedelta(days=days)
    lines = summary.splitlines()
    blocks = []
    current_block = []
    current_date = None
    in_session = False

    for line in lines:
        m = re.match(r"^###\s+Session\s+.{0,10}(\d{4}-\d{2}-\d{2})", line)
        if m:
            if current_block and current_date and current_date >= cutoff:
                blocks.append("\n".join(current_block))
            try:
                current_date = datetime.strptime(m.group(1), "%Y-%m-%d")
            except ValueError:
                current_date = None
            current_block = [line]
            in_session = True
            continue

        if re.match(r"^##\s+(?!#)", line) and in_session:
            if current_block and current_date and current_date >= cutoff:
                blocks.append("\n".join(current_block))
            current_block = []
            current_date = None
            in_session = False
            continue

        if in_session:
            current_block.append(line)

    if current_block and current_date and current_date >= cutoff:
        blocks.append("\n".join(current_block))

    if not blocks:
        return summary[:6000]

    return "\n\n---\n\n".join(blocks)


def generate_recap(openrouter_key: str, source_text: str, week_of: str) -> str:
    """Generate the recap via OpenRouter. Returns HTML body (p and h3 tags only)."""
    payload = {
        "model": "deepseek/deepseek-chat",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": f"""You are writing the weekly recap for dinovitale.com — Dino Vitale's personal site documenting his AI agent lab.

Week of: {week_of}

Source material (session notes from the past week):
{source_text}

Write a weekly recap that is:
- 300-400 words
- Detailed but readable — not a bullet dump, not a press release
- Covers: what shipped, what broke or got fixed, any infrastructure changes, and what's coming
- Written in first person as if Dino is writing it (direct, honest, low hype)
- Organized with 3-4 short sections using <h3> subheads
- Uses <p> tags for paragraphs, <h3> for section headers
- No intro preamble like "This week" — just get into it
- No outro like "Stay tuned" — end on the last actual fact

Return ONLY the HTML body content (p and h3 tags). No wrapping divs, no html/body tags.""",
            }
        ],
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read().decode())
    return resp["choices"][0]["message"]["content"].strip()


def publish_post(title: str, display_date: str, week_of: str, body_html: str, filename: str):
    """Write the post HTML file directly — does not touch posts.json or the writing section."""
    template = (SITE_DIR / "posts/_template.html").read_text()
    post_html = (
        template
        .replace("POST_TITLE", title)
        .replace("POST_DATE", display_date)
        .replace("POST_DESCRIPTION", f"Weekly recap for {week_of} — Vitale Dynamics build log")
        .replace("POST_BODY", body_html)
    )
    out_path = SITE_DIR / "posts" / filename
    out_path.write_text(post_html)
    print(f"[weekly-recap] Post written: {out_path}")


def update_weekly_archive(title: str, display_date: str, filename: str):
    """Insert the new recap at the top of weekly.html's archive list."""
    html = WEEKLY_HTML.read_text()
    entry = (
        f'\n    <div class="recap-entry">\n'
        f'      <a href="posts/{filename}">{title}</a>\n'
        f'      <span class="recap-entry-date">{display_date}</span>\n'
        f'    </div>'
    )
    new_html = re.sub(
        r"<!-- WEEKLY_START -->.*?<!-- WEEKLY_END -->",
        f"<!-- WEEKLY_START -->{entry}\n    <!-- WEEKLY_END -->",
        html,
        flags=re.DOTALL,
    )
    WEEKLY_HTML.write_text(new_html)


def post_to_slack(token: str, channel: str, text: str):
    payload = json.dumps({"channel": channel, "text": text}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        resp = json.loads(r.read().decode())
    if not resp.get("ok"):
        print(f"[weekly-recap] Slack post failed: {resp.get('error')}", file=sys.stderr)


def main():
    print(f"[weekly-recap] Starting — {datetime.now().isoformat()}")

    github_token = vault_get("github_token_mike")
    openrouter_key = vault_get("openrouter_api_key")
    slack_token = vault_get("slack_ops_bot_token")
    slack_channel = vault_get("slack_channel_opslog")

    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_of = monday.strftime("%B %-d, %Y")
    slug = "week-of-" + monday.strftime("%b-%d").lower()
    title = f"Week of {week_of}"
    date_str = monday.strftime("%Y-%m-%d")
    display_date = monday.strftime("%B %-d, %Y")
    filename = f"{date_str}-{slug}.html"

    # Skip if already published this week
    out_path = SITE_DIR / "posts" / filename
    if out_path.exists():
        print(f"[weekly-recap] Already published for this week: {filename}")
        return

    print(f"[weekly-recap] Generating: {title}")

    print("[weekly-recap] Fetching SUMMARY.md from GitHub...")
    summary = fetch_summary(github_token)
    source = extract_recent_sessions(summary, days=7)
    print(f"[weekly-recap] Extracted {len(source)} chars of session content")

    print("[weekly-recap] Calling OpenRouter for recap generation...")
    body_html = generate_recap(openrouter_key, source, week_of)
    print(f"[weekly-recap] Generated {len(body_html)} chars of HTML")

    publish_post(title, display_date, week_of, body_html, filename)
    update_weekly_archive(title, display_date, filename)
    print("[weekly-recap] weekly.html archive updated")

    post_url = f"https://dinovitale.com/posts/{filename}"
    post_to_slack(slack_token, slack_channel, f":newspaper: *Weekly recap published* — {title}\n{post_url}")

    print(f"[weekly-recap] Done — {post_url}")


if __name__ == "__main__":
    main()
