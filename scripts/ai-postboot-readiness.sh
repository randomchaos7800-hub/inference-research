#!/usr/bin/env bash

set -euo pipefail

REAL_HOME="${REAL_HOME:-${DINO_HOME:-/home/dino}}"
SMOKE="$REAL_HOME/scripts/agent-smoke.sh"
LOG_TAG="ai-postboot-readiness"
RECOVERY_WAIT_SECS=20
SERVICES=(
  harness-api.service
  harness.service
  mike.service
  mike-irc.service
  mike-irchighway.service
  autoresearch.service
)

log() {
    logger -t "$LOG_TAG" "$1"
    echo "$1"
}

recover_services() {
    local restarted=0
    for svc in "${SERVICES[@]}"; do
        if ! systemctl --user is-active "$svc" --quiet; then
            log "recovering $svc"
            systemctl --user reset-failed "$svc" || true
            systemctl --user restart "$svc" || true
            restarted=1
        fi
    done
    return "$restarted"
}

main() {
    if "$SMOKE" --tier2 --no-alert; then
        log "tier2 smoke check passed on first attempt"
        exit 0
    fi

    log "initial tier2 smoke check failed; attempting service recovery"
    recover_services || true
    sleep "$RECOVERY_WAIT_SECS"

    if "$SMOKE" --tier2 --no-alert; then
        log "tier2 smoke check passed after recovery"
        exit 0
    fi

    log "tier2 smoke check still failing after recovery"
    exec "$SMOKE" --tier2
}

main "$@"
