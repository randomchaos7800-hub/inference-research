#!/usr/bin/env bash
# Hourly ops check — always writes to ops dashboard. Silent otherwise.
set -uo pipefail

OPS_WRITE="python3 /home/dino/scripts/ops-write.py ops-check"
ISSUES=()
PASSES=()

# Failed systemd units
FAILED=$(systemctl --user is-failed 2>/dev/null | grep -v "^0 units" || true)
if [[ -n "$FAILED" ]]; then
    ISSUES+=("Failed units: $FAILED")
else
    PASSES+=("All units running")
fi

# Disk over 85%
DISK_OK=1
while IFS= read -r line; do
    PCT=$(echo "$line" | awk '{print $5}' | tr -d '%')
    MNT=$(echo "$line" | awk '{print $6}')
    if [[ "$PCT" -ge 85 ]] 2>/dev/null; then
        ISSUES+=("Disk critical: $MNT at ${PCT}%")
        DISK_OK=0
    fi
done < <(df -h 2>/dev/null | tail -n +2)
[[ "$DISK_OK" -eq 1 ]] && PASSES+=("Disk: all clear")

# Inference
HEALTH=$(curl -sf --max-time 5 http://100.120.50.35:8010/health 2>/dev/null)
if echo "$HEALTH" | grep -q '"status":"ok"'; then
    PASSES+=("Inference :8010: ok")
else
    ISSUES+=("Inference :8010 unreachable")
fi

# Build HTML
HTML='<ul class="checklist">'
for p in "${PASSES[@]}"; do
    HTML+="<li class=\"ok\"><span class=\"icon\">✓</span>${p}</li>"
done
for i in "${ISSUES[@]}"; do
    HTML+="<li class=\"fail\"><span class=\"icon\">✗</span>${i}</li>"
done
HTML+='</ul>'

echo "$HTML" | $OPS_WRITE
