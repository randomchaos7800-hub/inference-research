#!/usr/bin/env bash
# Two-tier health check for cha0tikhome agent stack.
# Tier 1 (--tier1): safe endpoint checks, no quota. Run every 15min via cron.
# Tier 2 (--tier2): functional service checks. Run 2x/day (6AM, 6PM).
# Success is always silent. Failures post to #ops-log.

set -uo pipefail

VAULT="$HOME/.vault/vault.sh"
PROXY="http://100.120.50.35:8010"
OPS_LOG_CHANNEL="C0AHSAE9YN9"
LATENCY_WARN_MS=500
INFERENCE_STATUS_FILE="$HOME/www/dinovitale.com/data/inference-status.json"
INFERENCE_STALE_MINS=20

FAILURES=()

slack_alert() {
    local msg="$1"
    local token
    token=$("$VAULT" get slack_kato_bot_token 2>/dev/null) || return
    curl -s -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"$OPS_LOG_CHANNEL\", \"text\": \"[agent-smoke] $msg\", \"unfurl_links\": false}" \
        > /dev/null
}

tier1_checks() {
    # 1. Proxy health endpoint
    local health_response
    local http_code
    local latency_s
    http_code=$(curl -s -o /tmp/agent-smoke-health.json -w '%{http_code}' \
        --connect-timeout 5 --max-time 10 "$PROXY/health" 2>/dev/null) || http_code="000"
    latency_s=$(curl -s -o /dev/null -w '%{time_total}' \
        --connect-timeout 5 --max-time 10 "$PROXY/health" 2>/dev/null) || latency_s="99"

    if [ "$http_code" != "200" ]; then
        FAILURES+=("proxy /health returned HTTP $http_code (expected 200)")
    else
        local status
        status=$(python3 -c "import json,sys; d=json.load(open('/tmp/agent-smoke-health.json')); print(d.get('status','unknown'))" 2>/dev/null || echo "parse_error")
        [ "$status" != "ok" ] && FAILURES+=("proxy /health status=$status (expected ok)")

        local latency_ms
        latency_ms=$(python3 -c "print(int(float('$latency_s') * 1000))" 2>/dev/null || echo "0")
        if [ "$latency_ms" -gt "$LATENCY_WARN_MS" ] 2>/dev/null; then
            FAILURES+=("proxy /health latency ${latency_ms}ms exceeds ${LATENCY_WARN_MS}ms threshold")
        fi
    fi

    # 2. Models endpoint — confirm at least one model loaded
    local models_response
    http_code=$(curl -s -o /tmp/agent-smoke-models.json -w '%{http_code}' \
        --connect-timeout 5 --max-time 10 "$PROXY/v1/models" 2>/dev/null) || http_code="000"
    if [ "$http_code" != "200" ]; then
        FAILURES+=("proxy /v1/models returned HTTP $http_code")
    else
        local model_count
        model_count=$(python3 -c "import json,sys; d=json.load(open('/tmp/agent-smoke-models.json')); print(len(d.get('data',[])))" 2>/dev/null || echo "0")
        [ "$model_count" -eq 0 ] 2>/dev/null && FAILURES+=("proxy /v1/models returned 0 models")
    fi
}

tier2_checks() {
    # 3. Frank service state
    if ! systemctl --user is-active frank-api --quiet 2>/dev/null; then
        FAILURES+=("frank-api service is not active")
    fi

    # 4. Hermes service state
    if ! systemctl is-active hermes-gateway --quiet 2>/dev/null; then
        FAILURES+=("hermes-gateway service is not active")
    fi

    # 5. Hermes recent log errors (last 2 hours)
    local hermes_errors
    hermes_errors=$(journalctl -u hermes-gateway --since "2 hours ago" --no-pager -q 2>/dev/null \
        | grep -c "ERROR\|CRITICAL\|Traceback" 2>/dev/null || echo "0")
    if [ "$hermes_errors" -gt 10 ] 2>/dev/null; then
        FAILURES+=("hermes-gateway logged $hermes_errors errors in last 2 hours")
    fi

    # 6. Inference status file freshness (proves update-inference-status.py is running)
    if [ -f "$INFERENCE_STATUS_FILE" ]; then
        local file_age_s now_s file_mtime
        now_s=$(date +%s)
        file_mtime=$(stat -c '%Y' "$INFERENCE_STATUS_FILE" 2>/dev/null || echo "0")
        file_age_s=$(( now_s - file_mtime ))
        local stale_threshold=$(( INFERENCE_STALE_MINS * 60 ))
        if [ "$file_age_s" -gt "$stale_threshold" ] 2>/dev/null; then
            local age_mins=$(( file_age_s / 60 ))
            FAILURES+=("inference-status.json is ${age_mins}min old (threshold: ${INFERENCE_STALE_MINS}min) — cron may be down")
        fi
    else
        FAILURES+=("inference-status.json not found at $INFERENCE_STATUS_FILE")
    fi
}

main() {
    local mode="${1:-}"
    if [ -z "$mode" ] || [ "$mode" = "--tier1" ]; then
        tier1_checks
    elif [ "$mode" = "--tier2" ]; then
        tier1_checks
        tier2_checks
    else
        echo "Usage: agent-smoke.sh [--tier1|--tier2]" >&2
        exit 1
    fi

    if [ ${#FAILURES[@]} -gt 0 ]; then
        local msg
        msg=$(printf "• %s\n" "${FAILURES[@]}")
        slack_alert "$msg"
        exit 1
    fi

    exit 0
}

main "$@"
