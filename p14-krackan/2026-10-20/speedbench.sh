#!/usr/bin/env bash
# MoE survey speed pass, cha0tikp14, 2026-10-20. Protocol: ../../BENCHMARK-PROTOCOL.md
#   cells.txt lines:  label|binary|model|extra server flags
# Per cell: 150 s idle, boot, 2 unscored warm-ups, then
#   clean    short prompt, 128 tok, RUNS_CLEAN runs
#   loaded   ~5k-token prompt, 128 tok, RUNS_LOADED runs   (prefill + loaded decode)
#   deep     ~32k-token prompt, 128 tok, RUNS_DEEP runs    (long-context decode)
# Two repetitions, rep 2 in reverse order. ignore_eos on; n_pred asserted. Telemetry per run.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
CELLS=${CELLS:-$HERE/cells.txt}
OUT=${OUT:-$HERE/raw/speed-$(date +%Y%m%d-%H%M).jsonl}
IDLE=${IDLE:-150}; RUNS_CLEAN=${RUNS_CLEAN:-8}; RUNS_LOADED=${RUNS_LOADED:-6}; RUNS_DEEP=${RUNS_DEEP:-3}
PORT=8091; D=/sys/class/drm/card1/device; HW=$(ls -d $D/hwmon/hwmon* | head -1)
mkdir -p "$HERE/raw"

python3 "$HERE/mkprompts.py" "$HERE"   # writes /tmp/sb-{clean,loaded,deep}.json (natural text, not a repeated sentence)

telemetry() {
  local sclk pw tc top
  sclk=$(awk '/\*/{print $2}' $D/pp_dpm_sclk | head -1)
  pw=$(cat $HW/power1_average 2>/dev/null || echo 0)
  tc=$(( $(cat $HW/temp1_input 2>/dev/null || echo 0) / 1000 ))
  top=$(ps -eo pcpu,comm --sort=-pcpu | awk 'NR>1 && $2!="llama-server"{print $2":"$1; exit}')
  echo "\"sclk\":\"$sclk\",\"power_w\":$(python3 -c "print(round($pw/1e6,1))"),\"temp_c\":$tc,\"top_other\":\"$top\""
}

stop_server() { pkill -x llama-server 2>/dev/null; for i in $(seq 1 30); do pgrep -x llama-server >/dev/null || return 0; sleep 1; done; pkill -9 -x llama-server; sleep 2; }

measure() { # label rep phase file runs expected_pred
  local label=$1 rep=$2 phase=$3 file=$4 runs=$5
  for r in $(seq 1 "$runs"); do
    local tel; tel=$(telemetry)
    curl -s -m 1800 http://127.0.0.1:$PORT/completion -d @"$file" > /tmp/sb-resp.json
    python3 - "$label" "$rep" "$phase" "$r" "$tel" >> "$OUT" <<'PY'
import json,sys
label,rep,phase,r,tel=sys.argv[1:6]
try:
    t=json.load(open('/tmp/sb-resp.json'))['timings']
    d={'cell':label,'rep':int(rep),'phase':phase,'run':int(r),
       'pp_tps':round(t['prompt_per_second'],2),'tg_tps':round(t['predicted_per_second'],2),
       'n_prompt':t['prompt_n'],'n_pred':t['predicted_n'],
       'draft_n':t.get('draft_n'),'draft_accepted':t.get('draft_n_accepted')}
    d['valid']= d['n_pred']==128
except Exception as e:
    d={'cell':label,'rep':int(rep),'phase':phase,'run':int(r),'error':str(e)[:200],'valid':False}
d.update(json.loads('{'+tel+'}'))
print(json.dumps(d))
PY
  done
}

cell() { # rep label bin model flags...
  local rep=$1 label=$2 bin=$3 model=$4; shift 4
  stop_server; sync; sleep "$IDLE"
  nohup "$bin" --host 127.0.0.1 --port $PORT -m "$model" -ngl 99 -c 65536 -t 8 -fa on --jinja --no-warmup "$@" \
    > "$HERE/raw/server-$label-rep$rep.log" 2>&1 &
  local up=0
  for i in $(seq 1 120); do curl -sf -m 3 http://127.0.0.1:$PORT/health >/dev/null 2>&1 && { up=1; break; }; sleep 3; done
  if [ $up = 0 ]; then
    echo "{\"cell\":\"$label\",\"rep\":$rep,\"error\":\"no boot\",\"log_tail\":$(tail -5 "$HERE/raw/server-$label-rep$rep.log" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')}" >> "$OUT"
    stop_server; return 1
  fi
  for w in 1 2; do curl -s -m 600 http://127.0.0.1:$PORT/completion -d @/tmp/sb-clean.json >/dev/null; done
  measure "$label" "$rep" clean  /tmp/sb-clean.json  "$RUNS_CLEAN"
  measure "$label" "$rep" loaded /tmp/sb-loaded.json "$RUNS_LOADED"
  measure "$label" "$rep" deep   /tmp/sb-deep.json   "$RUNS_DEEP"
  stop_server
}

echo "# $(date -Is) speed pass: -ngl 99 -c 65536 -t 8 -fa on, UMA 16 GiB, kernel $(uname -r), governor $(powerprofilesctl get), AC $(cat /sys/class/power_supply/AC*/online), idle ${IDLE}s, runs ${RUNS_CLEAN}/${RUNS_LOADED}/${RUNS_DEEP}" >> "$OUT"
mapfile -t LINES < <(grep -v '^\s*#' "$CELLS" | grep -v '^\s*$')
for rep in 1 2; do
  if [ $rep = 1 ]; then order=$(seq 0 $((${#LINES[@]}-1))); else order=$(seq $((${#LINES[@]}-1)) -1 0); fi
  for i in $order; do
    IFS='|' read -r label bin model flags <<< "${LINES[$i]}"
    # shellcheck disable=SC2086
    cell "$rep" "$label" "$bin" "$model" $flags
  done
done
stop_server
echo "SPEED-DONE $(date -Is)" >> "$OUT"
