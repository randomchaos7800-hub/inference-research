#!/usr/bin/env python3
"""
autoresearch-prism-pro.py — PRISM-PRO-DQ llama.cpp tuning, dual RTX 5060 Ti

Model:    Qwen3.6-27B-PRISM-PRO-DQ (13.7 GB GGUF, hybrid SSM+Attention, 65 blocks)
Engine:   llama.cpp llama-server (auto-splits across both GPUs)
Baseline: MTP n_max=1, ctx=32K, threads=8, cache f16 → ~35 t/s

Experiments:
  Group A — MTP draft tokens
    1. baseline       — n_max=1, n_min=1 (current)
    2. mtp_n0         — no speculative decoding (sanity baseline)
    3. mtp_n2         — n_max=2
    4. mtp_n3         — n_max=3
    5. mtp_n2_min2    — n_max=2, n_min=2 (force 2 always)

  Group B — KV cache quantization (frees VRAM for longer ctx)
    6. kv_q8          — cache-type-k/v q8_0
    7. kv_q4          — cache-type-k/v q4_0
    8. kv_q4_mtp2     — q4 KV + MTP n=2 (combo)

  Group C — Context size
    9. ctx_16k        — ctx-size 16384
   10. ctx_64k        — ctx-size 65536 (needs VRAM headroom)
   11. ctx_64k_q8     — ctx-size 65536 + q8 KV (more headroom)

  Group D — Batch/thread tuning
   12. threads_4      — 4 CPU threads
   13. threads_16     — 16 CPU threads
   14. ubatch_256     — ubatch-size 256
   15. ubatch_1024    — ubatch-size 1024

  Group E — Flash attention
   16. flash_attn     — --flash-attn (may help attention layers in hybrid)

  Group F — Combos of winners (filled in after groups A-E)
   17. best_combo     — winner MTP + winner KV + winner threads

Run: python3 autoresearch-prism-pro.py
Results: /home/dino/inference-research/autoresearch-prism-pro-results.tsv
Log:     /home/dino/inference-research/autoresearch-prism-pro-log.md
"""

import os, re, signal, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from statistics import median

# ── config ────────────────────────────────────────────────────────────────────

MODEL_PATH   = "/home/dino/models/Qwen3.6-27B-PRISM-PRO-DQ/Qwen3.6-27B-PRISM-PRO-DQ.gguf"
LLAMA_SERVER = "/home/dino/llama.cpp/build-cuda13/bin/llama-server"
LD_LIB       = "/home/dino/llama.cpp/build-cuda13/bin"
LOG_FILE     = "/tmp/prism-serve.log"
RESULTS_TSV  = Path("/home/dino/inference-research/autoresearch-prism-pro-results.tsv")
LOG_MD       = Path("/home/dino/inference-research/autoresearch-prism-pro-log.md")

PORT         = 8022
URL          = f"http://localhost:{PORT}/v1/chat/completions"
HEALTH       = f"http://localhost:{PORT}/health"
HEADERS      = {"Content-Type": "application/json"}

BENCH_TOKENS     = 512
N_WARMUP         = 2
N_BENCH          = 5
READY_TIMEOUT    = 120
CLEAN_VRAM_MIB   = 1000   # both GPUs below this = clean
GPU_DRAIN_TIMEOUT = 45
IMPROVE_THRESHOLD = 1.0   # t/s to call a win

# Baseline flags (always present unless overridden)
BASELINE_FLAGS = {
    "--n-gpu-layers": "999",
    "--ctx-size":     "32768",
    "--threads":      "8",
    "--spec-type":    "draft-mtp",
    "--spec-draft-n-max": "1",
    "--spec-draft-n-min": "1",
    "--reasoning":    "off",
}

PROMPTS = [
    "Explain in technical detail how CUDA tensor cores accelerate matrix multiplication on Blackwell GPU architecture. Cover the hardware pipeline, precision handling, KV cache memory implications, and tensor parallel communication patterns.",
    "Describe the engineering challenges of running large language model inference at scale, covering batching strategies, KV cache management, quantization approaches, and tensor parallel communication patterns.",
    "Explain the architecture of a Retrieval Augmented Generation system, covering embedding models, vector databases, chunking strategies, hybrid search, reranking, and prompt construction for grounded generation.",
    "Describe how speculative decoding works to accelerate autoregressive inference, covering draft models, token verification, acceptance rates, and Multi-Token Prediction approaches in modern inference engines.",
    "Explain CUDA memory management for deep learning, covering cudaMalloc, memory pools, VRAM fragmentation, unified memory, and best practices for managing GPU memory in multi-GPU inference workloads.",
    "Describe how prefix caching works in LLM inference servers, covering KV cache reuse, hash-based cache lookup, cache eviction policies, and the throughput impact on production workloads.",
    "Explain the Mamba state space model architecture, covering selective state spaces, input-dependent transitions, parallel scan computation, and how SSMs compare to attention for long-context inference.",
]

EXPERIMENTS = [
    # A: MTP draft tokens
    {
        "id":    "baseline",
        "label": "MTP n_max=1 (current)",
        "flags": {},
    },
    {
        "id":    "mtp_n0",
        "label": "no speculative decoding (sanity baseline)",
        "flags": {"--spec-type": None, "--spec-draft-n-max": None, "--spec-draft-n-min": None},
    },
    {
        "id":    "mtp_n2",
        "label": "MTP n_max=2",
        "flags": {"--spec-draft-n-max": "2"},
    },
    {
        "id":    "mtp_n3",
        "label": "MTP n_max=3",
        "flags": {"--spec-draft-n-max": "3"},
    },
    {
        "id":    "mtp_n2_min2",
        "label": "MTP n_max=2 n_min=2 (force 2 drafts always)",
        "flags": {"--spec-draft-n-max": "2", "--spec-draft-n-min": "2"},
    },
    # B: KV cache quantization
    {
        "id":    "kv_q8",
        "label": "KV cache q8_0 (halves KV VRAM)",
        "flags": {"--cache-type-k": "q8_0", "--cache-type-v": "q8_0"},
    },
    {
        "id":    "kv_q4",
        "label": "KV cache q4_0 (quarters KV VRAM)",
        "flags": {"--cache-type-k": "q4_0", "--cache-type-v": "q4_0"},
    },
    {
        "id":    "kv_q8_mtp2",
        "label": "q8 KV + MTP n=2 (combo)",
        "flags": {"--cache-type-k": "q8_0", "--cache-type-v": "q8_0", "--spec-draft-n-max": "2"},
    },
    # C: Context size
    {
        "id":    "ctx_16k",
        "label": "ctx-size 16384",
        "flags": {"--ctx-size": "16384"},
    },
    {
        "id":    "ctx_64k",
        "label": "ctx-size 65536",
        "flags": {"--ctx-size": "65536"},
    },
    {
        "id":    "ctx_64k_q8",
        "label": "ctx-size 65536 + q8 KV",
        "flags": {"--ctx-size": "65536", "--cache-type-k": "q8_0", "--cache-type-v": "q8_0"},
    },
    # D: Threads and batch
    {
        "id":    "threads_4",
        "label": "4 CPU threads",
        "flags": {"--threads": "4"},
    },
    {
        "id":    "threads_16",
        "label": "16 CPU threads",
        "flags": {"--threads": "16"},
    },
    {
        "id":    "ubatch_256",
        "label": "ubatch-size 256",
        "flags": {"--ubatch-size": "256"},
    },
    {
        "id":    "ubatch_1024",
        "label": "ubatch-size 1024",
        "flags": {"--ubatch-size": "1024"},
    },
    # E: Flash attention
    {
        "id":    "flash_attn",
        "label": "flash-attn (attention layers in hybrid)",
        "flags": {"--flash-attn": ""},
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
        ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True
    )
    return [int(x.strip()) for x in r.stdout.strip().splitlines() if x.strip()]


def kill_server():
    subprocess.run(["pkill", "-9", "-f", "llama-server"], capture_output=True)
    # Also kill by port
    r = subprocess.run(["ss", "-tlnpH", f"sport = :{PORT}"], capture_output=True, text=True)
    for line in r.stdout.strip().splitlines():
        m = re.search(r'pid=(\d+)', line)
        if m:
            try:
                os.kill(int(m.group(1)), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


def wait_clean_gpu(timeout=GPU_DRAIN_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        free = gpu_free_mib()
        if all(f >= (16311 - CLEAN_VRAM_MIB) for f in free):
            log(f"  GPU clean: {free} MiB free")
            return True
        time.sleep(2)
    log(f"  WARNING: GPU not clean after {timeout}s: {gpu_free_mib()}")
    return False


def build_flags(exp_flags):
    """Merge baseline flags with experiment overrides. None value = remove flag."""
    flags = dict(BASELINE_FLAGS)
    for k, v in exp_flags.items():
        if v is None:
            flags.pop(k, None)
        else:
            flags[k] = v
    return flags


def start_server(flags):
    cmd = [LLAMA_SERVER, "--model", MODEL_PATH, "--host", "0.0.0.0", "--port", str(PORT)]
    for k, v in flags.items():
        if v == "":       # boolean flag, no value
            cmd.append(k)
        else:
            cmd.extend([k, v])
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = LD_LIB

    log_fh = open(LOG_FILE, "w")
    proc = subprocess.Popen(cmd, env=env, stdout=log_fh, stderr=log_fh)
    return proc, log_fh


def wait_ready(timeout=READY_TIMEOUT):
    import urllib.request, urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def read_tg_from_log():
    """Parse all 'tg = X t/s' lines from server log, return list of floats."""
    try:
        with open(LOG_FILE) as f:
            content = f.read()
        return [float(m) for m in re.findall(r'tg\s*=\s*([\d.]+)\s*t/s', content)]
    except Exception:
        return []


def bench_single(prompt):
    import urllib.request, json
    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": BENCH_TOKENS,
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers=HEADERS, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            body = json.loads(r.read())
        elapsed = time.time() - t0
        tokens = body.get("usage", {}).get("completion_tokens", BENCH_TOKENS)
        return tokens / elapsed if elapsed > 0 else 0.0
    except Exception as e:
        log(f"  bench error: {e}")
        return 0.0


def run_experiment(exp):
    log(f"\n{'='*60}")
    log(f"EXP: {exp['id']} — {exp['label']}")

    kill_server()
    time.sleep(3)
    wait_clean_gpu()

    flags = build_flags(exp["flags"])
    flag_str = " ".join(f"{k} {v}" if v != "" else k for k, v in flags.items())
    log(f"  flags: {flag_str}")

    proc, log_fh = start_server(flags)

    if not wait_ready():
        log(f"  FAIL: server did not come up in {READY_TIMEOUT}s")
        proc.terminate()
        log_fh.close()
        return None

    log(f"  server ready")

    # warmup
    log(f"  warmup ({N_WARMUP} runs)...")
    for i in range(N_WARMUP):
        bench_single(PROMPTS[i % len(PROMPTS)])

    # clear log tg readings before benchmark
    open(LOG_FILE, "w").close()
    proc_log_fh = open(LOG_FILE, "a")

    # bench
    log(f"  bench ({N_BENCH} runs)...")
    wall_toks = []
    for i in range(N_BENCH):
        tps = bench_single(PROMPTS[i % len(PROMPTS)])
        wall_toks.append(tps)
        log(f"    run {i+1}: {tps:.2f} t/s (wall)")

    # grab server-reported tg values
    proc_log_fh.close()
    tg_vals = read_tg_from_log()
    log(f"  server tg readings: {[round(x,2) for x in tg_vals]}")

    wall_med = median(wall_toks) if wall_toks else 0.0
    tg_med   = median(tg_vals)   if tg_vals   else 0.0

    log(f"  RESULT: wall={wall_med:.2f} t/s  server_tg={tg_med:.2f} t/s")

    proc.terminate()
    log_fh.close()
    time.sleep(2)

    return {
        "id":       exp["id"],
        "label":    exp["label"],
        "flags":    flag_str,
        "wall_med": wall_med,
        "tg_med":   tg_med,
        "wall_all": wall_toks,
        "tg_all":   tg_vals,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    log(f"autoresearch-prism-pro starting — {datetime.now().isoformat()}")
    log(f"model: {MODEL_PATH}")
    log(f"experiments: {len(EXPERIMENTS)}")

    results = []
    baseline_tg = None

    for exp in EXPERIMENTS:
        r = run_experiment(exp)
        if r is None:
            log(f"  skipping {exp['id']} (server failed)")
            continue

        results.append(r)

        if exp["id"] == "baseline":
            baseline_tg = r["tg_med"]
            log(f"  baseline set: {baseline_tg:.2f} t/s")
        elif baseline_tg:
            delta = r["tg_med"] - baseline_tg
            sign = "+" if delta >= 0 else ""
            log(f"  vs baseline: {sign}{delta:.2f} t/s ({sign}{delta/baseline_tg*100:.1f}%)")

    # ── results table ─────────────────────────────────────────────────────────
    log(f"\n{'='*60}")
    log("FINAL RESULTS")
    log(f"{'='*60}")

    sorted_results = sorted(results, key=lambda x: x["tg_med"], reverse=True)
    for r in sorted_results:
        delta = r["tg_med"] - (baseline_tg or 0)
        sign = "+" if delta >= 0 else ""
        log(f"  {r['id']:20s}  tg={r['tg_med']:6.2f}  wall={r['wall_med']:6.2f}  ({sign}{delta:.2f})")

    winner = sorted_results[0]
    log(f"\nWINNER: {winner['id']} — {winner['tg_med']:.2f} t/s")
    log(f"  flags: {winner['flags']}")

    # ── write TSV ─────────────────────────────────────────────────────────────
    with open(RESULTS_TSV, "w") as f:
        f.write("id\tlabel\twall_med\ttg_med\tflags\n")
        for r in results:
            f.write(f"{r['id']}\t{r['label']}\t{r['wall_med']:.2f}\t{r['tg_med']:.2f}\t{r['flags']}\n")
    log(f"\nTSV: {RESULTS_TSV}")

    # ── write markdown log ────────────────────────────────────────────────────
    with open(LOG_MD, "w") as f:
        f.write(f"# autoresearch-prism-pro — {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(f"Model: {MODEL_PATH}\n\n")
        f.write(f"## Results\n\n")
        f.write("| rank | id | tg_med | wall_med | delta | flags |\n")
        f.write("|------|-----|--------|----------|-------|-------|\n")
        for i, r in enumerate(sorted_results):
            delta = r["tg_med"] - (baseline_tg or 0)
            sign = "+" if delta >= 0 else ""
            f.write(f"| {i+1} | {r['id']} | {r['tg_med']:.2f} | {r['wall_med']:.2f} | {sign}{delta:.2f} | `{r['flags']}` |\n")
        f.write(f"\n## Winner\n\n`{winner['flags']}`\n\n")
        f.write("## Full log\n\n```\n")
        f.write("\n".join(_log_lines))
        f.write("\n```\n")
    log(f"MD:  {LOG_MD}")

    # ── update start script with winner ───────────────────────────────────────
    winner_flags = build_flags(EXPERIMENTS[[e["id"] for e in EXPERIMENTS].index(winner["id"])]["flags"])
    script_lines = [
        "#!/bin/bash",
        f"export LD_LIBRARY_PATH={LD_LIB}",
        f"exec {LLAMA_SERVER} \\",
        f"  --model {MODEL_PATH} \\",
        f"  --host 0.0.0.0 --port {PORT} \\",
    ]
    flag_items = list(winner_flags.items())
    for i, (k, v) in enumerate(flag_items):
        tail = " \\" if i < len(flag_items) - 1 else ""
        if v == "":
            script_lines.append(f"  {k}{tail}")
        else:
            script_lines.append(f"  {k} {v}{tail}")

    script_content = "\n".join(script_lines) + "\n"
    with open("/tmp/prism-start.sh", "w") as f:
        f.write(script_content)
    os.chmod("/tmp/prism-start.sh", 0o755)
    log(f"\nStart script updated: /tmp/prism-start.sh")
    log(f"\nautoresearch-prism-pro complete.")


if __name__ == "__main__":
    main()
