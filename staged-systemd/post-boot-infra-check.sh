#!/usr/bin/env bash

set -euo pipefail

READY_FILE=/run/post-boot-infra.ready
TAILSCALE_IP=100.94.10.36
SERVICES=(ssh.service forgejo.service)
PORTS=(22 3002)

log() {
    logger -t post-boot-infra "$1"
    echo "$1"
}

wait_for_tailscale_ip() {
    for _ in $(seq 1 60); do
        if ip -4 addr show dev tailscale0 2>/dev/null | grep -q "${TAILSCALE_IP}/32"; then
            return 0
        fi
        sleep 1
    done
    return 1
}

check_port() {
    local port="$1"
    ss -ltn | grep -q " ${TAILSCALE_IP}:${port} "
}

rm -f "$READY_FILE"

if ! wait_for_tailscale_ip; then
    log "tailscale0 did not acquire ${TAILSCALE_IP}/32 within timeout"
    exit 1
fi

for svc in "${SERVICES[@]}"; do
    if ! systemctl is-active "$svc" --quiet; then
        log "restarting $svc"
        systemctl reset-failed "$svc" || true
        systemctl restart "$svc"
    fi
done

for port in "${PORTS[@]}"; do
    for _ in $(seq 1 30); do
        if check_port "$port"; then
            break
        fi
        sleep 1
    done
    if ! check_port "$port"; then
        log "tailscale listener ${TAILSCALE_IP}:${port} not ready"
        exit 1
    fi
done

touch "$READY_FILE"
log "critical tailscale-bound infra ready"
