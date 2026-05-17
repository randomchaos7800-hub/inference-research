#!/usr/bin/env python3
"""
autoresearch-genesis-021.py — Genesis INT4 tuning on vLLM 0.21.0, dual RTX 5060 Ti

Baseline: Genesis INT4 MTP n=3, auto KV, ctx 65536, GMU 0.90 → ~69-70 t/s

Experiments:
  1. baseline          — confirm current config
  2. nvfp4_kv          — nvfp4 KV (new in 0.21.0, halves KV vs fp8, native Blackwell)
  3. fp8_kv            — fp8 KV (halves KV vs auto/bf16, frees VRAM for more blocks)
  4. mtp_n2            — MTP 2 speculative tokens (higher acceptance rate, less parallelism)
  5. mtp_n4            — MTP 4 speculative tokens (more parallelism, lower accept rate)
  6. mtp_n5            — MTP 5 (ceiling test — may OOM or crash)
  7. batched_8192      — max_num_batched_tokens 8192 (more throughput room)
  8. nccl_16mb         — NCCL_BUFFSIZE 16MB (was +1.06 t/s in pass2)
  9. gmu_092           — GMU 0.92 (more KV blocks)
  10. nvfp4_mtp4       — nvfp4 KV + MTP n=4 (best-case combo)

Run: python3 autoresearch-genesis-021.py
Results: /home/dino/inference-research/autoresearch-genesis-021-results.tsv
Log:     /home/dino/inference-research/autoresearch-genesis-021-log.md
"""

import csv, os, re, signal, subprocess, sys, tempfile, time
from datetime import datetime
from pathlib import Path
from statistics import median

# ── config ────────────────────────────────────────────────────────────────────

GENESIS_SCRIPT   = Path("/home/dino/bin/vllm-genesis-start.sh")
GENESIS_SERVICE  = "vllm-genesis"
RESULTS_TSV      = Path("/home/dino/inference-research/autoresearch-genesis-021-results.tsv")
LOG_MD           = Path("/home/dino/inference-research/autoresearch-genesis-021-log.md")
VLLM_PYTHON      = "/opt/ai/vllm-env/bin/python3"

PORT      = 8022
API_KEY   = "genesis-local"
MODEL     = "qwen3627b"
URL       = f"http://localhost:{PORT}/v1/completions"
HEALTH    = f"http://localhost:{PORT}/health"
HEADERS   = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

BENCH_TOKENS      = 512
N_WARMUP          = 2
N_BENCH           = 5
READY_TIMEOUT     = 480   # seconds
IMPROVE_THRESHOLD = 1.0   # t/s to call a win
CLEAN_VRAM_MIB    = 500   # both GPUs must be below this to consider GPU clean
GPU_DRAIN_TIMEOUT = 60

PROMPTS = [
    "Explain in technical detail how CUDA tensor cores accelerate matrix multiplication on Blackwell GPU architecture. Cover the hardware pipeline, NVFP4 vs FP8 precision handling, KV cache memory implications, and tensor parallel communication patterns.",
    "Describe the engineering challenges of running large language model inference at scale, covering batching strategies, KV cache management, quantization approaches, and tensor parallel communication patterns.",
    "Explain the architecture of a Retrieval Augmented Generation system, covering embedding models, vector databases, chunking strategies, hybrid search, reranking, and prompt construction for grounded generation.",
    "Describe how speculative decoding works to accelerate autoregressive inference, covering draft models, token verification, acceptance rates, and Multi-Token Prediction approaches in modern inference engines.",
    "Explain CUDA memory management for deep learning, covering cudaMalloc, memory pools, VRAM fragmentation, unified memory, and best practices for managing GPU memory in multi-GPU inference workloads.",
    "Describe how prefix caching works in LLM inference servers, covering KV cache reuse, hash-based cache lookup, cache eviction policies, and the throughput impact on production workloads.",
    "Explain the Mamba state space model architecture, covering selective state spaces, input-dependent transitions, parallel scan computation, and how SSMs compare to attention for long-context inference.",
]
PROMPT = PROMPTS[0]  # kept for compat; run_benchmark uses PROMPTS rotation

# ── experiments ───────────────────────────────────────────────────────────────

EXPERIMENTS = [
    {
        "id":    "baseline",
        "label": "Genesis baseline (INT4, auto KV, MTP n=3, GMU 0.90)",
        "flags": {},
        "env":   {},
    },
    {
        "id":    "nvfp4_kv",
        "label": "nvfp4 KV cache (vLLM 0.21.0 native Blackwell FP4)",
        "flags": {"--kv-cache-dtype": "nvfp4"},
        "env":   {},
    },
    {
        "id":    "fp8_kv",
        "label": "fp8 KV cache (halves KV footprint vs auto, more KV blocks)",
        "flags": {"--kv-cache-dtype": "fp8"},
        "env":   {},
    },
    {
        "id":    "mtp_n2",
        "label": "MTP 2 speculative tokens (higher accept rate)",
        "flags": {"--speculative-config": '\'{"method":"mtp","num_speculative_tokens":2}\''},
        "env":   {},
    },
    {
        "id":    "mtp_n4",
        "label": "MTP 4 speculative tokens (more parallelism)",
        "flags": {"--speculative-config": '\'{"method":"mtp","num_speculative_tokens":4}\''},
        "env":   {},
    },
    {
        "id":    "mtp_n5",
        "label": "MTP 5 speculative tokens (ceiling test)",
        "flags": {"--speculative-config": '\'{"method":"mtp","num_speculative_tokens":5}\''},
        "env":   {},
    },
    {
        "id":    "batched_8192",
        "label": "max_num_batched_tokens 8192 (more throughput headroom)",
        "flags": {"--max-num-batched-tokens": "8192"},
        "env":   {"GENESIS_PREALLOC_TOKEN_BUDGET": "8192"},
    },
    {
        "id":    "nccl_16mb",
        "label": "NCCL_BUFFSIZE 16MB (was +1.06 t/s in pass2)",
        "flags": {},
        "env":   {"NCCL_BUFFSIZE": "16777216"},
    },
    {
        "id":    "gmu_092",
        "label": "GMU 0.92 (more KV blocks, slightly more VRAM)",
        "flags": {"--gpu-memory-utilization": "0.92"},
        "env":   {},
    },
    {
        "id":    "nvfp4_mtp4",
        "label": "nvfp4 KV + MTP n=4 (best-case combo)",
        "flags": {
            "--kv-cache-dtype": "nvfp4",
            "--speculative-config": '\'{"method":"mtp","num_speculative_tokens":4}\'',
        },
        "env":   {},
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


def kill_gpu_procs():
    r = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
        capture_output=True, text=True
    )
    pids = [int(p.strip()) for p in r.stdout.strip().splitlines() if p.strip()]
    killed = []
    for pid in pids:
        try:
            with open(f"/proc/{pid}/cmdline") as f:
                cmd = f.read()
            if any(k in cmd for k in ["proxy.py", "harness.py", "frank", "mike", "kato"]):
                continue
            os.kill(pid, signal.SIGKILL)
            killed.append(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return killed


def wait_clean_gpu(timeout=GPU_DRAIN_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        free = gpu_free_mib()
        if all(f >= (16311 - CLEAN_VRAM_MIB) for f in free):
            log(f"  GPU clean: {free[0]}/{free[1]} MiB free")
            return True
        time.sleep(3)
    free = gpu_free_mib()
    log(f"  WARNING: GPU not fully clean after {timeout}s: {free}")
    return False


def kill_port_procs(port=PORT):
    """Kill any process listening on PORT (catches APIServer which has no GPU context)."""
    r = subprocess.run(["ss", "-tlnpH", f"sport = :{port}"],
                       capture_output=True, text=True)
    killed = []
    for line in r.stdout.strip().splitlines():
        # format: LISTEN 0 N *:PORT *:* users:(("vllm",pid=N,fd=M))
        import re as _re
        m = _re.search(r'pid=(\d+)', line)
        if m:
            pid = int(m.group(1))
            try:
                os.kill(pid, signal.SIGKILL)
                killed.append(pid)
            except (ProcessLookupError, PermissionError):
                pass
    if killed:
        log(f"  killed port-{port} procs: {killed}")
    return killed


def stop_service_and_clean():
    subprocess.run(["systemctl", "--user", "stop", f"{GENESIS_SERVICE}.service"],
                   check=False, capture_output=True)
    time.sleep(3)
    killed = kill_gpu_procs()
    kill_port_procs()
    if killed:
        log(f"  killed GPU procs: {killed}")
        time.sleep(5)
        kill_gpu_procs()
        kill_port_procs()
        time.sleep(3)
    wait_clean_gpu()


def make_test_script(exp):
    """Build a temp bash script from the genesis base with flag/env overrides."""
    content = GENESIS_SCRIPT.read_text()

    # Apply env overrides
    for key, val in exp["env"].items():
        pattern = rf'^(export {re.escape(key)}=).*$'
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, rf'\g<1>{val}', content, flags=re.MULTILINE)
        else:
            content = content.replace(
                "/opt/ai/vllm-env/bin/python3 -m vllm._genesis.patches.apply_all",
                f"export {key}={val}\n\n/opt/ai/vllm-env/bin/python3 -m vllm._genesis.patches.apply_all"
            )

    # Apply flag overrides
    for flag, value in exp["flags"].items():
        # Special handling for speculative-config (JSON, need careful replacement)
        escaped_flag = re.escape(flag)
        # Match --flag 'anything' or --flag anything on same line with trailing backslash
        pattern = rf"(  {escaped_flag} )('[^']*'|\S+)( \\)"
        if re.search(pattern, content):
            content = re.sub(pattern, rf"\g<1>{value}\g<3>", content)
        else:
            # Flag not present — inject before --disable-log-stats
            content = content.replace(
                "  --disable-log-stats",
                f"  {flag} {value} \\\n  --disable-log-stats"
            )

    tmp = tempfile.NamedTemporaryFile(
        suffix=".sh", delete=False, mode="w", prefix="/tmp/genesis-test-"
    )
    tmp.write(content)
    tmp.close()
    os.chmod(tmp.name, 0o755)
    return Path(tmp.name)


def port_owner_pid(port=PORT):
    """Return the PID listening on PORT, or None."""
    import re as _re
    r = subprocess.run(["ss", "-tlnpH", f"sport = :{port}"],
                       capture_output=True, text=True)
    for line in r.stdout.strip().splitlines():
        m = _re.search(r'pid=(\d+)', line)
        if m:
            return int(m.group(1))
    return None


def wait_ready(test_pgid, timeout=READY_TIMEOUT):
    """Wait until /health returns 200 AND port 8022 is owned by a process in test_pgid's group."""
    import urllib.request, urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            owner = port_owner_pid()
            if owner is not None:
                # Verify owner is in the test process group
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


def one_inference(prompt):
    import urllib.request, urllib.error, json
    body = json.dumps({
        "model": MODEL, "prompt": prompt,
        "max_tokens": BENCH_TOKENS, "temperature": 0, "stream": False
    }).encode()
    req = urllib.request.Request(URL, data=body, headers=HEADERS, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    elapsed = time.time() - t0
    ct = data["usage"]["completion_tokens"]
    return ct / elapsed


def run_benchmark():
    log(f"  warmup x{N_WARMUP}...")
    for i in range(N_WARMUP):
        try:
            tps = one_inference(PROMPTS[i % len(PROMPTS)])
            log(f"    warmup {i+1}: {tps:.2f} t/s")
        except Exception as e:
            log(f"    warmup {i+1} error: {e}")

    log(f"  bench x{N_BENCH}...")
    results = []
    for i in range(N_BENCH):
        try:
            tps = one_inference(PROMPTS[(N_WARMUP + i) % len(PROMPTS)])
            results.append(tps)
            log(f"    run {i+1}: {tps:.2f} t/s")
        except Exception as e:
            log(f"    run {i+1} ERROR: {e}")

    if not results:
        return None
    return {
        "median": round(median(results), 2),
        "min": round(min(results), 2),
        "max": round(max(results), 2),
        "runs": results,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def run_experiment(exp, baseline_tps):
    log(f"\n{'='*60}")
    log(f"EXPERIMENT: {exp['id']}")
    log(f"  {exp['label']}")

    stop_service_and_clean()

    script = make_test_script(exp)
    log(f"  script: {script}")

    # Apply genesis patches
    subprocess.run([VLLM_PYTHON, "-m", "vllm._genesis.patches.apply_all"],
                   capture_output=True, check=False)

    log("  starting genesis...")
    log_fh = open(f"/tmp/genesis-test-{exp['id']}.log", "w")
    proc = subprocess.Popen(
        ["/bin/bash", str(script)],
        stdout=log_fh, stderr=log_fh,
        preexec_fn=os.setsid
    )
    pgid = os.getpgid(proc.pid)
    log(f"  pid={proc.pid} pgid={pgid}")

    ready = wait_ready(test_pgid=pgid)
    if not ready:
        log("  FAIL: never became healthy")
        try:
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            pass
        kill_gpu_procs()
        log_fh.close()
        os.unlink(script)
        return None

    log(f"  ready at {datetime.now().strftime('%H:%M:%S')}")
    vram_free = gpu_free_mib()
    log(f"  VRAM free: {vram_free[0]}/{vram_free[1]} MiB")

    result = run_benchmark()

    # Shutdown
    log(f"  stopping pid={proc.pid}...")
    try:
        os.killpg(pgid, signal.SIGTERM)
        time.sleep(5)
        os.killpg(pgid, signal.SIGKILL)
    except Exception:
        pass
    kill_gpu_procs()
    time.sleep(5)
    kill_gpu_procs()
    log_fh.close()
    os.unlink(script)

    if result:
        delta = result["median"] - baseline_tps if baseline_tps else 0
        win = "WIN" if delta >= IMPROVE_THRESHOLD else ("LOSS" if delta <= -IMPROVE_THRESHOLD else "NEUTRAL")
        log(f"  RESULT: {result['median']:.2f} t/s  ({delta:+.2f} vs baseline)  [{win}]")
    else:
        log("  RESULT: FAILED")

    return result


def write_results(rows):
    with open(RESULTS_TSV, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["timestamp", "id", "label", "flags", "env", "median_tps",
                    "min_tps", "max_tps", "delta", "outcome", "runs"])
        for r in rows:
            w.writerow(r)
    log(f"TSV → {RESULTS_TSV}")


def write_markdown(rows):
    baseline_tps = next((r[5] for r in rows if r[1] == "baseline" and r[5]), None)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Genesis 0.21.0 Autoresearch — {now}",
        "",
        f"**Baseline:** {baseline_tps} t/s (INT4, auto KV, MTP n=3, GMU 0.90)",
        f"**Threshold:** ±{IMPROVE_THRESHOLD} t/s to call a win/loss",
        "",
        "## Results",
        "",
        "| ID | Label | Median t/s | Delta | Outcome |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        _, eid, label, flags, env, med, mn, mx, delta, outcome, _ = r
        med_str = f"{med:.2f}" if med else "FAIL"
        delta_str = f"{delta:+.2f}" if delta else "—"
        lines.append(f"| {eid} | {label} | {med_str} | {delta_str} | {outcome} |")

    wins = [r for r in rows if r[9] == "WIN"]
    lines += ["", "## Recommendation", ""]
    if wins:
        best = max(wins, key=lambda r: r[5] or 0)
        lines.append(f"**Deploy `{best[1]}`** — {best[5]:.2f} t/s ({best[8]:+.2f} vs baseline). Update genesis start script.")
    else:
        lines.append("No improvement found. Current config is optimal for this hardware+version.")

    lines += ["", "## Log", "", "```"]
    lines.extend(_log_lines)
    lines.append("```")
    LOG_MD.write_text("\n".join(lines) + "\n")
    log(f"Report → {LOG_MD}")


def restore_production():
    log("\nRestoring production genesis...")
    stop_service_and_clean()
    subprocess.run(["systemctl", "--user", "reset-failed", f"{GENESIS_SERVICE}.service"],
                   check=False, capture_output=True)
    subprocess.run(["systemctl", "--user", "start", f"{GENESIS_SERVICE}.service"], check=False)
    log("  waiting for production genesis...")
    ready = wait_ready(timeout=300)
    if ready:
        log("  production genesis healthy")
    else:
        log("  WARNING: production genesis did not come up — check manually")


def main():
    log(f"Genesis 0.21.0 autoresearch  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Base script: {GENESIS_SCRIPT}")
    log(f"Experiments: {len(EXPERIMENTS)}")

    rows = []
    baseline_tps = None

    for exp in EXPERIMENTS:
        result = run_experiment(exp, baseline_tps)

        med = result["median"] if result else None
        mn  = result["min"]    if result else None
        mx  = result["max"]    if result else None

        if exp["id"] == "baseline" and med:
            baseline_tps = med

        delta = round(med - baseline_tps, 2) if (med and baseline_tps) else None
        if delta is None:
            outcome = "FAIL"
        elif delta >= IMPROVE_THRESHOLD:
            outcome = "WIN"
        elif delta <= -IMPROVE_THRESHOLD:
            outcome = "LOSS"
        else:
            outcome = "NEUTRAL"

        flags_str = " ".join(f"{k} {v}" for k, v in exp["flags"].items())
        env_str   = " ".join(f"{k}={v}" for k, v in exp["env"].items())
        runs_str  = str(result["runs"]) if result else ""

        rows.append([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            exp["id"], exp["label"], flags_str, env_str,
            med, mn, mx, delta, outcome, runs_str
        ])

        write_results(rows)   # checkpoint after each experiment

    write_markdown(rows)
    restore_production()
    log("\nDone.")


if __name__ == "__main__":
    main()
