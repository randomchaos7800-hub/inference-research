#!/usr/bin/env bash
# Nightly context sync — commit and push operator context to GitHub. Runs at 3:05AM.
set -uo pipefail

VAULT="$HOME/.vault/vault.sh"
CHANNEL="C0B651Z4C0P"
REPO="$HOME/.claude"

alert() {
    local token
    token=$("$VAULT" get slack_ops_bot_token 2>/dev/null) || return
    curl -s -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"channel\":\"$CHANNEL\",\"text\":\"⚠️ nightly-context-sync: $1\"}" \
        > /dev/null
}

cd "$REPO" || { alert "repo not found at $REPO"; exit 1; }

git add CLAUDE.md INFRA_RUNBOOK.md 2>/dev/null || true
git diff --cached --quiet && exit 0

git commit -m "nightly context sync $(date '+%Y-%m-%d %H:%M:%S')" || { alert "git commit failed"; exit 1; }
git push origin master 2>&1 || alert "git push failed — check remote"
