#!/usr/bin/env bash
# publish-post.sh — Kato calls this to publish a post to dinovitale.com
# Usage: ./publish-post.sh "<slug>" "<title>" "<date YYYY-MM-DD>" "<body HTML>"
# Body HTML: use <p> tags for paragraphs, <h3> for subheads.

set -euo pipefail

SITE_DIR="/home/dino/www/dinovitale.com"
POSTS_DIR="$SITE_DIR/posts"
INDEX="$SITE_DIR/index.html"
TEMPLATE="$POSTS_DIR/_template.html"
POSTS_JSON="$POSTS_DIR/posts.json"

SLUG="$1"
TITLE="$2"
DATE="$3"
BODY="$4"

DISPLAY_DATE=$(date -d "$DATE" "+%B %-d, %Y" 2>/dev/null || echo "$DATE")
FILENAME="${DATE}-${SLUG}.html"
OUTFILE="$POSTS_DIR/$FILENAME"

# ── 1. Write post file ────────────────────────────────────────────────────────
cp "$TEMPLATE" "$OUTFILE"
python3 - "$OUTFILE" "$TITLE" "$DISPLAY_DATE" "$BODY" <<'PYEOF'
import sys
path, title, display_date, body = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
content = open(path).read()
content = content.replace("POST_TITLE", title)
content = content.replace("POST_DATE", display_date)
content = content.replace("POST_DESCRIPTION", title[:160])
content = content.replace("POST_BODY", body)
open(path, "w").write(content)
print(f"Post written: {path}")
PYEOF

# ── 2. Update posts.json ──────────────────────────────────────────────────────
python3 - "$POSTS_JSON" "$SLUG" "$TITLE" "$DATE" "$DISPLAY_DATE" "$FILENAME" <<'PYEOF'
import sys, json, os
posts_json, slug, title, date, display_date, filename = sys.argv[1:]
existing = json.loads(open(posts_json).read()) if os.path.exists(posts_json) else []
existing = [p for p in existing if p.get("slug") != slug]
posts = [{"slug": slug, "title": title, "date": date, "display_date": display_date, "file": f"posts/{filename}"}] + existing
posts = posts[:20]
with open(posts_json, "w") as f:
    json.dump(posts, f, indent=2)
print(f"posts.json updated ({len(posts)} posts)")
PYEOF

# ── 3. Update writing section in index.html ───────────────────────────────────
python3 - "$POSTS_JSON" "$INDEX" <<'PYEOF'
import sys, json, re

posts_json, index_path = sys.argv[1], sys.argv[2]
posts = json.loads(open(posts_json).read())
recent = posts[:5]

rows = "\n"
for p in recent:
    href = p.get("url") or p.get("file", "")
    extra = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
    rows += f'      <div class="post-entry">\n'
    rows += f'        <a href="{href}"{extra}>{p["title"]}</a>\n'
    rows += f'        <span class="post-entry-date">{p["display_date"]}</span>\n'
    rows += f'      </div>\n'

index = open(index_path).read()
new_index = re.sub(
    r'<!-- POSTS_START -->.*?<!-- POSTS_END -->',
    f'<!-- POSTS_START -->{rows}      <!-- POSTS_END -->',
    index,
    flags=re.DOTALL
)
open(index_path, "w").write(new_index)
print("index.html updated")
PYEOF

echo "Published: $TITLE ($DATE) → posts/$FILENAME"
