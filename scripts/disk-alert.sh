#!/usr/bin/env bash
# Alert to #ops-log if root filesystem exceeds threshold
set -uo pipefail

THRESHOLD=80
REAL_HOME="${REAL_HOME:-${DINO_HOME:-/home/dino}}"
VAULT="$REAL_HOME/.vault/vault.sh"
OPS_LOG_CHANNEL="C0AHSAE9YN9"

USAGE=$(df / --output=pcent | tail -1 | tr -d ' %')

if [ "$USAGE" -ge "$THRESHOLD" ]; then
    token=$("$VAULT" get slack_kato_bot_token 2>/dev/null) || exit 1
    curl -s -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"$OPS_LOG_CHANNEL\", \"text\": \":warning: [disk-alert] cha0tikhome root filesystem at ${USAGE}% — action needed\", \"unfurl_links\": false}" \
        > /dev/null
fi
