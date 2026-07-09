#!/usr/bin/env python3
"""
autoresearch-nemotron.py — Nemotron 3 Nano 30B Q4_K_M parameter sweep
Hardware: dual RTX 5060 Ti 16GB, Intel Core Ultra 7 265F (20c), llama.cpp b9245

Baseline: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --cache-ram 0 → ~123 t/s

Optimize for 3 axes:
  SPEED   — maximize tokens/second
  CONTEXT — maximum ctx-size that fits in VRAM without OOM
  STABILITY — low variance, no crashes (track stddev across bench runs)

Groups:
  A: Threads       — find optimal CPU thread count (20-core box)
  B: KV quant      — q8/q4 KV cache to free VRAM, check speed impact
  C: Context size  — push ctx up with KV quant headroom
  D: Batch/ubatch  — ubatch tuning
  E: Flash attn    — --flash-attn (Nemotron has attention layers in hybrid)
  F: Combos        — winners from A-E combined

Results: /home/dino/inference-research/autoresearch-nemotron-results.tsv
Log:     /home/dino/inference-research/autoresearch-nemotron-log.md
"""

import json, os, re, signal, statistics, subprocess, sys, time
from datetime import datetime
from pathlib import Path

# ── config ────────────────────────────────────────────────────────────────────

MODEL_PATH   = "/home/dino/models/Nemotron-3-Nano-30B-A3B/nvidia_Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf"
LLAMA_SERVER = "/home/dino/llama.cpp/build-cuda128-clean/bin/llama-server"
LD_LIB       = "/home/dino/llama.cpp/build-cuda128-clean/bin"
SERVER_LOG   = "/tmp/nemotron-ar-serve.log"
RESULTS_TSV  = Path("/home/dino/inference-research/autoresearch-nemotron-results.tsv")
LOG_MD       = Path("/home/dino/inference-research/autoresearch-nemotron-log.md")
WINNER_SH    = Path("/home/dino/inference-research/nemotron-winner-start.sh")

PORT         = 8022
URL          = f"http://localhost:{PORT}/v1/chat/completions"
HEALTH       = f"http://localhost:{PORT}/health"
HEADERS      = {"Content-Type": "application/json"}

BENCH_TOKENS      = 400   # long enough for stable t/s reading
N_WARMUP          = 3
N_BENCH           = 8     # more runs = better stddev signal
READY_TIMEOUT     = 120
CLEAN_VRAM_MIB    = 1200  # free threshold per GPU to call it clean
GPU_DRAIN_TIMEOUT = 60
STABILITY_STDDEV_THRESH = 3.0  # t/s stddev above this = unstable

BASELINE_FLAGS = {
    "--n-gpu-layers": "999",
    "--ctx-size":     "32768",
    "--threads":      "8",
    "--cache-ram":    "0",
}

PROMPTS = [
    "Explain in technical detail how CUDA tensor cores accelerate matrix multiplication on Blackwell GPU architecture. Cover hardware pipeline, precision handling, and memory implications.",
    "Describe the engineering challenges of running large language model inference at scale, covering batching strategies, KV cache management, and quantization approaches.",
    "Explain how retrieval augmented generation works, covering embedding models, vector databases, chunking strategies, hybrid search, and reranking for grounded generation.",
    "Describe how speculative decoding accelerates autoregressive inference, covering draft models, token verification, acceptance rates, and multi-token prediction approaches.",
    "Explain CUDA memory management for deep learning: cudaMalloc, memory pools, VRAM fragmentation, unified memory, and best practices for multi-GPU inference workloads.",
    "Describe prefix caching in LLM inference servers: KV cache reuse, hash-based lookup, eviction policies, and throughput impact on production workloads.",
    "Explain the Mamba state space model architecture, selective state spaces, input-dependent transitions, parallel scan, and how SSMs compare to attention for long context.",
    "Describe multi-GPU tensor parallelism for LLM inference: how weight sharding works, all-reduce communication patterns, and latency-throughput tradeoffs.",
]

EXPERIMENTS = [
    # ── A: Threads ────────────────────────────────────────────────────────────
    {
        "id": "baseline",
        "label": "baseline — threads=8, ctx=32K, f16 KV (current production)",
        "flags": {},
        "axes": ["speed", "stability"],
    },
    {
        "id": "threads_12",
        "label": "threads=12",
        "flags": {"--threads": "12"},
        "axes": ["speed"],
    },
    {
        "id": "threads_16",
        "label": "threads=16",
        "flags": {"--threads": "16"},
        "axes": ["speed"],
    },
    {
        "id": "threads_20",
        "label": "threads=20 (max, full CPU)",
        "flags": {"--threads": "20"},
        "axes": ["speed"],
    },
    # ── B: KV quant ───────────────────────────────────────────────────────────
    {
        "id": "kv_q8",
        "label": "KV cache q8_0 — halves KV VRAM",
        "flags": {"--cache-type-k": "q8_0", "--cache-type-v": "q8_0"},
        "axes": ["speed", "context", "stability"],
    },
    {
        "id": "kv_q4",
        "label": "KV cache q4_0 — quarters KV VRAM",
        "flags": {"--cache-type-k": "q4_0", "--cache-type-v": "q4_0"},
        "axes": ["speed", "context", "stability"],
    },
    # ── C: Context ────────────────────────────────────────────────────────────
    {
        "id": "ctx_64k",
        "label": "ctx=64K (f16 KV — may OOM)",
        "flags": {"--ctx-size": "65536"},
        "axes": ["context"],
    },
    {
        "id": "ctx_64k_kv_q8",
        "label": "ctx=64K + q8 KV",
        "flags": {"--ctx-size": "65536", "--cache-type-k": "q8_0", "--cache-type-v": "q8_0"},
        "axes": ["context"],
    },
    {
        "id": "ctx_64k_kv_q4",
        "label": "ctx=64K + q4 KV",
        "flags": {"--ctx-size": "65536", "--cache-type-k": "q4_0", "--cache-type-v": "q4_0"},
        "axes": ["context"],
    },
    {
        "id": "ctx_96k_kv_q4",
        "label": "ctx=96K + q4 KV (stretch)",
        "flags": {"--ctx-size": "98304", "--cache-type-k": "q4_0", "--cache-type-v": "q4_0"},
        "axes": ["context"],
    },
    # ── D: Batch/ubatch ───────────────────────────────────────────────────────
    {
        "id": "ubatch_1024",
        "label": "ubatch-size=1024",
        "flags": {"--ubatch-size": "1024"},
        "axes": ["speed"],
    },
    {
        "id": "ubatch_2048",
        "label": "ubatch-size=2048",
        "flags": {"--ubatch-size": "2048"},
        "axes": ["speed"],
    },
    # ── E: Flash attn ─────────────────────────────────────────────────────────
    {
        "id": "flash_attn",
        "label": "--flash-attn on (attention layers in hybrid)",
        "flags": {"--flash-attn": "on"},
        "axes": ["speed", "stability"],
    },
    # ── F: Combos (filled after seeing A-E winners) ───────────────────────────
    # These use hardcoded candidates — update after first run if needed
    {
        "id": "combo_speed",
        "label": "combo: best threads + ubatch + flash-attn on",
        "flags": {"--threads": "16", "--ubatch-size": "1024", "--flash-attn": "on"},
        "axes": ["speed", "stability"],
    },
    {
        "id": "combo_ctx64k",
        "label": "combo: ctx=64K + q8 KV + threads=16",
        "flags": {"--ctx-size": "65536", "--cache-type-k": "q8_0", "--cache-type-v": "q8_0",
                  "--threads": "16"},
        "axes": ["context", "stability"],
    },
    {
        "id": "combo_all",
        "label": "combo: ctx=64K + q4 KV + threads=16 + flash-attn on",
        "flags": {"--ctx-size": "65536", "--cache-type-k": "q4_0", "--cache-type-v": "q4_0",
                  "--threads": "16", "--flash-attn": "on"},
        "axes": ["speed", "context", "stability"],
    },
]

# ── helpers ───────────────────────────────────────────────────────────────────

_log_lines = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    _log_lines.append(line)

def gpu_free_mib():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.free,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True)
    rows = []
    for line in r.stdout.strip().splitlines():
        parts = [int(x.strip()) for x in line.split(",")]
        rows.append({"used": parts[0], "free": parts[1], "total": parts[2]})
    return rows

def kill_server():
    subprocess.run(["pkill", "-9", "-f", "llama-server"], capture_output=True)
    time.sleep(2)
    # belt-and-suspenders: kill by port
    r = subprocess.run(["ss", "-tlnpH", f"sport = :{PORT}"], capture_output=True, text=True)
    for line in r.stdout.strip().splitlines():
        m = re.search(r'pid=(\d+)', line)
        if m:
            try:
                os.kill(int(m.group(1)), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

def wait_clean_vram(timeout=GPU_DRAIN_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        gpus = gpu_free_mib()
        if all(g["free"] >= CLEAN_VRAM_MIB for g in gpus):
            log(f"  VRAM clean: {[g['free'] for g in gpus]} MiB free")
            return True
        time.sleep(3)
    gpus = gpu_free_mib()
    log(f"  WARNING: VRAM not clean after {timeout}s: {[g['free'] for g in gpus]} MiB free")
    return False

def build_cmd(flags):
    cmd = [LLAMA_SERVER, "--model", MODEL_PATH,
           "--host", "0.0.0.0", "--port", str(PORT)]
    merged = dict(BASELINE_FLAGS)
    for k, v in flags.items():
        if v is None:
            merged.pop(k, None)
        else:
            merged[k] = v
    for k, v in merged.items():
        if v == "":
            cmd.append(k)
        else:
            cmd.extend([k, v])
    return cmd

def start_server(flags):
    cmd = build_cmd(flags)
    flag_display = " ".join(cmd[cmd.index("--host"):])
    log(f"  cmd: llama-server ... {flag_display}")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = LD_LIB
    fh = open(SERVER_LOG, "w")
    proc = subprocess.Popen(cmd, env=env, stdout=fh, stderr=fh)
    return proc, fh

def wait_ready(timeout=READY_TIMEOUT):
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
        "stream": False,
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
        timings = resp.get("timings", {})
        tps = timings.get("predicted_per_second", 0)
        tokens = resp.get("usage", {}).get("completion_tokens", 0)
        return tps, tokens
    except Exception as e:
        log(f"    request error: {e}")
        return None, 0

def run_experiment(exp):
    log(f"\n{'='*64}")
    log(f"EXP [{exp['id']}] {exp['label']}")
    log(f"  axes: {', '.join(exp['axes'])}")

    kill_server()
    time.sleep(2)
    wait_clean_vram()

    gpus = gpu_free_mib()
    log(f"  pre-start VRAM: {[(g['used'], g['free']) for g in gpus]} (used, free MiB)")

    proc, fh = start_server(exp["flags"])

    if not wait_ready(READY_TIMEOUT):
        log(f"  FAIL: server did not come up in {READY_TIMEOUT}s — likely OOM")
        proc.terminate()
        fh.close()
        # log last few lines of server output
        try:
            with open(SERVER_LOG) as f:
                tail = f.readlines()[-10:]
            for l in tail:
                log(f"  SERVER: {l.rstrip()}")
        except Exception:
            pass
        return None

    gpus = gpu_free_mib()
    log(f"  post-load VRAM: {[(g['used'], g['free']) for g in gpus]} (used, free MiB)")
    log(f"  server ready — warmup ({N_WARMUP})...")

    for i in range(N_WARMUP):
        tps, tok = bench_one(PROMPTS[i % len(PROMPTS)])
        status = f"{tps:.1f} t/s" if tps else "FAIL"
        log(f"    warmup {i+1}: {status}")

    log(f"  bench ({N_BENCH} runs)...")
    readings = []
    for i in range(N_BENCH):
        tps, tok = bench_one(PROMPTS[i % len(PROMPTS)])
        if tps and tps > 0:
            readings.append(tps)
            log(f"    run {i+1}: {tps:.1f} t/s ({tok} tokens)")
        else:
            log(f"    run {i+1}: FAIL")

    proc.terminate()
    fh.close()
    time.sleep(2)

    if not readings:
        log(f"  ALL BENCH RUNS FAILED")
        return None

    med    = statistics.median(readings)
    mean   = statistics.mean(readings)
    stddev = statistics.stdev(readings) if len(readings) > 1 else 0.0
    low    = min(readings)
    high   = max(readings)
    stable = stddev < STABILITY_STDDEV_THRESH

    log(f"  RESULT: median={med:.1f}  mean={mean:.1f}  stddev={stddev:.2f}  "
        f"min={low:.1f}  max={high:.1f}  stable={'YES' if stable else 'NO'}")

    return {
        "id":       exp["id"],
        "label":    exp["label"],
        "axes":     exp["axes"],
        "flags":    exp["flags"],
        "median":   med,
        "mean":     mean,
        "stddev":   stddev,
        "min":      low,
        "max":      high,
        "stable":   stable,
        "n":        len(readings),
        "raw":      readings,
    }

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    log(f"autoresearch-nemotron start — {datetime.now().isoformat()}")
    log(f"model: {MODEL_PATH}")
    log(f"binary: {LLAMA_SERVER}")
    log(f"experiments: {len(EXPERIMENTS)}")
    log(f"bench: {N_WARMUP} warmup + {N_BENCH} bench runs, {BENCH_TOKENS} tokens/run")

    results = []
    baseline_med = None

    for exp in EXPERIMENTS:
        r = run_experiment(exp)
        if r is None:
            log(f"  SKIPPED {exp['id']} (server failed or OOM)")
            results.append({"id": exp["id"], "label": exp["label"],
                            "axes": exp["axes"], "flags": exp["flags"],
                            "median": None, "stddev": None, "stable": None})
            continue

        results.append(r)

        if exp["id"] == "baseline":
            baseline_med = r["median"]
            log(f"  BASELINE SET: {baseline_med:.1f} t/s")
        elif baseline_med:
            delta = r["median"] - baseline_med
            pct   = delta / baseline_med * 100
            sign  = "+" if delta >= 0 else ""
            log(f"  vs baseline: {sign}{delta:.1f} t/s ({sign}{pct:.1f}%)")

    # ── final table ───────────────────────────────────────────────────────────
    log(f"\n{'='*64}")
    log("FINAL RESULTS")
    log(f"{'='*64}")
    log(f"{'id':<22} {'median':>7} {'stddev':>7} {'stable':>7} {'delta':>8}  axes")
    log(f"{'-'*22} {'-'*7} {'-'*7} {'-'*7} {'-'*8}  ----")

    valid = [r for r in results if r.get("median") is not None]
    for r in sorted(valid, key=lambda x: x["median"], reverse=True):
        delta = r["median"] - (baseline_med or 0)
        sign  = "+" if delta >= 0 else ""
        log(f"  {r['id']:<20} {r['median']:>7.1f} {r['stddev']:>7.2f} "
            f"{'YES' if r['stable'] else 'NO':>7} {sign}{delta:>7.1f}  "
            f"{','.join(r['axes'])}")

    # winner per axis
    speed_winner   = max((r for r in valid), key=lambda x: x["median"], default=None)
    ctx_winners    = [r for r in valid if "context" in r["axes"] and r.get("stable")]
    stable_winner  = min((r for r in valid if r.get("stable")), key=lambda x: x["stddev"], default=None)

    log(f"\nSPEED WINNER:   {speed_winner['id']} — {speed_winner['median']:.1f} t/s" if speed_winner else "\nSPEED WINNER: none")
    if ctx_winners:
        # find highest ctx-size that loaded successfully
        def ctx_size(r):
            v = r["flags"].get("--ctx-size", "32768")
            return int(v)
        best_ctx = max(ctx_winners, key=ctx_size)
        log(f"CONTEXT WINNER: {best_ctx['id']} — ctx={best_ctx['flags'].get('--ctx-size', '32768')} tokens, {best_ctx['median']:.1f} t/s")
    else:
        log("CONTEXT WINNER: none passed stability filter")
    log(f"STABILITY WIN:  {stable_winner['id']} — stddev={stable_winner['stddev']:.2f} t/s" if stable_winner else "STABILITY WIN: none")

    # ── write TSV ─────────────────────────────────────────────────────────────
    with open(RESULTS_TSV, "w") as f:
        f.write("id\tmedian\tmean\tstddev\tmin\tmax\tstable\tn\taxes\tflags\n")
        for r in results:
            if r.get("median") is None:
                f.write(f"{r['id']}\tFAIL\t\t\t\t\t\t\t{','.join(r['axes'])}\t\n")
            else:
                flags_str = " ".join(
                    f"{k}" if v == "" else f"{k} {v}"
                    for k, v in r["flags"].items()
                )
                f.write(
                    f"{r['id']}\t{r['median']:.2f}\t{r['mean']:.2f}\t{r['stddev']:.2f}\t"
                    f"{r['min']:.2f}\t{r['max']:.2f}\t{r['stable']}\t{r['n']}\t"
                    f"{','.join(r['axes'])}\t{flags_str}\n"
                )
    log(f"\nTSV: {RESULTS_TSV}")

    # ── write markdown log ────────────────────────────────────────────────────
    with open(LOG_MD, "w") as f:
        f.write(f"# autoresearch-nemotron — {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(f"Model: `{MODEL_PATH}`  \nBinary: `{LLAMA_SERVER}`  \n")
        f.write(f"Baseline: {baseline_med:.1f} t/s  \n\n")
        f.write("## Results by speed\n\n")
        f.write("| rank | id | median t/s | stddev | stable | delta | ctx | axes |\n")
        f.write("|------|-----|-----------|--------|--------|-------|-----|------|\n")
        for i, r in enumerate(sorted(valid, key=lambda x: x["median"], reverse=True)):
            delta = r["median"] - (baseline_med or 0)
            sign  = "+" if delta >= 0 else ""
            ctx   = r["flags"].get("--ctx-size", "32768")
            f.write(f"| {i+1} | {r['id']} | {r['median']:.1f} | {r['stddev']:.2f} | "
                    f"{'✓' if r['stable'] else '✗'} | {sign}{delta:.1f} | {ctx} | "
                    f"{','.join(r['axes'])} |\n")
        failed = [r for r in results if r.get("median") is None]
        if failed:
            f.write(f"\n**OOM/failed:** {', '.join(r['id'] for r in failed)}\n")
        f.write(f"\n## Full log\n\n```\n")
        f.write("\n".join(_log_lines))
        f.write("\n```\n")
    log(f"MD:  {LOG_MD}")

    # ── write winner start script ─────────────────────────────────────────────
    if speed_winner:
        merged = dict(BASELINE_FLAGS)
        for k, v in speed_winner["flags"].items():
            if v is None:
                merged.pop(k, None)
            else:
                merged[k] = v
        lines = [
            "#!/bin/bash",
            f"# nemotron winner: {speed_winner['id']} — {speed_winner['median']:.1f} t/s",
            f"# generated by autoresearch-nemotron {datetime.now().strftime('%Y-%m-%d')}",
            f"export LD_LIBRARY_PATH={LD_LIB}",
            f"exec {LLAMA_SERVER} \\",
            f"  --model {MODEL_PATH} \\",
            f"  --host 0.0.0.0 --port {PORT} \\",
        ]
        items = list(merged.items())
        for i, (k, v) in enumerate(items):
            tail = " \\" if i < len(items) - 1 else ""
            lines.append(f"  {k} {v}{tail}" if v != "" else f"  {k}{tail}")
        WINNER_SH.write_text("\n".join(lines) + "\n")
        WINNER_SH.chmod(0o755)
        log(f"Winner start script: {WINNER_SH}")

    log(f"\nautoresearch-nemotron complete — {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
