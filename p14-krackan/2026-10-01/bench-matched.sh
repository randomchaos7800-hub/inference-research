#!/usr/bin/env bash
# ROCm cannot hold this model at a 16 GiB carve-out (VRAM is a hard ceiling for
# HIP; RADV spills to GTT). So: find the largest -ngl ROCm CAN take, then run
# BOTH backends at that same -ngl. Partial offload, but a true single-variable
# backend comparison.
set -uo pipefail
HIP=$HOME/src/llama.cpp-hip/build-hip/bin/llama-server
VK=$HOME/opt/llama.cpp/llama-server
M=$HOME/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf
OUT=$HOME/bench-matched-$(date +%Y%m%d).jsonl
python3 -c "
import json
p=('The quick brown fox jumps over the lazy dog. '*520)
json.dump({'prompt':p,'n_predict':128,'cache_prompt':False,'ignore_eos':True},open('/tmp/big2.json','w'))"

boot() { # $1=bin  $2=ngl  rest=flags ; returns 0 if server came up
  pkill -f "[l]lama-server" 2>/dev/null; sleep 3
  local bin="$1" ngl="$2"; shift 2
  nohup "$bin" --host 127.0.0.1 --port 8090 -m "$M" --alias local \
    -ngl "$ngl" -c 65536 -t 8 -fa on --jinja --no-warmup "$@" > /tmp/mb.log 2>&1 &
  for i in $(seq 1 60); do curl -sf -m 3 http://127.0.0.1:8090/health >/dev/null 2>&1 && return 0; sleep 3; done
  return 1
}

NGL=0
for n in 38 36 34 32 30 28; do
  echo "probing rocm -ngl $n ..."
  if boot "$HIP" "$n"; then NGL=$n; echo "rocm fits at -ngl $n"; break; fi
done
pkill -f "[l]lama-server" 2>/dev/null; sleep 3
if [ "$NGL" = 0 ]; then echo '{"error":"rocm could not load at any tested -ngl"}' >> $OUT; echo DONE >> $OUT; exit 1; fi
echo "# $(date -Is) MATCHED -ngl=$NGL carve-out=16GiB kernel=$(uname -r)" >> $OUT

cell() { # $1=name $2=bin  rest=flags
  local name="$1" bin="$2"; shift 2
  boot "$bin" "$NGL" "$@" || { echo "{\"cell\":\"$name\",\"error\":\"no boot\"}" >> $OUT; return 1; }
  curl -s -m 180 http://127.0.0.1:8090/completion -d '{"prompt":"Hello.","n_predict":16,"cache_prompt":false}' >/dev/null
  for r in 1 2 3 4 5; do
    curl -s -m 300 http://127.0.0.1:8090/completion \
      -d '{"prompt":"Write a short paragraph about memory bandwidth.","n_predict":128,"cache_prompt":false,"ignore_eos":true}' \
    | python3 -c "
import sys,json;t=json.load(sys.stdin)['timings']
print(json.dumps({'cell':'$name','ngl':$NGL,'kind':'clean','run':$r,'tg_tps':round(t['predicted_per_second'],2),
 'pp_tps':round(t['prompt_per_second'],2),'n_pred':t['predicted_n']}))" >> $OUT
  done
  for r in 1 2 3; do
    curl -s -m 600 http://127.0.0.1:8090/completion -d @/tmp/big2.json \
    | python3 -c "
import sys,json;t=json.load(sys.stdin)['timings']
print(json.dumps({'cell':'$name','ngl':$NGL,'kind':'loaded','run':$r,'tg_tps':round(t['predicted_per_second'],2),
 'pp_tps':round(t['prompt_per_second'],2),'n_pred':t['predicted_n']}))" >> $OUT
  done
  pkill -f "[l]lama-server" 2>/dev/null; sleep 3
}

cell rocm_mtp_off   "$HIP"
cell vulkan_mtp_off "$VK"
cell rocm_mtp_on    "$HIP" --spec-type draft-mtp --spec-draft-n-max 2
cell vulkan_mtp_on  "$VK"  --spec-type draft-mtp --spec-draft-n-max 2
echo DONE >> $OUT
