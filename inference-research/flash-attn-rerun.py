#!/usr/bin/env python3
"""
flash-attn-rerun.py — single experiment: --flash-attn on
Re-run after fixing bare flag bug in autoresearch-nemotron.py
"""

import json, os, re, signal, statistics, subprocess, time
from datetime import datetime

MODEL_PATH   = "/home/dino/models/Nemotron-3-Nano-30B-A3B/nvidia_Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf"
LLAMA_SERVER = "/home/dino/llama.cpp/build-cuda128-clean/bin/llama-server"
LD_LIB       = "/home/dino/llama.cpp/build-cuda128-clean/bin"
SERVER_LOG   = "/tmp/flash-attn-serve.log"
LOG_FILE     = "/home/dino/inference-research/flash-attn-rerun.log"

PORT    = 8022
URL     = f"http://localhost:{PORT}/v1/chat/completions"
HEALTH  = f"http://localhost:{PORT}/health"
HEADERS = {"Content-Type": "application/json"}

N_WARMUP = 3
N_BENCH  = 8
BENCH_TOKENS = 400
BASELINE = 123.6

PROMPTS = [
    "Explain in technical detail how CUDA tensor cores accelerate matrix multiplication on Blackwell GPU architecture.",
    "Describe the engineering challenges of running large language model inference at scale.",
    "Explain how retrieval augmented generation works end to end.",
    "Describe how speculative decoding accelerates autoregressive inference.",
    "Explain CUDA memory management for deep learning workloads.",
    "Describe prefix caching in LLM inference servers.",
    "Explain the Mamba state space model architecture.",
    "Describe multi-GPU tensor parallelism for LLM inference.",
]

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def kill_server():
    subprocess.run(["pkill", "-9", "-f", "llama-server"], capture_output=True)
    time.sleep(2)

def gpu_free():
    r = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True)
    return [int(x.strip()) for x in r.stdout.strip().splitlines() if x.strip()]

def wait_clean(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        free = gpu_free()
        if all(f >= 14000 for f in free):
            log(f"  VRAM clean: {free} MiB free")
            return True
        time.sleep(3)
    log(f"  WARNING: VRAM not clean: {gpu_free()}")
    return False

def wait_ready(timeout=120):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH, timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False

def bench_one(prompt):
    import urllib.request
    payload = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": BENCH_TOKENS,
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
        return resp.get("timings", {}).get("predicted_per_second", 0)
    except Exception as e:
        log(f"    error: {e}")
        return None

def main():
    open(LOG_FILE, "w").close()
    log(f"flash-attn-rerun start — {datetime.now().isoformat()}")

    kill_server()
    wait_clean()

    cmd = [
        LLAMA_SERVER,
        "--model", MODEL_PATH,
        "--host", "0.0.0.0", "--port", str(PORT),
        "--n-gpu-layers", "999",
        "--ctx-size", "32768",
        "--threads", "8",
        "--cache-ram", "0",
        "--flash-attn", "on",
    ]
    log(f"  cmd: ... --flash-attn on")

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = LD_LIB
    fh = open(SERVER_LOG, "w")
    proc = subprocess.Popen(cmd, env=env, stdout=fh, stderr=fh)

    if not wait_ready():
        log("  FAIL: server did not come up — flash-attn not supported on this build/model")
        try:
            with open(SERVER_LOG) as f:
                for line in f.readlines()[-5:]:
                    log(f"  SERVER: {line.rstrip()}")
        except Exception:
            pass
        proc.terminate()
        fh.close()
        return

    log("  server ready — warmup...")
    for i in range(N_WARMUP):
        tps = bench_one(PROMPTS[i])
        log(f"    warmup {i+1}: {tps:.1f} t/s" if tps else f"    warmup {i+1}: FAIL")

    log(f"  bench ({N_BENCH} runs)...")
    readings = []
    for i in range(N_BENCH):
        tps = bench_one(PROMPTS[i])
        if tps:
            readings.append(tps)
            log(f"    run {i+1}: {tps:.1f} t/s")
        else:
            log(f"    run {i+1}: FAIL")

    proc.terminate()
    fh.close()

    if not readings:
        log("  ALL RUNS FAILED")
        return

    med    = statistics.median(readings)
    stddev = statistics.stdev(readings) if len(readings) > 1 else 0.0
    delta  = med - BASELINE
    sign   = "+" if delta >= 0 else ""
    log(f"\n  RESULT: median={med:.1f}  stddev={stddev:.2f}  delta={sign}{delta:.1f} vs baseline")
    log(f"  flash-attn on: {'WIN' if delta > 1.0 else 'NO GAIN' if delta > -1.0 else 'SLOWER'}")
    log(f"\nflash-attn-rerun complete")

if __name__ == "__main__":
    main()
