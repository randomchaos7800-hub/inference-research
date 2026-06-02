#!/usr/bin/env bash
# Monthly restore drill — proves backups can actually be extracted.
# Rotates through services by month: system → www → vault → mike
# Runs first Sunday of each month at 4AM via cron.
# Writes result to Chronicle daily log. Posts to #ops-log on failure.

set -uo pipefail

REAL_HOME="${REAL_HOME:-${DINO_HOME:-/home/dino}}"
VAULT="$REAL_HOME/.vault/vault.sh"
OPS_LOG_CHANNEL="C0AHSAE9YN9"
BACKUP_BASE="/mnt/jellyfin-backups"
DRILL_DIR="/tmp/restore-drill-test"
CHRONICLE_LOG="$REAL_HOME/.claude/daily-logs/$(date +%Y-%m-%d).md"

MONTH=$(date +%-m)
SERVICES=("system" "www" "vault" "mike")
SERVICE="${SERVICES[$(( (MONTH - 1) % 4 ))]}"

slack_alert() {
    local msg="$1"
    local token
    token=$("$VAULT" get slack_ops_bot_token 2>/dev/null) || return
    curl -s -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"$OPS_LOG_CHANNEL\", \"text\": \"[restore-drill] $msg\", \"unfurl_links\": false}" \
        > /dev/null
}

chronicle_log() {
    local msg="$1"
    echo "" >> "$CHRONICLE_LOG"
    echo "## Restore Drill $(date +%H:%M) — $SERVICE" >> "$CHRONICLE_LOG"
    echo "$msg" >> "$CHRONICLE_LOG"
}

cleanup() {
    rm -rf "$DRILL_DIR"
}
trap cleanup EXIT

# Find most recent backup for this service
ARCHIVE=$(find "$BACKUP_BASE/$SERVICE" -name "*.tar.gz" -type f \
    | sort -r | head -1)

if [ -z "$ARCHIVE" ]; then
    msg="FAIL: no backup archive found in $BACKUP_BASE/$SERVICE"
    echo "$msg" >&2
    slack_alert "$msg"
    chronicle_log "$msg"
    exit 1
fi

ARCHIVE_DATE=$(basename "$ARCHIVE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1 || echo "unknown")
echo "Testing restore: $ARCHIVE"

# Extract to temp dir
rm -rf "$DRILL_DIR"
mkdir -p "$DRILL_DIR"

if ! tar -xzf "$ARCHIVE" -C "$DRILL_DIR" 2>/dev/null; then
    msg="FAIL: extraction failed for $ARCHIVE"
    echo "$msg" >&2
    slack_alert "$msg"
    chronicle_log "$msg"
    exit 1
fi

FILE_COUNT=$(find "$DRILL_DIR" -type f | wc -l)

# Service-specific key file checks
case "$SERVICE" in
    system)
        KEY_CHECK="$DRILL_DIR/.ssh"
        KEY_DESC=".ssh directory"
        ;;
    www)
        KEY_CHECK="$DRILL_DIR/www"
        KEY_DESC="www directory"
        ;;
    vault)
        KEY_CHECK="$DRILL_DIR/.vault/secrets.age"
        KEY_DESC=".vault/secrets.age"
        ;;
    mike)
        KEY_CHECK="$DRILL_DIR/mike/config"
        KEY_DESC="mike/config directory"
        ;;
esac

if [ ! -e "$KEY_CHECK" ]; then
    msg="FAIL: $SERVICE backup from $ARCHIVE_DATE missing expected $KEY_DESC ($FILE_COUNT files extracted)"
    echo "$msg" >&2
    slack_alert "$msg"
    chronicle_log "$msg"
    exit 1
fi

msg="PASS — $SERVICE backup from $ARCHIVE_DATE: $FILE_COUNT files, $KEY_DESC verified"
echo "$msg"
chronicle_log "$msg"
