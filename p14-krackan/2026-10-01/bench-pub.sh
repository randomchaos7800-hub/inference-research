#!/usr/bin/env bash
# Publication run. Three binaries so backend and compiler are separable:
#   rocm      HIP      | clang22 | commit 07fc586e3
#   vkclang   Vulkan   | clang22 | commit 07fc586e3   <- compiler control
#   vkgcc     Vulkan   | gcc11.4 | commit 07fc586e3   <- production binary
# Fixes applied from today's findings: cold start + idle before every cell so no
# cell monopolises the boost budget; 12 runs/cell with the boost window reported
# SEPARATELY from the sustained tail; interleaved repeated order, not blocked.
set -uo pipefail
ROCM=$HOME/src/llama.cpp-hip/build-hip/bin/llama-server
VKCLANG=$HOME/src/llama.cpp-hip/build-vk/bin/llama-server
VKGCC=$HOME/opt/llama.cpp/llama-server
M=$HOME/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf
OUT=$HOME/bench-pub-$(date +%Y%m%d-%H%M).jsonl
D=/sys/class/drm/card1/device
HW=$(ls -d $D/hwmon/hwmon* 2>/dev/null | head -1)
IDLE=${IDLE:-150}

sample() { while true; do
  echo "{\"t\":$(date +%s),\"sclk\":\"$(awk '/\*/{print $2}' $D/pp_dpm_sclk 2>/dev/null|head -1)\",\"busy\":\"$(cat $D/gpu_busy_percent 2>/dev/null)\",\"temp_c\":$(( $(cat $HW/temp1_input 2>/dev/null||echo 0)/1000 )),\"power_uw\":$(cat $HW/power1_average 2>/dev/null||echo 0),\"vram_mb\":$(( $(cat $D/mem_info_vram_used 2>/dev/null||echo 0)/1048576 )),\"gtt_mb\":$(( $(cat $D/mem_info_gtt_used 2>/dev/null||echo 0)/1048576 ))}" >> $HOME/pub-sample.jsonl
  sleep 2; done; }

quiet_check() { ps -eo pcpu,comm --sort=-pcpu | awk 'NR==2{print $1}'; }

cell() { # $1 label  $2 bin  $3 rep  rest flags
  local label="$1" bin="$2" rep="$3"; shift 3
  pkill -f "[l]lama-server" 2>/dev/null; sleep 4
  echo "  idle ${IDLE}s to recharge boost budget..."; sleep "$IDLE"
  nohup "$bin" --host 127.0.0.1 --port 8090 -m "$M" --alias local \
    -ngl 36 -c 65536 -t 8 -fa on --jinja --no-warmup "$@" > /tmp/pub-$label.log 2>&1 &
  local up=0
  for i in $(seq 1 80); do curl -sf -m 3 http://127.0.0.1:8090/health >/dev/null 2>&1 && { up=1; break; }; sleep 3; done
  if [ $up = 0 ]; then
    echo "{\"cell\":\"$label\",\"rep\":$rep,\"error\":\"no boot\",\"log\":\"$(grep -iE 'out of memory|error' /tmp/pub-$label.log|head -2|tr '\n' ' '|tr -d '\"')\"}" >> $OUT
    return 1
  fi
  # two warm-ups: page cache + first-token paths, never scored
  for w in 1 2; do curl -s -m 300 http://127.0.0.1:8090/completion \
      -d '{"prompt":"Hello.","n_predict":32,"cache_prompt":false,"ignore_eos":true}' >/dev/null; done
  for r in $(seq 1 12); do
    local sclk=$(awk '/\*/{print $2}' $D/pp_dpm_sclk 2>/dev/null|head -1)
    local pw=$(cat $HW/power1_average 2>/dev/null||echo 0)
    local tc=$(( $(cat $HW/temp1_input 2>/dev/null||echo 0)/1000 ))
    curl -s -m 300 http://127.0.0.1:8090/completion \
      -d '{"prompt":"Write a short paragraph about memory bandwidth.","n_predict":128,"cache_prompt":false,"ignore_eos":true}' \
    | python3 -c "
import sys,json;t=json.load(sys.stdin)['timings']
print(json.dumps({'cell':'$label','rep':$rep,'run':$r,'tg_tps':round(t['predicted_per_second'],2),
 'pp_tps':round(t['prompt_per_second'],2),'sclk':'$sclk','power_w':round($pw/1e6,1),'temp_c':$tc,
 'top_cpu':'$(quiet_check)'}))" >> $OUT
  done
  pkill -f "[l]lama-server" 2>/dev/null; sleep 3
}

rm -f $HOME/pub-sample.jsonl
sample & SPID=$!
echo "# $(date -Is) PUBLICATION RUN -ngl 36/40 fence=16GiB commit=07fc586e3 idle=${IDLE}s runs=12" >> $OUT
for rep in 1 2; do
  echo "== repetition $rep =="
  cell rocm_mtp_off    "$ROCM"    $rep
  cell vkclang_mtp_off "$VKCLANG" $rep
  cell vkgcc_mtp_off   "$VKGCC"   $rep
  cell rocm_mtp_on     "$ROCM"    $rep --spec-type draft-mtp --spec-draft-n-max 2
  cell vkgcc_mtp_on    "$VKGCC"   $rep --spec-type draft-mtp --spec-draft-n-max 2
done
kill $SPID 2>/dev/null; pkill -f "[l]lama-server" 2>/dev/null
echo DONE >> $OUT
