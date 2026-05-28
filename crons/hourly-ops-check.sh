#!/usr/bin/env bash
# Hourly ops check — silent on green, posts to #ops-log only on anomaly.
set -uo pipefail

VAULT="$HOME/.vault/vault.sh"
CHANNEL="C0B651Z4C0P"
ISSUES=()

alert() {
    local token
    token=$("$VAULT" get slack_kato_bot_token 2>/dev/null) || return
    local msg
    msg=$(printf '%s\n' "${ISSUES[@]}")
    curl -s -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"channel\":\"$CHANNEL\",\"text\":\"⚠️ *hourly-ops-check* $(date '+%H:%M')\n$msg\",\"mrkdwn\":true}" \
        > /dev/null
}

# Failed systemd units
FAILED=$(systemctl --user is-failed 2>/dev/null | grep -v "^0 units" || true)
[[ -n "$FAILED" ]] && ISSUES+=("Failed units: $FAILED")

# Disk over 85%
while IFS= read -r line; do
    PCT=$(echo "$line" | awk '{print $5}' | tr -d '%')
    MNT=$(echo "$line" | awk '{print $6}')
    [[ "$PCT" -ge 85 ]] && ISSUES+=("Disk critical: $MNT at ${PCT}%")
done < <(df -h 2>/dev/null | tail -n +2)

# Inference down
HEALTH=$(curl -sf --max-time 5 http://100.120.50.35:8010/health 2>/dev/null)
echo "$HEALTH" | grep -q '"status":"ok"' || ISSUES+=("Inference :8010 unreachable")

[[ ${#ISSUES[@]} -gt 0 ]] && alert
