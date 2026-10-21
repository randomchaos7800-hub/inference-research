#!/usr/bin/env bash
# Whole survey, unattended: speed pass (speedbench.sh over cells.txt), then quality pass
# (harness.py over quality.txt, two seeds). Progress + sentinels in raw/progress.log.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); cd "$HERE"; mkdir -p raw
P=raw/progress.log
log() { echo "$(date -Is) $*" >> $P; }
stop_server() { pkill -x llama-server 2>/dev/null; for i in $(seq 1 30); do pgrep -x llama-server >/dev/null || return 0; sleep 1; done; pkill -9 -x llama-server; sleep 2; }

until grep -qE "ALL-DONE|FAILED" ~/models/survey/fetch.log; do sleep 20; done
grep -q FAILED ~/models/survey/fetch.log && log "WARNING: a download failed: $(grep FAILED ~/models/survey/fetch.log)"
sleep 60   # let the last download's page-cache writeback settle
# never benchmark against the production unit or the offline agent
systemctl --user stop llama-local 2>/dev/null; stop_server
log "START speed"
OUT=raw/speed.jsonl ./speedbench.sh && log "speed done" || log "speed exited nonzero"

log "START quality"
mapfile -t Q < <(grep -v '^\s*#' quality.txt | grep -v '^\s*$')
for seed in 1 2; do
  for line in "${Q[@]}"; do
    IFS='|' read -r label bin model flags <<< "$line"
    stop_server; sleep 20
    # shellcheck disable=SC2086
    nohup "$bin" --host 127.0.0.1 --port 8091 -m "$model" -ngl 99 -c 131072 -t 8 -fa on --jinja --no-warmup $flags \
      > "raw/qserver-$label-s$seed.log" 2>&1 &
    up=0; for i in $(seq 1 120); do curl -sf -m 3 http://127.0.0.1:8091/health >/dev/null 2>&1 && { up=1; break; }; sleep 3; done
    if [ $up = 0 ]; then log "quality $label seed $seed NO BOOT: $(tail -3 raw/qserver-$label-s$seed.log | tr '\n' ' ')"; continue; fi
    python3 harness.py --label "$label" --seed "$seed" --out raw/quality.jsonl >> raw/quality-console.log 2>&1
    log "quality $label seed $seed done"
  done
done
stop_server
log "ALL-DONE"
