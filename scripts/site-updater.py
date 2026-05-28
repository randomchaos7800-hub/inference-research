#!/usr/bin/env python3
# site-updater.py — pulls Substack RSS, updates dinovitale.com writing section
# Runs via cron. No LLM. No Kato.

import json, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

SITE_DIR   = Path("/home/dino/www/dinovitale.com")
INDEX      = SITE_DIR / "index.html"
POSTS_JSON = SITE_DIR / "posts/posts.json"
SEEN_FILE  = Path("/home/dino/.config/site-updater/seen.json")
RSS_URL    = "https://dinoxvitale.substack.com/feed"
SKIP_SLUGS = {"coming-soon"}

def fetch_rss():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        tree = ET.parse(r)
    items = []
    for item in tree.getroot().find("channel").findall("item"):
        title = item.findtext("title", "").strip()
        link  = item.findtext("link", "").strip()
        pub   = item.findtext("pubDate", "").strip()
        if not title or not link:
            continue
        slug = link.rstrip("/").split("/")[-1]
        if slug in SKIP_SLUGS:
            continue
        try:
            dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
        except Exception:
            dt = datetime.now()
        items.append({"title": title, "url": link, "slug": slug,
                      "date": dt.strftime("%Y-%m-%d"),
                      "display_date": dt.strftime("%B %-d, %Y")})
    return items

def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()

def save_seen(seen):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(sorted(seen)))

def load_posts():
    if POSTS_JSON.exists():
        return json.loads(POSTS_JSON.read_text())
    return []

def save_posts(posts):
    POSTS_JSON.write_text(json.dumps(posts, indent=2))

def rebuild_index(posts):
    rows = "\n"
    for p in posts[:10]:
        href  = p.get("url") or p.get("file", "")
        extra = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
        rows += f'      <div class="post-entry">\n'
        rows += f'        <a href="{href}"{extra}>{p["title"]}</a>\n'
        rows += f'        <span class="post-entry-date">{p["display_date"]}</span>\n'
        rows += f'      </div>\n'

    index = INDEX.read_text()
    new_index = re.sub(
        r"<!-- POSTS_START -->.*?<!-- POSTS_END -->",
        f"<!-- POSTS_START -->{rows}      <!-- POSTS_END -->",
        index,
        flags=re.DOTALL,
    )
    INDEX.write_text(new_index)

def main():
    seen  = load_seen()
    posts = load_posts()
    items = fetch_rss()

    new_count = 0
    for item in items:
        if item["slug"] in seen:
            continue
        # add as external substack entry if not already in posts
        existing_slugs = {p.get("slug") for p in posts}
        if item["slug"] not in existing_slugs:
            posts.insert(0, {
                "slug":         item["slug"],
                "title":        item["title"],
                "date":         item["date"],
                "display_date": item["display_date"],
                "url":          item["url"],
            })
            new_count += 1
        seen.add(item["slug"])

    if new_count:
        posts.sort(key=lambda p: p["date"], reverse=True)
        save_posts(posts)
        rebuild_index(posts)
        save_seen(seen)
        print(f"site-updater: added {new_count} post(s), index rebuilt")
    else:
        print("site-updater: nothing new")

if __name__ == "__main__":
    main()
