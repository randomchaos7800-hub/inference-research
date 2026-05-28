#!/bin/bash
# mollydog — grants Codex/Claude session-scoped sudo until the shell exits.

RULE_FILE=/etc/sudoers.d/agent-session
LOCK_FILE=/tmp/mollydog.pid
RULE="dino ALL=(ALL) NOPASSWD: ALL"
MAX_AGE_HOURS=4

cleanup() {
    echo ""
    echo "Revoking agent sudo access..."
    sudo rm -f "$RULE_FILE"
    rm -f "$LOCK_FILE"
    echo "Access revoked. Mollydog out."
    exit 0
}

# Refuse if already running
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "mollydog is already running (PID $PID). Only one session allowed."
        exit 1
    else
        # Stale lock — clean up and proceed
        rm -f "$LOCK_FILE"
        sudo rm -f "$RULE_FILE"
    fi
fi

echo $$ > "$LOCK_FILE"

trap cleanup EXIT INT TERM

# Install the rule (one password prompt here)
echo "$RULE" | sudo tee "$RULE_FILE" > /dev/null
sudo chmod 440 "$RULE_FILE"

# Verify it looks right
if ! sudo visudo -cf "$RULE_FILE" &>/dev/null; then
    echo "ERROR: sudoers rule failed validation. Removing."
    sudo rm -f "$RULE_FILE"
    rm -f "$LOCK_FILE"
    exit 1
fi

echo ""
echo "  mollydog is running (PID $$)"
echo "  Agent sudo access: ACTIVE (system-wide)"
echo "  Press Ctrl+C or close this window to revoke."
echo ""

# Hold open until user kills it
while true; do
    sleep 60
    # Safety check: remove if somehow we've been running > MAX_AGE_HOURS
    if [ -f "$RULE_FILE" ]; then
        AGE=$(( $(date +%s) - $(stat -c %Y "$RULE_FILE") ))
        if [ "$AGE" -gt $(( MAX_AGE_HOURS * 3600 )) ]; then
            echo "Max session time (${MAX_AGE_HOURS}h) reached. Revoking automatically."
            cleanup
        fi
    else
        # Rule was removed externally (e.g. cron cleanup) — exit cleanly
        rm -f "$LOCK_FILE"
        echo "Access rule removed externally. Mollydog out."
        exit 0
    fi
done
