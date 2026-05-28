#!/bin/bash
# Daily inference performance logger
# Benchmarks tower proxy (100.120.50.35:8010), logs JSON + TSV.
# Fails loudly if proxy is unreachable — no local fallback.
# Log dir: ~/logs/perf/
# TSV summary: ~/logs/perf/perf.tsv
# JSON detail: ~/logs/perf/YYYY-MM-DD-<hostname>.json

set -euo pipefail

REAL_HOME="${REAL_HOME:-${DINO_HOME:-/home/dino}}"
LOG_DIR="$REAL_HOME/logs/perf"
DATE=$(date +%Y-%m-%d)
HOST=$(hostname)
JSON_LOG="$LOG_DIR/${DATE}-${HOST}.json"
TSV_LOG="$LOG_DIR/perf.tsv"
SERVER_URL="http://100.120.50.35:8010"
MODEL_ALIAS="local"

mkdir -p "$LOG_DIR"

# ── System info ────────────────────────────────────────────────────────────────
CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
CPU_CORES=$(nproc)
RAM_TOTAL_GIB=$(awk '/MemTotal/{printf "%.1f", $2/1048576}' /proc/meminfo)
ARCH=$(uname -m)
KERNEL=$(uname -r | cut -d- -f1)

# ── Proxy health check ────────────────────────────────────────────────────────
if ! curl -s "$SERVER_URL/health" 2>/dev/null | grep -q "ok"; then
    echo "ERROR: tower proxy $SERVER_URL unreachable — skipping benchmark" >&2
    exit 1
fi

MODEL_NAME=$(curl -s "$SERVER_URL/v1/models" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0]['id'])" 2>/dev/null || echo "$MODEL_ALIAS")

# ── Benchmark: TTFT + generation speed ────────────────────────────────────────
run_inference() {
    local prompt="$1"
    local max_tokens="$2"
    python3 - "$SERVER_URL" "$MODEL_ALIAS" "$prompt" "$max_tokens" <<'PYEOF'
import sys, json, time, urllib.request

url = sys.argv[1] + "/v1/chat/completions"
model = sys.argv[2]
prompt = sys.argv[3]
max_tokens = int(sys.argv[4])

payload = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": max_tokens,
    "stream": True,
}).encode()

req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
start = time.time()
first_token_t = None
tokens = 0

with urllib.request.urlopen(req, timeout=120) as resp:
    for line in resp:
        line = line.decode().strip()
        if line.startswith("data: ") and line != "data: [DONE]":
            chunk = json.loads(line[6:])
            if not chunk.get("choices"):
                continue
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                if first_token_t is None:
                    first_token_t = time.time()
                tokens += 1

end = time.time()
ttft_ms = round((first_token_t - start) * 1000) if first_token_t else -1
gen_tps = round(tokens / (end - first_token_t), 2) if first_token_t and tokens > 1 else 0
pp_tps = round(len(prompt.split()) / (first_token_t - start), 2) if first_token_t else 0

print(json.dumps({"ttft_ms": ttft_ms, "gen_tps": gen_tps, "pp_tps": pp_tps, "tokens": tokens}))
PYEOF
}

# Short prompt (fast path)
SHORT=$(run_inference "What is 2+2?" 30)
# Medium prompt (typical use)
MEDIUM=$(run_inference "Explain transformer attention in 3 sentences." 150)

TTFT_MS=$(echo "$SHORT" | python3 -c "import json,sys; print(json.load(sys.stdin)['ttft_ms'])")
GEN_TPS=$(echo "$MEDIUM" | python3 -c "import json,sys; print(json.load(sys.stdin)['gen_tps'])")
PP_TPS=$(echo "$MEDIUM" | python3 -c "import json,sys; print(json.load(sys.stdin)['pp_tps'])")
GEN_TOKENS=$(echo "$MEDIUM" | python3 -c "import json,sys; print(json.load(sys.stdin)['tokens'])")

# ── Load average ───────────────────────────────────────────────────────────────
LOAD_AVG=$(cat /proc/loadavg | awk '{print $1"/"$2"/"$3}')
SWAP_USED_GIB=$(free | awk '/Swap/{printf "%.1f", $3/1048576}')
MEM_AVAILABLE_GIB=$(awk '/MemAvailable/{printf "%.1f", $2/1048576}' /proc/meminfo)

# ── Write JSON ─────────────────────────────────────────────────────────────────
python3 - <<PYEOF
import json
data = {
    "date": "$DATE",
    "host": "$HOST",
    "arch": "$ARCH",
    "kernel": "$KERNEL",
    "cpu": "$CPU_MODEL",
    "cpu_cores": $CPU_CORES,
    "ram_total_gib": $RAM_TOTAL_GIB,
    "model": "$MODEL_NAME",
    "ttft_ms": $TTFT_MS,
    "gen_tps": $GEN_TPS,
    "pp_tps": $PP_TPS,
    "gen_tokens": $GEN_TOKENS,
    "swap_used_gib": $SWAP_USED_GIB,
    "mem_available_gib": $MEM_AVAILABLE_GIB,
    "load_avg_1_5_15": "$LOAD_AVG",
}
with open("$JSON_LOG", "w") as f:
    json.dump(data, f, indent=2)
print("JSON written:", "$JSON_LOG")
PYEOF

# ── Append TSV ─────────────────────────────────────────────────────────────────
if [ ! -f "$TSV_LOG" ]; then
    echo -e "date\thost\tcpu\tmodel\tttft_ms\tgen_tps\tpp_tps\tswap_used_gib\tmem_avail_gib" > "$TSV_LOG"
fi
echo -e "${DATE}\t${HOST}\t${CPU_MODEL}\t${MODEL_NAME}\t${TTFT_MS}\t${GEN_TPS}\t${PP_TPS}\t${SWAP_USED_GIB}\t${MEM_AVAILABLE_GIB}" >> "$TSV_LOG"
echo "TSV appended: $TSV_LOG"

echo "Done: gen=${GEN_TPS}t/s ttft=${TTFT_MS}ms model=${MODEL_NAME}"
