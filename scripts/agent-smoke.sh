#!/usr/bin/env bash
# Two-tier health check for cha0tikhome agent stack.
# Tier 1 (--tier1): safe endpoint checks, no quota. Run every 15min via cron.
# Tier 2 (--tier2): functional service checks. Run 2x/day (6AM, 6PM).
# Always writes to ops dashboard.

set -uo pipefail

REAL_HOME="${REAL_HOME:-${DINO_HOME:-/home/dino}}"
PROXY="http://100.120.50.35:8010"
LATENCY_WARN_MS=500
INFERENCE_STATUS_FILE="$REAL_HOME/www/dinovitale.com/data/inference-status.json"
INFERENCE_STALE_MINS=20
OPS_WRITE="python3 $REAL_HOME/scripts/ops-write.py smoke"

FAILURES=()
PASSES=()

tier1_checks() {
    local http_code latency_s latency_ms status model_count

    http_code=$(curl -s -o /tmp/agent-smoke-health.json -w '%{http_code}' \
        --connect-timeout 5 --max-time 10 "$PROXY/health" 2>/dev/null) || http_code="000"
    latency_s=$(curl -s -o /dev/null -w '%{time_total}' \
        --connect-timeout 5 --max-time 10 "$PROXY/health" 2>/dev/null) || latency_s="99"
    latency_ms=$(python3 -c "print(int(float('$latency_s') * 1000))" 2>/dev/null || echo "0")

    if [ "$http_code" != "200" ]; then
        FAILURES+=("proxy /health HTTP $http_code")
    else
        status=$(python3 -c "import json; d=json.load(open('/tmp/agent-smoke-health.json')); print(d.get('status','?'))" 2>/dev/null || echo "err")
        if [ "$status" = "ok" ]; then
            PASSES+=("proxy /health: ok (${latency_ms}ms)")
        else
            FAILURES+=("proxy /health status=$status")
        fi
        if [ "$latency_ms" -gt "$LATENCY_WARN_MS" ] 2>/dev/null; then
            FAILURES+=("proxy latency ${latency_ms}ms > ${LATENCY_WARN_MS}ms")
        fi
    fi

    http_code=$(curl -s -o /tmp/agent-smoke-models.json -w '%{http_code}' \
        --connect-timeout 5 --max-time 10 "$PROXY/v1/models" 2>/dev/null) || http_code="000"
    if [ "$http_code" != "200" ]; then
        FAILURES+=("proxy /v1/models HTTP $http_code")
    else
        model_count=$(python3 -c "import json; d=json.load(open('/tmp/agent-smoke-models.json')); print(len(d.get('data',[])))" 2>/dev/null || echo "0")
        if [ "$model_count" -eq 0 ] 2>/dev/null; then
            FAILURES+=("/v1/models: 0 models loaded")
        else
            PASSES+=("/v1/models: ${model_count} loaded")
        fi
    fi
}

tier2_checks() {
    for svc in harness-api.service mike.service mike-irc.service mike-irchighway.service; do
        if systemctl --user is-active "$svc" --quiet 2>/dev/null; then
            PASSES+=("${svc%.service}: active")
        else
            FAILURES+=("${svc%.service}: not active")
        fi
    done

    if [ -f "$INFERENCE_STATUS_FILE" ]; then
        local now_s file_mtime file_age_s age_mins stale_threshold
        now_s=$(date +%s)
        file_mtime=$(stat -c '%Y' "$INFERENCE_STATUS_FILE" 2>/dev/null || echo "0")
        file_age_s=$(( now_s - file_mtime ))
        stale_threshold=$(( INFERENCE_STALE_MINS * 60 ))
        age_mins=$(( file_age_s / 60 ))
        if [ "$file_age_s" -gt "$stale_threshold" ] 2>/dev/null; then
            FAILURES+=("inference-status.json: ${age_mins}min old (threshold ${INFERENCE_STALE_MINS}min)")
        else
            PASSES+=("inference-status.json: fresh (${age_mins}min old)")
        fi
    else
        FAILURES+=("inference-status.json: not found")
    fi
}

main() {
    local mode="--tier1"
    while [ $# -gt 0 ]; do
        case "$1" in
            --tier1|--tier2) mode="$1" ;;
            --no-alert) : ;;
            *) echo "Usage: agent-smoke.sh [--tier1|--tier2]" >&2; exit 1 ;;
        esac
        shift
    done

    tier1_checks
    [ "$mode" = "--tier2" ] && tier2_checks

    local HTML='<ul class="checklist">'
    for p in "${PASSES[@]}"; do
        HTML+="<li class=\"ok\"><span class=\"icon\">✓</span>${p}</li>"
    done
    for f in "${FAILURES[@]}"; do
        HTML+="<li class=\"fail\"><span class=\"icon\">✗</span>${f}</li>"
    done
    HTML+="</ul>"
    [ "$mode" = "--tier2" ] && HTML+='<div class="sub">tier2 run</div>' || HTML+='<div class="sub">tier1 run</div>'

    echo "$HTML" | $OPS_WRITE

    [ ${#FAILURES[@]} -gt 0 ] && exit 1
    exit 0
}

main "$@"
