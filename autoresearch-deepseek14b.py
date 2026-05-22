#!/usr/bin/env python3
"""
autoresearch-deepseek14b.py
DeepSeek-R1-Distill-Qwen-14B AWQ — comprehensive autoresearch on dual RTX 5060 Ti

Throughput sweep: GMU 0.85/0.90/0.92, TP=1 vs TP=2, KV dtype (auto/fp8/nvfp4), seqs/batch
Cache size sweep: ctx 32K / 65K / 128K × KV dtype

Recovery: 10-min hard timeout per experiment (threading watchdog + SIGKILL)
Checkpoint/resume: writes checkpoint.json after each experiment; resumes on restart

Run:
  cd /home/dino/inference-research
  nohup python3 autoresearch-deepseek14b.py >> autoresearch-deepseek14b-stdout.log 2>&1 &
  echo $! > autoresearch-deepseek14b.pid
"""

import csv, json, os, signal, subprocess, sys, threading, time
from datetime import datetime
from pathlib import Path
from statistics import median

# ── paths & constants ─────────────────────────────────────────────────────────

RESULTS_TSV = Path("/home/dino/inference-research/autoresearch-deepseek14b-results.tsv")
LOG_MD      = Path("/home/dino/inference-research/autoresearch-deepseek14b-log.md")
CHECKPOINT  = Path("/home/dino/inference-research/autoresearch-deepseek14b-checkpoint.json")
VENV        = "/opt/ai/vllm-env"
MODEL_PATH  = "/home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ"

PORT    = 8022
API_KEY = "genesis-local"
MODEL   = "deepseek-r1-14b"
URL     = f"http://localhost:{PORT}/v1/completions"
HEALTH  = f"http://localhost:{PORT}/health"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

BENCH_TOKENS       = 512
N_WARMUP           = 2
N_BENCH            = 5
READY_TIMEOUT      = 480    # 8 min to become healthy
EXPERIMENT_TIMEOUT = 600    # 10 min hard kill per experiment
DRAIN_TIMEOUT      = 60
CLEAN_VRAM_MIB     = 800    # both GPUs must have ≤800 MiB used (driver baseline ~600 MiB)
IMPROVE_THRESHOLD  = 1.0    # t/s delta to call a win/loss

COMMON_ENV = {
    "PATH":                         "/usr/local/cuda-13.0/bin:/opt/ai/vllm-env/bin:/usr/bin:/bin",
    "LD_LIBRARY_PATH":              "/usr/local/cuda-13.0/lib64",
    "CUDA_HOME":                    "/usr/local/cuda-13.0",
    "VLLM_NO_USAGE_STATS":          "1",
    "VLLM_USE_FLASHINFER_SAMPLER":  "1",
    "VLLM_FLOAT32_MATMUL_PRECISION":"high",
    "VLLM_ALLOW_LONG_MAX_MODEL_LEN":"1",
    "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
    "VLLM_LOGGING_LEVEL":           "WARNING",
    "PYTORCH_CUDA_ALLOC_CONF":      "expandable_segments:True,max_split_size_mb:512",
    "NCCL_P2P_DISABLE":             "1",
    "NCCL_BUFFSIZE":                "4194304",
    "OMP_NUM_THREADS":              "1",
    "CUDA_DEVICE_MAX_CONNECTIONS":  "8",
}

BASE_ARGS = [
    f"{VENV}/bin/vllm", "serve", MODEL_PATH,
    "--tensor-parallel-size",    "2",
    "--gpu-memory-utilization",  "0.85",
    "--max-model-len",           "65536",
    "--kv-cache-dtype",          "auto",
    "--max-num-seqs",            "2",
    "--max-num-batched-tokens",  "4096",
    "--enable-chunked-prefill",
    "--enable-prefix-caching",
    "--dtype",                   "bfloat16",
    "--disable-custom-all-reduce",
    "--trust-remote-code",
    "--reasoning-parser",        "deepseek_r1",
    "--api-key",                 API_KEY,
    "--served-model-name",       MODEL,
    "--host",                    "0.0.0.0",
    "--port",                    str(PORT),
    "--disable-log-stats",
]

PROMPTS = [
    "Explain in technical detail how CUDA tensor cores accelerate matrix multiplication on Blackwell GPU architecture. Cover the hardware pipeline, NVFP4 vs FP8 precision handling, KV cache memory implications, and tensor parallel communication patterns.",
    "Describe the engineering challenges of running large language model inference at scale, covering batching strategies, KV cache management, quantization approaches, and tensor parallel communication patterns.",
    "Explain the architecture of a Retrieval Augmented Generation system, covering embedding models, vector databases, chunking strategies, hybrid search, reranking, and prompt construction for grounded generation.",
    "Describe how speculative decoding works to accelerate autoregressive inference, covering draft models, token verification, acceptance rates, and Multi-Token Prediction approaches in modern inference engines.",
    "Explain CUDA memory management for deep learning, covering cudaMalloc, memory pools, VRAM fragmentation, unified memory, and best practices for managing GPU memory in multi-GPU inference workloads.",
    "Describe how prefix caching works in LLM inference servers, covering KV cache reuse, hash-based cache lookup, cache eviction policies, and the throughput impact on production workloads.",
    "Explain the Mamba state space model architecture, covering selective state spaces, input-dependent transitions, parallel scan computation, and how SSMs compare to attention for long-context inference.",
]

# ── experiments ───────────────────────────────────────────────────────────────
# Throughput section: vary GMU, TP, KV dtype, seqs/batch
# Cache size section: vary max-model-len × KV dtype

EXPERIMENTS = [
    # ── throughput sweep ─────────────────────────────────────────────────────
    {
        "id":    "baseline",
        "label": "Baseline (TP=2, GMU=0.85, ctx=65536, auto KV, seqs=2, batch=4096)",
        "overrides": {},
    },
    {
        "id":    "gmu_090",
        "label": "GMU=0.90 — more KV blocks for the same context",
        "overrides": {"--gpu-memory-utilization": "0.90"},
    },
    {
        "id":    "gmu_092",
        "label": "GMU=0.92 — max safe VRAM allocation",
        "overrides": {"--gpu-memory-utilization": "0.92"},
    },
    {
        "id":    "single_gpu",
        "label": "TP=1 single GPU — eliminate TP communication overhead (14B AWQ fits in 16GB)",
        "overrides": {
            "--tensor-parallel-size":   "1",
            "--gpu-memory-utilization": "0.90",
        },
    },
    {
        "id":    "fp8_kv",
        "label": "FP8 KV cache — halves KV footprint vs auto/bf16",
        "overrides": {"--kv-cache-dtype": "fp8"},
    },
    {
        "id":    "nvfp4_kv",
        "label": "NVFP4 KV cache — native Blackwell FP4, quarter KV footprint",
        "overrides": {"--kv-cache-dtype": "nvfp4"},
    },
    {
        "id":    "seqs4",
        "label": "seqs=4, batch=8192, GMU=0.90 — higher concurrency headroom",
        "overrides": {
            "--gpu-memory-utilization":  "0.90",
            "--max-num-seqs":            "4",
            "--max-num-batched-tokens":  "8192",
        },
    },
    # ── cache size sweep ─────────────────────────────────────────────────────
    {
        "id":    "ctx_32k",
        "label": "ctx=32768 — shorter window, more KV block slots per VRAM",
        "overrides": {"--max-model-len": "32768"},
    },
    {
        "id":    "ctx_128k",
        "label": "ctx=131072 — full DeepSeek-R1 context (GMU=0.90 for headroom)",
        "overrides": {
            "--max-model-len":          "131072",
            "--gpu-memory-utilization": "0.90",
        },
    },
    {
        "id":    "ctx_128k_fp8",
        "label": "ctx=131072 + FP8 KV — full context, halved KV footprint",
        "overrides": {
            "--max-model-len":  "131072",
            "--kv-cache-dtype": "fp8",
        },
    },
    {
        "id":    "ctx_128k_nvfp4",
        "label": "ctx=131072 + NVFP4 KV — full context, native Blackwell quarter-precision KV",
        "overrides": {
            "--max-model-len":  "131072",
            "--kv-cache-dtype": "nvfp4",
        },
    },
]

# ── state ─────────────────────────────────────────────────────────────────────

_log_lines    = []
_kill_event   = threading.Event()


def log(msg):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    _log_lines.append(line)


# ── GPU helpers ───────────────────────────────────────────────────────────────

def gpu_free_mib():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    )
    return [int(x.strip()) for x in r.stdout.strip().splitlines() if x.strip()]


def kill_gpu_procs():
    r = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
        capture_output=True, text=True,
    )
    killed = []
    for p in r.stdout.strip().splitlines():
        p = p.strip()
        if not p:
            continue
        try:
            pid = int(p)
            # spare proxy / agent processes
            with open(f"/proc/{pid}/cmdline") as f:
                cmd = f.read()
            if any(k in cmd for k in ["proxy.py", "frank", "mike", "kato", "hermes"]):
                continue
            os.kill(pid, signal.SIGKILL)
            killed.append(pid)
        except Exception:
            pass
    return killed


def kill_port_procs(port=PORT):
    import re as _re
    r = subprocess.run(["ss", "-tlnpH", f"sport = :{port}"],
                       capture_output=True, text=True)
    killed = []
    for line in r.stdout.strip().splitlines():
        m = _re.search(r'pid=(\d+)', line)
        if m:
            pid = int(m.group(1))
            try:
                os.kill(pid, signal.SIGKILL)
                killed.append(pid)
            except Exception:
                pass
    if killed:
        log(f"  killed port-{port} procs: {killed}")
    return killed


def wait_clean_gpu(timeout=DRAIN_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        free = gpu_free_mib()
        if all(f >= (16311 - CLEAN_VRAM_MIB) for f in free):
            log(f"  GPU clean: {free} MiB free")
            return True
        time.sleep(3)
    free = gpu_free_mib()
    log(f"  WARNING: GPU not clean after {timeout}s: {free}")
    return False


def drain_all(pgid=None):
    if pgid is not None:
        try:
            os.killpg(pgid, signal.SIGTERM)
            time.sleep(3)
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            pass
    kill_gpu_procs()
    kill_port_procs()
    time.sleep(5)
    kill_gpu_procs()
    kill_port_procs()
    wait_clean_gpu()


# ── args builder ──────────────────────────────────────────────────────────────

def build_args(exp):
    """BASE_ARGS with flag overrides applied."""
    args = list(BASE_ARGS)
    for flag, value in exp["overrides"].items():
        if flag in args:
            idx = args.index(flag)
            args[idx + 1] = value
        else:
            pos = args.index("--disable-log-stats")
            args.insert(pos, value)
            args.insert(pos, flag)
    return args


# ── health / bench ────────────────────────────────────────────────────────────

def port_owner_pid(port=PORT):
    import re as _re
    r = subprocess.run(["ss", "-tlnpH", f"sport = :{port}"],
                       capture_output=True, text=True)
    for line in r.stdout.strip().splitlines():
        m = _re.search(r'pid=(\d+)', line)
        if m:
            return int(m.group(1))
    return None


def wait_ready(test_pgid, timeout=READY_TIMEOUT):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _kill_event.is_set():
            return False
        try:
            owner = port_owner_pid()
            if owner is not None:
                try:
                    owner_pgid = os.getpgid(owner)
                except ProcessLookupError:
                    owner_pgid = -1
                if owner_pgid == test_pgid:
                    resp = urllib.request.urlopen(HEALTH, timeout=5)
                    if resp.status == 200:
                        return True
        except Exception:
            pass
        elapsed = int(time.time() - (deadline - timeout))
        print(f"\r  {elapsed}s ...", end="", flush=True)
        time.sleep(5)
    print()
    return False


def one_inference(prompt_idx):
    import urllib.request, json
    prompt = PROMPTS[prompt_idx % len(PROMPTS)]
    body   = json.dumps({
        "model": MODEL, "prompt": prompt,
        "max_tokens": BENCH_TOKENS, "temperature": 0, "stream": False,
    }).encode()
    req = urllib.request.Request(URL, data=body, headers=HEADERS, method="POST")
    t0  = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    elapsed = time.time() - t0
    return data["usage"]["completion_tokens"] / elapsed


def run_benchmark():
    log(f"  warmup ×{N_WARMUP}...")
    for i in range(N_WARMUP):
        if _kill_event.is_set():
            return None
        try:
            tps = one_inference(i)
            log(f"    warmup {i+1}: {tps:.2f} t/s")
        except Exception as e:
            log(f"    warmup {i+1} ERROR: {e}")

    log(f"  bench ×{N_BENCH}...")
    results = []
    for i in range(N_BENCH):
        if _kill_event.is_set():
            return None
        try:
            tps = one_inference(N_WARMUP + i)
            results.append(tps)
            log(f"    run {i+1}: {tps:.2f} t/s")
        except Exception as e:
            log(f"    run {i+1} ERROR: {e}")

    if not results:
        return None
    return {
        "median": round(median(results), 2),
        "min":    round(min(results), 2),
        "max":    round(max(results), 2),
        "runs":   results,
    }


# ── checkpoint ────────────────────────────────────────────────────────────────

def load_checkpoint():
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text())
    return {"done": [], "rows": []}


def save_checkpoint(state):
    CHECKPOINT.write_text(json.dumps(state, indent=2))


# ── watchdog ─────────────────────────────────────────────────────────────────

def _watchdog(pgid, timeout):
    """Fire after timeout seconds and hard-kill everything."""
    if not _kill_event.wait(timeout=timeout):
        log(f"\n  !! HARD TIMEOUT ({timeout}s) — emergency SIGKILL pgid={pgid} !!")
        _kill_event.set()
        try:
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            pass
        kill_gpu_procs()
        kill_port_procs()


# ── experiment runner ─────────────────────────────────────────────────────────

def run_experiment(exp, baseline_tps):
    log(f"\n{'='*60}")
    log(f"EXPERIMENT: {exp['id']}")
    log(f"  {exp['label']}")

    drain_all()

    args    = build_args(exp)
    env     = {**os.environ, **COMMON_ENV}
    log_fh  = open(f"/tmp/deepseek-bench-{exp['id']}.log", "w")
    log(f"  cmd: {' '.join(args[:6])} ...")

    _kill_event.clear()
    proc = subprocess.Popen(args, env=env, stdout=log_fh, stderr=log_fh,
                            preexec_fn=os.setsid)
    pgid = os.getpgid(proc.pid)
    log(f"  pid={proc.pid} pgid={pgid}")

    # arm 10-min hard timeout
    wd = threading.Thread(target=_watchdog, args=(pgid, EXPERIMENT_TIMEOUT), daemon=True)
    wd.start()

    ready = wait_ready(test_pgid=pgid)
    if not ready:
        log("  FAIL: never became healthy (timeout or hard-kill)")
        _kill_event.set()
        drain_all(pgid)
        log_fh.close()
        return None

    log(f"  healthy at {datetime.now().strftime('%H:%M:%S')}")
    free = gpu_free_mib()
    log(f"  VRAM free: {free} MiB")

    result = run_benchmark()

    _kill_event.set()   # cancel watchdog
    drain_all(pgid)
    log_fh.close()

    if result:
        delta = round(result["median"] - baseline_tps, 2) if baseline_tps else 0.0
        win   = ("WIN" if delta >= IMPROVE_THRESHOLD
                 else "LOSS" if delta <= -IMPROVE_THRESHOLD
                 else "NEUTRAL")
        log(f"  RESULT: {result['median']:.2f} t/s  ({delta:+.2f} vs baseline)  [{win}]")
    else:
        log("  RESULT: FAILED")

    return result


# ── output ────────────────────────────────────────────────────────────────────

def write_results(rows):
    with open(RESULTS_TSV, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["timestamp", "id", "label", "overrides",
                    "median_tps", "min_tps", "max_tps",
                    "delta", "outcome", "runs"])
        for r in rows:
            w.writerow(r)


def write_markdown(rows):
    baseline_tps = next((r[4] for r in rows if r[1] == "baseline" and r[4]), None)
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# DeepSeek-R1-Distill-14B AWQ Autoresearch — {now}",
        "",
        f"**Baseline:** {baseline_tps} t/s  (TP=2, GMU=0.85, ctx=65536, auto KV, seqs=2)",
        f"**Genesis reference:** 65.40 t/s (eval-v4, same config)",
        f"**Threshold:** ±{IMPROVE_THRESHOLD} t/s for win/loss",
        "",
        "## Throughput Sweep",
        "",
        "| ID | Label | Median t/s | Delta | Outcome |",
        "|---|---|---|---|---|",
    ]
    throughput_ids = ["baseline","gmu_090","gmu_092","single_gpu",
                      "fp8_kv","nvfp4_kv","seqs4"]
    cache_ids      = ["ctx_32k","ctx_128k","ctx_128k_fp8","ctx_128k_nvfp4"]

    def row_line(r):
        _, eid, label, overrides, med, mn, mx, delta, outcome, _ = r
        med_s   = f"{med:.2f}" if med else "FAIL"
        delta_s = f"{delta:+.2f}" if delta is not None else "—"
        return f"| {eid} | {label} | {med_s} | {delta_s} | {outcome} |"

    for r in rows:
        if r[1] in throughput_ids:
            lines.append(row_line(r))

    lines += ["", "## Cache Size Sweep", "",
              "| ID | Label | Median t/s | Delta | Outcome |",
              "|---|---|---|---|---|"]
    for r in rows:
        if r[1] in cache_ids:
            lines.append(row_line(r))

    wins = [r for r in rows if r[8] == "WIN"]
    lines += ["", "## Recommendation", ""]
    if wins:
        best = max(wins, key=lambda r: r[4] or 0)
        lines.append(
            f"**Deploy `{best[1]}`** — {best[4]:.2f} t/s "
            f"({best[7]:+.2f} vs baseline). Update vllm-deepseek-r1-start.sh."
        )
    else:
        lines.append("Baseline config is optimal. No improvement found.")

    lines += ["", "## Log", "", "```"]
    lines.extend(_log_lines)
    lines.append("```\n")
    LOG_MD.write_text("\n".join(lines))
    log(f"Report → {LOG_MD}")


# ── restore production ────────────────────────────────────────────────────────

def restore_production():
    log("\nRestoring production backend (vllm-backend.service)...")
    drain_all()
    subprocess.run(["systemctl", "--user", "reset-failed", "vllm-backend.service"],
                   check=False, capture_output=True)
    subprocess.run(["systemctl", "--user", "start", "vllm-backend.service"],
                   check=False)
    log("  waiting for production deepseek-r1 backend...")
    import urllib.request
    deadline = time.time() + 480
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(HEALTH, timeout=5)
            if resp.status == 200:
                log("  production backend healthy")
                return
        except Exception:
            pass
        time.sleep(10)
    log("  WARNING: production backend did not come up — check manually")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    log(f"DeepSeek-R1-Distill-14B AWQ autoresearch  {datetime.now():%Y-%m-%d %H:%M:%S}")
    log(f"Model: {MODEL_PATH}")
    log(f"Experiments: {len(EXPERIMENTS)}  |  Timeout: {EXPERIMENT_TIMEOUT}s/exp")

    state        = load_checkpoint()
    done_ids     = set(state["done"])
    rows         = state["rows"]
    baseline_tps = next((r[4] for r in rows if r[1] == "baseline" and r[4]), None)

    if done_ids:
        log(f"Resuming — already done: {sorted(done_ids)}")

    for exp in EXPERIMENTS:
        if exp["id"] in done_ids:
            log(f"  skip {exp['id']} (checkpoint)")
            continue

        result = run_experiment(exp, baseline_tps)

        med  = result["median"] if result else None
        mn   = result["min"]    if result else None
        mx   = result["max"]    if result else None

        if exp["id"] == "baseline" and med:
            baseline_tps = med

        delta = round(med - baseline_tps, 2) if (med and baseline_tps) else None

        if delta is None:
            outcome = "TIMEOUT" if _kill_event.is_set() else "FAIL"
        elif delta >= IMPROVE_THRESHOLD:
            outcome = "WIN"
        elif delta <= -IMPROVE_THRESHOLD:
            outcome = "LOSS"
        else:
            outcome = "NEUTRAL"

        overrides_str = " ".join(f"{k} {v}" for k, v in exp["overrides"].items())
        runs_str      = str(result["runs"]) if result else ""

        rows.append([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            exp["id"], exp["label"], overrides_str,
            med, mn, mx, delta, outcome, runs_str,
        ])

        done_ids.add(exp["id"])
        save_checkpoint({"done": list(done_ids), "rows": rows})
        write_results(rows)

    write_markdown(rows)
    restore_production()
    log("\nDone.")


if __name__ == "__main__":
    main()
