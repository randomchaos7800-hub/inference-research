#!/usr/bin/env bash
# 2026-11-06 Groot survey, unattended: wait for downloads, speed pass, quality pass. Progress in raw/progress.log.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); cd "$HERE"; mkdir -p raw
P=raw/progress.log; log() { echo "$(date -Is) $*" >> $P; }
stop_server() { pkill -x llama-server 2>/dev/null; for i in $(seq 1 30); do pgrep -x llama-server >/dev/null || return 0; sleep 1; done; pkill -9 -x llama-server; sleep 2; }
log "waiting for downloads"
while pgrep -f "curl.*Groot" >/dev/null; do sleep 20; done
for f in /home/dino/models/GrootTeam_Groot-19B-A3B-261023-IQ4_NL.gguf /home/dino/models/GrootTeam_Groot-19B-A3B-261023-Q4_K_M.gguf; do
  [ "$(head -c4 "$f" 2>/dev/null)" = "GGUF" ] || { log "FAILED: $f is not a GGUF (download broken)"; exit 1; }
  log "model ok: $(basename "$f") $(stat -c %s "$f") bytes; mtp tensors: $(python3 ggufmeta.py "$f" 2>/dev/null | grep -ciE "nextn|mtp" || echo 0)"
done
sleep 60
systemctl --user stop llama-local 2>/dev/null; stop_server
log "START speed"
OUT=raw/speed.jsonl ./speedbench.sh && log "speed done" || log "speed exited nonzero"
log "START quality"
mapfile -t Qs < <(grep -v "^\s*#" quality.txt | grep -v "^\s*$")
for seed in 1 2; do
  for line in "${Qs[@]}"; do
    IFS="|" read -r label bin model flags <<< "$line"
    stop_server; sleep 20
    # shellcheck disable=SC2086
    nohup "$bin" --host 127.0.0.1 --port 8091 -m "$model" -ngl 99 -c 131072 -t 8 -fa on --jinja --no-warmup $flags > "raw/qserver-$label-s$seed.log" 2>&1 &
    up=0; for i in $(seq 1 120); do curl -sf -m 3 http://127.0.0.1:8091/health >/dev/null 2>&1 && { up=1; break; }; sleep 3; done
    if [ $up = 0 ]; then log "quality $label seed $seed NO BOOT: $(tail -3 raw/qserver-$label-s$seed.log | tr "\n" " ")"; continue; fi
    python3 harness.py --label "$label" --seed "$seed" --out raw/quality.jsonl >> raw/quality-console.log 2>&1
    log "quality $label seed $seed done"
  done
done
stop_server
log "ALL-DONE"
[ -x "$HOME/bin/tg-notify" ] && "$HOME/bin/tg-notify" "P14 Groot survey: all runs finished $(date +%H:%M). Claude judges next." >/dev/null 2>&1 || true
