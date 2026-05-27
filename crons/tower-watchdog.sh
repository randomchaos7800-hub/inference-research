#!/usr/bin/env bash
# Tower watchdog — ping + health check, alert only if down. Runs every 5 min.
set -uo pipefail

VAULT="$HOME/.vault/vault.sh"
CHANNEL="C0AHSAE9YN9"
TOWER="100.120.50.35"

alert() {
    local msg="$1"
    local token
    token=$("$VAULT" get slack_kato_bot_token 2>/dev/null) || return
    curl -s -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"channel\":\"$CHANNEL\",\"text\":\"🔴 tower-watchdog: $msg\",\"mrkdwn\":true}" \
        > /dev/null
}

ping -c 2 -W 3 "$TOWER" > /dev/null 2>&1 || { alert "cha0tiktower unreachable (ping failed). Cycle: \`python3 ~/scripts/tower-plug.py cycle\`"; exit 0; }

HEALTH=$(curl -sf --max-time 5 "http://$TOWER:8010/health" 2>/dev/null)
echo "$HEALTH" | grep -q '"status":"ok"' || { alert ":8010/health failed — inference down. Cycle: \`python3 ~/scripts/tower-plug.py cycle\`"; exit 0; }
