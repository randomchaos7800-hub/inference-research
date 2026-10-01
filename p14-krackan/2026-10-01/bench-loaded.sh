#!/usr/bin/env bash
# Closes the gap in the publication run: valid PREFILL (~5.2k-token prompt) and
# LOADED-CONTEXT decode, across all three binaries. Same protocol as bench-pub:
# clean box, 150s idle per cell, interleaved repetitions, sustained tail reported
# separately. rocm_mtp is omitted — already documented as no-boot twice under the
# clean protocol; a third failure adds nothing and costs 8 minutes of timeouts.
set -uo pipefail
ROCM=$HOME/src/llama.cpp-hip/build-hip/bin/llama-server
VKCLANG=$HOME/src/llama.cpp-hip/build-vk/bin/llama-server
VKGCC=$HOME/opt/llama.cpp/llama-server
M=$HOME/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf
OUT=$HOME/bench-loaded-$(date +%Y%m%d-%H%M).jsonl
D=/sys/class/drm/card1/device
HW=$(ls -d $D/hwmon/hwmon* 2>/dev/null | head -1)
IDLE=${IDLE:-150}
RUNS=${RUNS:-8}

# identical prompt to the matched run (5201 tokens) so figures are comparable
python3 -c "
import json
p=('The quick brown fox jumps over the lazy dog. '*520)
json.dump({'prompt':p,'n_predict':128,'cache_prompt':False,'ignore_eos':True},open('/tmp/long.json','w'))"

cell() { # $1 label $2 bin $3 rep  rest flags
  local label="$1" bin="$2" rep="$3"; shift 3
  pkill -f "[l]lama-server" 2>/dev/null; sleep 4
  sleep "$IDLE"
  nohup "$bin" --host 127.0.0.1 --port 8090 -m "$M" --alias local \
    -ngl 36 -c 65536 -t 8 -fa on --jinja --no-warmup "$@" > /tmp/ld-$label.log 2>&1 &
  local up=0
  for i in $(seq 1 80); do curl -sf -m 3 http://127.0.0.1:8090/health >/dev/null 2>&1 && { up=1; break; }; sleep 3; done
  [ $up = 0 ] && { echo "{\"cell\":\"$label\",\"rep\":$rep,\"error\":\"no boot\"}" >> $OUT; return 1; }
  for w in 1 2; do curl -s -m 300 http://127.0.0.1:8090/completion \
      -d '{"prompt":"Hello.","n_predict":32,"cache_prompt":false,"ignore_eos":true}' >/dev/null; done
  for r in $(seq 1 $RUNS); do
    local sclk=$(awk '/\*/{print $2}' $D/pp_dpm_sclk 2>/dev/null|head -1)
    local pw=$(cat $HW/power1_average 2>/dev/null||echo 0)
    local tc=$(( $(cat $HW/temp1_input 2>/dev/null||echo 0)/1000 ))
    curl -s -m 600 http://127.0.0.1:8090/completion -d @/tmp/long.json \
    | python3 -c "
import sys,json
t=json.load(sys.stdin)['timings']
print(json.dumps({'cell':'$label','rep':$rep,'run':$r,
 'pp_tps':round(t['prompt_per_second'],2),'tg_tps':round(t['predicted_per_second'],2),
 'n_prompt':t['prompt_n'],'n_pred':t['predicted_n'],
 'sclk':'$sclk','power_w':round($pw/1e6,1),'temp_c':$tc}))" >> $OUT
  done
  pkill -f "[l]lama-server" 2>/dev/null; sleep 3
}

echo "# $(date -Is) LOADED/PREFILL pass, prompt=5201 tok, -ngl 36, fence=16GiB, commit 07fc586e3, runs=$RUNS idle=${IDLE}s" >> $OUT
for rep in 1 2; do
  cell rocm_mtp_off    "$ROCM"    $rep
  cell vkclang_mtp_off "$VKCLANG" $rep
  cell vkgcc_mtp_off   "$VKGCC"   $rep
  cell vkgcc_mtp_on    "$VKGCC"   $rep --spec-type draft-mtp --spec-draft-n-max 2
done
pkill -f "[l]lama-server" 2>/dev/null
echo DONE >> $OUT
