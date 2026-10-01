#!/usr/bin/env bash
# Why does ROCm decode decay 24% over five identical runs?
# Batch A: 5 runs. Restart server. Batch B: 5 runs.
#   B starts high  -> per-PROCESS state (allocator / fragmentation / cache)
#   B stays low    -> SYSTEM state (clocks, power budget, memory pressure)
# A sampler logs clocks/power/temp/memory the whole time.
set -uo pipefail
HIP=$HOME/src/llama.cpp-hip/build-hip/bin/llama-server
M=$HOME/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf
OUT=$HOME/diag-rocm-$(date +%Y%m%d-%H%M).jsonl
D=/sys/class/drm/card1/device
HW=$(ls -d $D/hwmon/hwmon* 2>/dev/null | head -1)

sample() {
  while true; do
    sclk=$(awk '/\*/{print $2}' $D/pp_dpm_sclk 2>/dev/null | head -1)
    busy=$(cat $D/gpu_busy_percent 2>/dev/null)
    vram=$(( $(cat $D/mem_info_vram_used 2>/dev/null || echo 0) / 1048576 ))
    gtt=$(( $(cat $D/mem_info_gtt_used 2>/dev/null || echo 0) / 1048576 ))
    temp=$(( $(cat $HW/temp1_input 2>/dev/null || echo 0) / 1000 ))
    pwr=$(cat $HW/power1_average 2>/dev/null || echo 0)
    cpu=$(( $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo 0) / 1000 ))
    avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
    echo "{\"t\":$(date +%s),\"sclk\":\"$sclk\",\"busy\":\"$busy\",\"vram_mb\":$vram,\"gtt_mb\":$gtt,\"temp_c\":$temp,\"power_uw\":$pwr,\"cpu_mhz\":$cpu,\"mem_avail_mb\":$avail}" >> $HOME/diag-sample.jsonl
    sleep 2
  done
}

boot() {
  pkill -f "[l]lama-server" 2>/dev/null; sleep 4
  nohup "$HIP" --host 127.0.0.1 --port 8090 -m "$M" --alias local \
    -ngl 36 -c 65536 -t 8 -fa on --jinja --no-warmup > /tmp/diag-srv.log 2>&1 &
  for i in $(seq 1 60); do curl -sf -m 3 http://127.0.0.1:8090/health >/dev/null 2>&1 && return 0; sleep 3; done
  return 1
}
batch() {
  local tag="$1"
  for r in 1 2 3 4 5; do
    local pid=$(pgrep -f "[l]lama-server" | head -1)
    local rss=$(awk '/VmRSS/{print int($2/1024)}' /proc/$pid/status 2>/dev/null)
    local sclk=$(awk '/\*/{print $2}' $D/pp_dpm_sclk 2>/dev/null | head -1)
    curl -s -m 300 http://127.0.0.1:8090/completion \
      -d '{"prompt":"Write a short paragraph about memory bandwidth.","n_predict":128,"cache_prompt":false,"ignore_eos":true}' \
    | python3 -c "
import sys,json;t=json.load(sys.stdin)['timings']
print(json.dumps({'batch':'$tag','run':$r,'tg_tps':round(t['predicted_per_second'],2),
 'pp_tps':round(t['prompt_per_second'],2),'rss_mb':'$rss','sclk_before':'$sclk'}))" >> $OUT
  done
}

rm -f $HOME/diag-sample.jsonl
sample & SPID=$!
boot || { echo '{"error":"no boot A"}' >> $OUT; kill $SPID; exit 1; }
echo "{\"note\":\"batch A, fresh process\"}" >> $OUT
batch A
echo "{\"note\":\"restarting server (same system state)\"}" >> $OUT
boot || { echo '{"error":"no boot B"}' >> $OUT; kill $SPID; exit 1; }
batch B
kill $SPID 2>/dev/null
pkill -f "[l]lama-server" 2>/dev/null
echo DONE >> $OUT
