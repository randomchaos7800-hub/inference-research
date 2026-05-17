#!/usr/bin/env python3
"""
autoresearch-vllm021.py — vLLM v0.21.0 + new AEON model benchmark, dual RTX 5060 Ti

Hypotheses:
  A) v0.21.0 NVFP4 KV cache improves AEON t/s vs fp8 KV baseline
  B) New AEON Text-NVFP4-MTP (AEON-7 HuggingFace, stripped vision tower) fits better
     on 2x16GB TP=2 (20GB / 2 = ~10GB/GPU vs current MTP-XS ~11GB/GPU) and may win
     on long-context throughput due to more BF16 in linear_attn projections

Baseline: Genesis (INT4 GPTQ, auto KV, ctx 65536) ~80 t/s
          AEON MTP-XS (NVFP4, fp8 KV, ctx 122880) ~69 t/s

Experiments:
  1. genesis_baseline        — live Genesis, confirm ~80 t/s (no restart)
  2. aeon_mtp_xs_baseline    — AEON MTP-XS fp8 KV baseline, confirm ~69 t/s
  3. aeon_mtp_xs_nvfp4_kv    — AEON MTP-XS + nvfp4 KV (v0.21.0 new flag)
  4. aeon_mtp_xs_ctx163k     — AEON MTP-XS + nvfp4 KV + 163840 ctx
  5. aeon_text_mtp            — New AEON Text-NVFP4-MTP (fp8 KV, no vision tower)
  6. aeon_text_mtp_nvfp4_kv  — New AEON Text-NVFP4-MTP + nvfp4 KV (v0.21.0)
  7. genesis_regression       — Genesis same config (post-upgrade regression check)

Model: AEON-7/Qwen3.6-27B-AEON-Ultimate-Uncensored-Text-NVFP4-MTP (HuggingFace)
  Download first: huggingface-cli download AEON-7/Qwen3.6-27B-AEON-Ultimate-Uncensored-Text-NVFP4-MTP
  or set TEXT_MTP_MODEL to its local path.

Run on cha0tiktower. Takes ~60-90 min total (model loads ~8 min each).
"""

import os, sys, re, time, json, csv, subprocess, requests, tempfile, stat
from datetime import datetime
from pathlib import Path
from statistics import median

# ── Paths ─────────────────────────────────────────────────────────────────────

VLLM_BIN        = "/opt/ai/vllm-env/bin/vllm"
VLLM_PYTHON     = "/opt/ai/vllm-env/bin/python3"
GENESIS_SCRIPT  = Path("/home/dino/bin/vllm-genesis-start.sh")
AEON_SCRIPT     = Path("/home/dino/bin/vllm-aeon-nvfp4-start.sh")
RESULTS_TSV     = Path("/home/dino/inference-research/autoresearch-vllm021-results.tsv")
LOG_MD          = Path("/home/dino/inference-research/autoresearch-vllm021-log.md")

GENESIS_SERVICE  = "vllm-backend"
AEON_SERVICE     = "vllm-aeon"

# New AEON Text-NVFP4-MTP model path — set before running if downloaded
TEXT_MTP_MODEL = Path("/home/dino/models/Qwen3.6-27B-AEON-Ultimate-Uncensored-Text-NVFP4-MTP")

# ── Bench config ──────────────────────────────────────────────────────────────

BENCH_TOKENS      = 512   # completion tokens per run
N_BENCH_RUNS      = 5     # benchmark runs per experiment
N_WARMUP_RUNS     = 2     # warmup runs (discarded)
SERVICE_TIMEOUT   = 480   # seconds to wait for vllm ready
IMPROVE_THRESHOLD = 1.0   # t/s delta to call a result a win

BENCH_PROMPT = (
    "Explain in technical detail how CUDA tensor cores accelerate matrix multiplication "
    "on Blackwell GPU architecture. Cover the hardware pipeline, NVFP4 vs FP8 precision "
    "handling, KV cache memory implications, and tensor parallel communication patterns."
)

# ── Experiments ───────────────────────────────────────────────────────────────

EXPERIMENTS = [
    {
        "id":          "genesis_baseline",
        "label":       "Genesis baseline (INT4 GPTQ, auto KV, ctx 65536)",
        "base_script": GENESIS_SCRIPT,
        "service":     GENESIS_SERVICE,
        "port":        8022,
        "api_key":     "genesis-local",
        "model":       "qwen3627b",
        "overrides":   {},
        "use_live":    True,   # don't restart if already running
    },
    {
        "id":          "aeon_mtp_xs_baseline",
        "label":       "AEON MTP-XS baseline (NVFP4, fp8 KV, ctx 122880)",
        "base_script": AEON_SCRIPT,
        "service":     AEON_SERVICE,
        "port":        8023,
        "api_key":     "genesis-local",
        "model":       "aeon-nvfp4",
        "overrides":   {},
        "use_live":    False,
    },
    {
        "id":          "aeon_mtp_xs_nvfp4_kv",
        "label":       "AEON MTP-XS + nvfp4 KV (v0.21.0 new flag)",
        "base_script": AEON_SCRIPT,
        "service":     AEON_SERVICE,
        "port":        8023,
        "api_key":     "genesis-local",
        "model":       "aeon-nvfp4",
        "overrides":   {"--kv-cache-dtype": "nvfp4"},
        "use_live":    False,
    },
    {
        "id":          "aeon_mtp_xs_ctx163k",
        "label":       "AEON MTP-XS + nvfp4 KV + 163840 ctx (was OOM at 131K with fp8)",
        "base_script": AEON_SCRIPT,
        "service":     AEON_SERVICE,
        "port":        8023,
        "api_key":     "genesis-local",
        "model":       "aeon-nvfp4",
        "overrides":   {"--kv-cache-dtype": "nvfp4", "--max-model-len": "163840"},
        "use_live":    False,
    },
    {
        # Requires: huggingface-cli download AEON-7/Qwen3.6-27B-AEON-Ultimate-Uncensored-Text-NVFP4-MTP
        # New from AEON-7 — strips vision tower (20GB total / 2 GPUs = ~10GB/GPU)
        # More BF16 in linear_attn projections → better long-ctx quality than MTP-XS
        "id":          "aeon_text_mtp",
        "label":       "NEW: AEON Text-NVFP4-MTP (no vision, fp8 KV, ctx 122880)",
        "base_script": AEON_SCRIPT,
        "service":     AEON_SERVICE,
        "port":        8023,
        "api_key":     "genesis-local",
        "model":       "aeon-nvfp4",
        "overrides":   {"AEON_MODEL_PATH": str(TEXT_MTP_MODEL)},
        "use_live":    False,
        "model_path":  TEXT_MTP_MODEL,  # checked before running
    },
    {
        "id":          "aeon_text_mtp_nvfp4_kv",
        "label":       "NEW: AEON Text-NVFP4-MTP + nvfp4 KV (v0.21.0)",
        "base_script": AEON_SCRIPT,
        "service":     AEON_SERVICE,
        "port":        8023,
        "api_key":     "genesis-local",
        "model":       "aeon-nvfp4",
        "overrides":   {"AEON_MODEL_PATH": str(TEXT_MTP_MODEL), "--kv-cache-dtype": "nvfp4"},
        "use_live":    False,
        "model_path":  TEXT_MTP_MODEL,
    },
    {
        "id":          "genesis_regression",
        "label":       "Genesis regression check (same config, post-upgrade)",
        "base_script": GENESIS_SCRIPT,
        "service":     GENESIS_SERVICE,
        "port":        8022,
        "api_key":     "genesis-local",
        "model":       "qwen3627b",
        "overrides":   {},
        "use_live":    False,
    },
]

# ── Service helpers ───────────────────────────────────────────────────────────

def svc_status(name):
    r = subprocess.run(
        ["systemctl", "--user", "is-active", f"{name}.service"],
        capture_output=True, text=True
    )
    return r.stdout.strip()


def svc_stop(name):
    log(f"  stopping {name}.service …")
    subprocess.run(["systemctl", "--user", "stop", f"{name}.service"], check=False)
    # wait up to 30s for it to die
    for _ in range(30):
        if svc_status(name) != "active":
            break
        time.sleep(1)
    log(f"  {name}.service stopped")


def svc_start(name):
    log(f"  starting {name}.service …")
    subprocess.run(["systemctl", "--user", "start", f"{name}.service"], check=False)


def apply_genesis_patches():
    subprocess.run(
        [VLLM_PYTHON, "-m", "vllm._genesis.patches.apply_all"],
        check=False, capture_output=True
    )


def make_test_script(base_script: Path, overrides: dict) -> Path:
    """Return a temp script with flag overrides applied.

    Special override key AEON_MODEL_PATH swaps the model path in the
    vllm serve command (first positional arg after 'serve').
    """
    content = base_script.read_text()

    model_path_override = overrides.pop("AEON_MODEL_PATH", None)
    if model_path_override:
        # Replace the model path line: the line after 'exec ... vllm serve \'
        content = re.sub(
            r'(exec\s+\S+\s+serve\s+)\S+',
            rf'\g<1>{model_path_override}',
            content
        )

    for flag, value in overrides.items():
        pattern = rf'({re.escape(flag)}\s+)\S+'
        if re.search(pattern, content):
            content = re.sub(pattern, rf'\g<1>{value}', content)
        else:
            content = content.replace(
                "  --disable-log-stats",
                f"  {flag} {value} \\\n  --disable-log-stats"
            )

    tmp = tempfile.NamedTemporaryFile(
        suffix=".sh", delete=False, mode="w", prefix="/tmp/vllm-test-"
    )
    tmp.write(content)
    tmp.close()
    os.chmod(tmp.name, stat.S_IRWXU)
    return Path(tmp.name)


def wait_for_ready(port, api_key, timeout=SERVICE_TIMEOUT):
    url = f"http://localhost:{port}/health"
    deadline = time.time() + timeout
    log(f"  waiting for port {port} ready (up to {timeout}s) …")
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                log(f"  port {port} ready")
                return True
        except Exception:
            pass
        time.sleep(5)
    log(f"  ERROR: port {port} not ready after {timeout}s")
    return False


def get_vllm_version():
    r = subprocess.run(
        [VLLM_PYTHON, "-c", "import vllm; print(vllm.__version__)"],
        capture_output=True, text=True
    )
    return r.stdout.strip() or "unknown"

# ── Benchmark ─────────────────────────────────────────────────────────────────

def one_completion(port, api_key, model, n_tokens):
    t0 = time.time()
    resp = requests.post(
        f"http://localhost:{port}/v1/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "prompt": BENCH_PROMPT,
            "max_tokens": n_tokens,
            "temperature": 0.0,
            "stream": False,
        },
        timeout=300,
    )
    elapsed = time.time() - t0
    data = resp.json()
    completion_tokens = data["usage"]["completion_tokens"]
    return completion_tokens / elapsed


def benchmark(port, api_key, model):
    log(f"  warmup ({N_WARMUP_RUNS} runs) …")
    for _ in range(N_WARMUP_RUNS):
        try:
            one_completion(port, api_key, model, BENCH_TOKENS)
        except Exception as e:
            log(f"  warmup error: {e}")

    log(f"  benchmarking ({N_BENCH_RUNS} runs × {BENCH_TOKENS} tokens) …")
    results = []
    for i in range(N_BENCH_RUNS):
        try:
            tps = one_completion(port, api_key, model, BENCH_TOKENS)
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

# ── Logging ───────────────────────────────────────────────────────────────────

_log_lines = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    _log_lines.append(line)


def write_results(rows):
    with open(RESULTS_TSV, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow([
            "timestamp", "experiment", "label", "vllm_version",
            "overrides", "median_tps", "min_tps", "max_tps", "runs"
        ])
        for row in rows:
            writer.writerow(row)
    log(f"results → {RESULTS_TSV}")


def write_markdown(rows, genesis_baseline, aeon_baseline):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# vLLM v0.21.0 Autoresearch — {now}",
        "",
        "## Hardware",
        "2x RTX 5060 Ti 16GB GDDR7, Blackwell SM_120, Core Ultra 7 265F",
        "",
        "## Results",
        "",
        "| Experiment | Overrides | Median t/s | vs Genesis | vs AEON fp8 | Result |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        _, exp_id, label, vllm_ver, overrides_str, med, mn, mx, _ = r
        if genesis_baseline and med:
            delta_g = f"{med - genesis_baseline:+.2f}"
        else:
            delta_g = "—"
        if aeon_baseline and med and exp_id != "genesis_baseline" and exp_id != "genesis_regression":
            delta_a = f"{med - aeon_baseline:+.2f}"
        else:
            delta_a = "—"
        win = ""
        if med and genesis_baseline and med > genesis_baseline + IMPROVE_THRESHOLD:
            win = "✅ BEATS GENESIS"
        elif med and aeon_baseline and med > aeon_baseline + IMPROVE_THRESHOLD and "aeon" in exp_id:
            win = "✅ WIN"
        elif med and aeon_baseline and med < aeon_baseline - IMPROVE_THRESHOLD and "aeon" in exp_id:
            win = "❌ REGRESSION"
        elif med and genesis_baseline and med < genesis_baseline - IMPROVE_THRESHOLD and "genesis" in exp_id:
            win = "❌ REGRESSION"
        lines.append(
            f"| {exp_id} | `{overrides_str or 'baseline'}` | {med or 'FAIL'} | {delta_g} | {delta_a} | {win} |"
        )

    lines += [
        "",
        "## Recommendation",
        "",
    ]

    # Find best AEON result
    aeon_results = [(r[4], r[0], r[2]) for r in rows if "aeon" in r[0] and r[4]]
    if aeon_results:
        best_tps, best_id, best_ver = max(aeon_results, key=lambda x: x[0])
        if genesis_baseline and best_tps > genesis_baseline + IMPROVE_THRESHOLD:
            lines.append(f"**Switch to {best_id}** — beats genesis by {best_tps - genesis_baseline:+.2f} t/s. Update proxy active=.")
        elif aeon_baseline and best_tps > aeon_baseline + IMPROVE_THRESHOLD:
            lines.append(f"**{best_id}** improves AEON by {best_tps - aeon_baseline:+.2f} t/s. Genesis still faster but AEON gap narrowed.")
        else:
            lines.append("No AEON variant beat genesis. Stay on Genesis.")

    lines += ["", "## Log", "", "```"]
    lines.extend(_log_lines)
    lines.append("```")

    LOG_MD.write_text("\n".join(lines) + "\n")
    log(f"report → {LOG_MD}")

# ── Main ──────────────────────────────────────────────────────────────────────

def run_experiment(exp, vllm_version):
    log(f"\n{'='*60}")
    log(f"EXPERIMENT: {exp['id']}")
    log(f"  {exp['label']}")
    log(f"  vLLM: {vllm_version}")

    # Skip if required model not downloaded
    if "model_path" in exp and not exp["model_path"].exists():
        log(f"  SKIP: model not found at {exp['model_path']}")
        log(f"  Download: huggingface-cli download AEON-7/Qwen3.6-27B-AEON-Ultimate-Uncensored-Text-NVFP4-MTP --local-dir {exp['model_path']}")
        return None

    port    = exp["port"]
    api_key = exp["api_key"]
    model   = exp["model"]
    service = exp["service"]

    currently_running = svc_status(service) == "active"

    if exp["use_live"] and currently_running:
        log("  using live service (no restart)")
        result = benchmark(port, api_key, model)
    else:
        # Stop whatever is on this port
        if currently_running:
            svc_stop(service)

        # Also stop genesis if we're switching to aeon (both need GPU)
        if service == AEON_SERVICE and svc_status(GENESIS_SERVICE) == "active":
            svc_stop(GENESIS_SERVICE)
        if service == GENESIS_SERVICE and svc_status(AEON_SERVICE) == "active":
            svc_stop(AEON_SERVICE)

        time.sleep(10)  # let GPU memory drain

        apply_genesis_patches()

        if exp["overrides"]:
            script = make_test_script(exp["base_script"], exp["overrides"])
            log(f"  test script: {script}")
        else:
            script = exp["base_script"]

        log(f"  launching: bash {script}")
        proc = subprocess.Popen(
            ["bash", str(script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        log(f"  pid: {proc.pid}")

        ready = wait_for_ready(port, api_key)
        if not ready:
            log("  SKIP: service failed to start")
            proc.terminate()
            if exp["overrides"] and script != exp["base_script"]:
                os.unlink(script)
            return None

        result = benchmark(port, api_key, model)

        log(f"  killing test instance pid={proc.pid}")
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()

        if exp["overrides"] and str(script).startswith("/tmp/"):
            os.unlink(script)

        time.sleep(5)

    if result:
        log(f"  RESULT: median={result['median']} t/s  min={result['min']}  max={result['max']}")
    else:
        log("  RESULT: FAILED")

    return result


def main():
    log(f"autoresearch-vllm021  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    vllm_version = get_vllm_version()
    log(f"vLLM version: {vllm_version}")

    if not Path(VLLM_BIN).exists():
        print(f"FATAL: vllm not found at {VLLM_BIN}", file=sys.stderr)
        sys.exit(1)

    rows = []
    genesis_baseline = None
    aeon_baseline    = None

    for exp in EXPERIMENTS:
        result = run_experiment(exp, vllm_version)

        med = result["median"] if result else None
        mn  = result["min"]    if result else None
        mx  = result["max"]    if result else None
        runs = str(result["runs"]) if result else ""

        overrides_str = " ".join(f"{k} {v}" for k, v in exp["overrides"].items())
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            exp["id"],
            exp["label"],
            vllm_version,
            overrides_str,
            med, mn, mx, runs,
        ]
        rows.append(row)

        if exp["id"] == "genesis_baseline" and med:
            genesis_baseline = med
        if exp["id"] == "aeon_mtp_xs_baseline" and med:
            aeon_baseline = med

    # restore genesis as the default
    log("\nRestoring genesis service …")
    if svc_status(AEON_SERVICE) == "active":
        svc_stop(AEON_SERVICE)
    if svc_status(GENESIS_SERVICE) != "active":
        svc_start(GENESIS_SERVICE)
        wait_for_ready(8022, "genesis-local", timeout=300)

    write_results(rows)
    write_markdown(rows, genesis_baseline, aeon_baseline)

    log("\nDone.")
    log(f"  TSV: {RESULTS_TSV}")
    log(f"  Report: {LOG_MD}")


if __name__ == "__main__":
    main()
