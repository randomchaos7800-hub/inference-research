#!/usr/bin/env bash
# Does OpenMP absence cause the GPU-clock throttling?
# Two Vulkan binaries, SAME compiler (gcc 16.2), SAME CPU strategy (GGML_NATIVE=ON),
# SAME commit. The ONLY difference is GGML_OPENMP. This is the single-variable test
# the earlier "GCC vs Clang" comparison was not.
set -uo pipefail
SRC=$HOME/src/llama.cpp-hip
M=$HOME/models/mtp/Qwen3.6-35B-A3B-UD-IQ4_NL.gguf
OUT=$HOME/bench-openmp-$(date +%Y%m%d-%H%M).jsonl
D=/sys/class/drm/card1/device
HW=$(ls -d $D/hwmon/hwmon* 2>/dev/null | head -1)
cd "$SRC"

build() { # $1=dir $2=OPENMP on/off
  echo "=== building $1 (GGML_OPENMP=$2) ==="
  cmake -S . -B "$1" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DGGML_NATIVE=ON \
    -DGGML_OPENMP="$2" -DLLAMA_CURL=OFF \
    -DCMAKE_C_COMPILER=/usr/bin/gcc -DCMAKE_CXX_COMPILER=/usr/bin/g++ 2>&1 | grep -iE "OpenMP|Warning: OpenMP" | head -4
  cmake --build "$1" --target llama-server -j8 >/dev/null 2>&1 || { echo "BUILD FAILED: $1"; return 1; }
  local lib=$(ls "$1"/bin/libggml-cpu*.so 2>/dev/null | head -1)
  printf "  %s -> OpenMP linked: " "$1"
  ldd "$lib" 2>/dev/null | grep -qiE "libgomp|libomp" && echo YES || echo NO
}

build build-omp-on  ON  || exit 1
build build-omp-off OFF || exit 1

cell() {
  local label="$1" bin="$2"
  pkill -f "[l]lama-server" 2>/dev/null; sleep 4
  sleep 150
  nohup "$bin" --host 127.0.0.1 --port 8090 -m "$M" --alias local \
    -ngl 36 -c 65536 -t 8 -fa on --jinja --no-warmup > /tmp/omp-$label.log 2>&1 &
  local up=0
  for i in $(seq 1 80); do curl -sf -m 3 http://127.0.0.1:8090/health >/dev/null 2>&1 && { up=1; break; }; sleep 3; done
  [ $up = 0 ] && { echo "{\"cell\":\"$label\",\"error\":\"no boot\"}" >> $OUT; return 1; }
  for w in 1 2; do curl -s -m 300 http://127.0.0.1:8090/completion \
      -d '{"prompt":"Hello.","n_predict":32,"cache_prompt":false,"ignore_eos":true}' >/dev/null; done
  for r in $(seq 1 12); do
    local sclk=$(awk '/\*/{print $2}' $D/pp_dpm_sclk 2>/dev/null|head -1)
    local pw=$(cat $HW/power1_average 2>/dev/null||echo 0)
    curl -s -m 300 http://127.0.0.1:8090/completion \
      -d '{"prompt":"Write a short paragraph about memory bandwidth.","n_predict":128,"cache_prompt":false,"ignore_eos":true,"temperature":0,"seed":42}' \
    | python3 -c "
import sys,json;t=json.load(sys.stdin)['timings']
print(json.dumps({'cell':'$label','run':$r,'tg_tps':round(t['predicted_per_second'],2),
 'sclk':'$sclk','power_w':round($pw/1e6,1)}))" >> $OUT
  done
  pkill -f "[l]lama-server" 2>/dev/null; sleep 3
}
echo "# $(date -Is) OPENMP ISOLATION: gcc $(gcc -dumpversion), GGML_NATIVE=ON both, -ngl 36, commit $(git rev-parse --short HEAD)" >> $OUT
cell omp_on  "$SRC/build-omp-on/bin/llama-server"
cell omp_off "$SRC/build-omp-off/bin/llama-server"
echo DONE >> $OUT
