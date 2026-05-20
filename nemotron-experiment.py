#!/usr/bin/env python3
"""
Nemotron 3 Nano 30B — Format Shootout + Autoresearch
Candidates: Q4_K_M (llama.cpp), Q5_K_M (llama.cpp), FP8 (vllm TP=2)
Crowns winner, then runs autoresearch parameter sweep on winner.
Log: /tmp/nemotron-experiment.log
Results: /home/dino/inference-research/nemotron-shootout-results.md
"""

import json, os, re, statistics, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────
LLAMA_BIN  = "/home/dino/llama.cpp/build-cuda13/bin/llama-server"
LLAMA_LIB  = "/home/dino/llama.cpp/build-cuda13/bin"
MODEL_Q4   = "/home/dino/models/Nemotron-3-Nano-30B-A3B/nvidia_Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf"
MODEL_Q5   = "/home/dino/models/Nemotron-3-Nano-30B-A3B/nvidia_Nemotron-3-Nano-30B-A3B-Q5_K_M.gguf"
MODEL_FP8  = "/home/dino/models/Nemotron-3-Nano-30B-A3B-FP8"
VLLM_BIN   = "/opt/ai/vllm-test-env/bin/python"
PORT       = 8022
LOG_FILE   = "/tmp/nemotron-experiment.log"
RESULTS_MD = "/home/dino/inference-research/nemotron-shootout-results.md"
WINNER_SH  = "/tmp/nemotron-start.sh"

PROMPT     = ("Explain distributed systems design principles and the CAP theorem "
              "tradeoffs. What should architects prioritize for high-availability services?")
MAX_TOKENS = 200
WARMUP     = 5
BENCH      = 15

# ── Logging ──────────────────────────────────────────────────────────────────
def ts():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── GPU / server helpers ─────────────────────────────────────────────────────
def gpu_free():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True)
    return [int(x.strip()) for x in r.stdout.strip().split("\n") if x.strip()]

def wait_gpu_clean(threshold=14000, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        free = gpu_free()
        if all(f > threshold for f in free):
            log(f"  GPU clean: {free} MiB free")
            return True
        time.sleep(4)
    log(f"  WARNING: GPU not clean after {timeout}s: {gpu_free()}")
    return False

def kill_servers():
    subprocess.run(["pkill", "-f", "llama-server"], capture_output=True)
    subprocess.run(["pkill", "-f", "vllm.entrypoints"], capture_output=True)
    time.sleep(4)

def wait_server(timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{PORT}/health", timeout=3)
            return True
        except:
            time.sleep(3)
    return False

def run_one():
    payload = json.dumps({
        "prompt": PROMPT, "max_tokens": MAX_TOKENS, "temperature": 0.7
    }).encode()
    t0 = time.time()
    try:
        req = urllib.request.Request(
            f"http://localhost:{PORT}/v1/completions",
            data=payload,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        elapsed = time.time() - t0
        toks = data.get("usage", {}).get("completion_tokens", 0)
        if toks > 0:
            return toks / elapsed
    except Exception as e:
        log(f"    request error: {e}")
    return None

def bench(label):
    log(f"  warmup ({WARMUP} runs)...")
    for i in range(WARMUP):
        r = run_one()
        log(f"    warmup {i+1}: {r:.2f} t/s" if r else f"    warmup {i+1}: FAIL")

    log(f"  bench ({BENCH} runs)...")
    results = []
    for i in range(BENCH):
        r = run_one()
        if r:
            results.append(r)
            log(f"    run {i+1}: {r:.2f} t/s")
        else:
            log(f"    run {i+1}: FAIL")

    if not results:
        log("  ALL RUNS FAILED")
        return None
    med  = statistics.median(results)
    peak = max(results)
    low  = min(results)
    log(f"  RESULT: median={med:.2f}  peak={peak:.2f}  min={low:.2f}  n={len(results)}")
    return {"median": med, "peak": peak, "min": low, "runs": results}

# ── Download wait ─────────────────────────────────────────────────────────────
def wait_for_downloads():
    log("=" * 60)
    log("Waiting for downloads...")
    while True:
        q4_ok = Path(MODEL_Q4).exists() and Path(MODEL_Q4).stat().st_size > 20_000_000_000
        q5_ok = Path(MODEL_Q5).exists() and Path(MODEL_Q5).stat().st_size > 22_000_000_000

        fp8_index = Path(MODEL_FP8) / "model.safetensors.index.json"
        if fp8_index.exists():
            try:
                idx = json.loads(fp8_index.read_text())
                shards = set(idx.get("weight_map", {}).values())
                fp8_ok = bool(shards) and all(
                    (Path(MODEL_FP8) / s).exists() and
                    (Path(MODEL_FP8) / s).stat().st_size > 1_000_000
                    for s in shards)
            except Exception:
                fp8_ok = False
        else:
            fp8_ok = False

        status = (f"  Q4_K_M: {'✓' if q4_ok else 'downloading'} | "
                  f"Q5_K_M: {'✓' if q5_ok else 'downloading'} | "
                  f"FP8: {'✓' if fp8_ok else 'downloading'}")
        log(status)
        if q4_ok and q5_ok and fp8_ok:
            log("All downloads complete.")
            return
        time.sleep(60)

# ── Experiment runners ────────────────────────────────────────────────────────
def run_llamacpp(model_path, label, extra_flags=None):
    log("=" * 60)
    log(f"EXP: {label}")
    kill_servers()
    wait_gpu_clean()

    flags = [
        LLAMA_BIN,
        "--model", model_path,
        "--host", "0.0.0.0", "--port", str(PORT),
        "--n-gpu-layers", "999",
        "--ctx-size", "32768",
        "--threads", "8",
    ]
    if extra_flags:
        flags.extend(extra_flags)

    log(f"  flags: {' '.join(flags[flags.index('--ctx-size'):][:12])}")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = LLAMA_LIB

    server_log = f"/tmp/nemotron-{label}.log"
    proc = subprocess.Popen(flags, env=env,
                            stdout=open(server_log, "w"),
                            stderr=subprocess.STDOUT)
    if not wait_server(timeout=120):
        log("  FAIL: server did not come up (assertion bug?)")
        proc.terminate()
        proc.wait()
        return None

    log("  server ready")
    result = bench(label)
    proc.terminate()
    proc.wait()
    return result

def run_vllm_fp8(label, extra_flags=None):
    log("=" * 60)
    log(f"EXP: {label} (vllm FP8 TP=2)")
    kill_servers()
    wait_gpu_clean()

    cmd = [
        VLLM_BIN, "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL_FP8,
        "--tensor-parallel-size", "2",
        "--trust-remote-code",
        "--max-model-len", "32768",
        "--port", str(PORT),
        "--disable-log-requests",
    ]
    if extra_flags:
        cmd.extend(extra_flags)

    log(f"  cmd: {' '.join(cmd[3:])}")
    env = os.environ.copy()
    env["VLLM_USE_FLASHINFER_MOE_FP8"] = "1"
    env["VLLM_FLASHINFER_MOE_BACKEND"] = "throughput"

    server_log = f"/tmp/nemotron-{label}.log"
    proc = subprocess.Popen(cmd, env=env,
                            stdout=open(server_log, "w"),
                            stderr=subprocess.STDOUT)
    if not wait_server(timeout=360):
        log("  FAIL: vllm server did not come up")
        proc.terminate()
        proc.wait()
        return None

    log("  vllm server ready")
    result = bench(label)
    proc.terminate()
    proc.wait()
    return result

# ── Autoresearch ──────────────────────────────────────────────────────────────
def autoresearch_llamacpp(model_path, model_label, baseline):
    log("=" * 60)
    log(f"AUTORESEARCH: {model_label} — llama.cpp parameter sweep")

    experiments = [
        ("ctx_16k",      ["--ctx-size", "16384"]),
        ("ctx_64k",      ["--ctx-size", "65536"]),
        ("threads_4",    ["--threads", "4"]),
        ("threads_16",   ["--threads", "16"]),
        ("kv_q8",        ["--cache-type-k", "q8_0", "--cache-type-v", "q8_0"]),
        ("kv_q4",        ["--cache-type-k", "q4_0", "--cache-type-v", "q4_0"]),
        ("ubatch_2048",  ["--ubatch-size", "2048"]),
        ("batch_8192",   ["--batch-size", "8192", "--ubatch-size", "2048"]),
        ("flash_attn",   ["--flash-attn"]),
        ("kv_q8_b8192",  ["--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
                           "--batch-size", "8192", "--ubatch-size", "2048"]),
    ]

    results = {"baseline": baseline}
    for name, flags in experiments:
        r = run_llamacpp(model_path, f"ar_{name}", flags)
        results[name] = r
        time.sleep(3)

    return results

def autoresearch_vllm(baseline):
    log("=" * 60)
    log("AUTORESEARCH: FP8 vllm parameter sweep")

    experiments = [
        ("gpu_util_90",    ["--gpu-memory-utilization", "0.90"]),
        ("gpu_util_98",    ["--gpu-memory-utilization", "0.98"]),
        ("eager",          ["--enforce-eager"]),
        ("max_seq_4",      ["--max-num-seqs", "4"]),
        ("ctx_16k",        ["--max-model-len", "16384"]),
    ]

    results = {"baseline": baseline}
    for name, flags in experiments:
        r = run_vllm_fp8(f"ar_{name}", extra_flags=flags)
        results[name] = r
        time.sleep(3)

    return results

# ── Results writer ────────────────────────────────────────────────────────────
def write_results(shootout, winner_name, ar_results, ar_winner_name):
    lines = [
        "# Nemotron 3 Nano 30B — Shootout Results\n",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n",
        "## Format Shootout\n\n",
        "| Model | Median t/s | Peak t/s | Min t/s |\n",
        "|---|---|---|---|\n",
    ]
    ranked = sorted(
        [(k, v) for k, v in shootout.items() if v],
        key=lambda x: x[1]["median"], reverse=True)
    for name, r in ranked:
        marker = " ← WINNER" if name == winner_name else ""
        lines.append(f"| {name}{marker} | {r['median']:.2f} | {r['peak']:.2f} | {r['min']:.2f} |\n")
    if any(v is None for v in shootout.values()):
        lines.append("\n*Failed experiments: " +
                     ", ".join(k for k, v in shootout.items() if v is None) + "*\n")

    lines.append(f"\n**Winner: {winner_name}**\n\n")
    lines.append("## Autoresearch Results\n\n")
    lines.append("| Experiment | Median t/s | Δ vs baseline |\n")
    lines.append("|---|---|---|\n")

    baseline_med = ar_results.get("baseline", {})
    if baseline_med:
        base = baseline_med["median"]
    else:
        base = 0

    ar_ranked = sorted(
        [(k, v) for k, v in ar_results.items() if v],
        key=lambda x: x[1]["median"], reverse=True)
    for name, r in ar_ranked:
        delta = r["median"] - base
        marker = " ← WINNER" if name == ar_winner_name else ""
        lines.append(f"| {name}{marker} | {r['median']:.2f} | {delta:+.2f} |\n")

    lines.append(f"\n**Autoresearch winner: {ar_winner_name}**\n")
    lines.append("\n---\n_nemotron-experiment complete_\n")

    Path(RESULTS_MD).write_text("".join(lines))
    log(f"Results written: {RESULTS_MD}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs("/home/dino/inference-research", exist_ok=True)
    Path(LOG_FILE).write_text("")  # fresh log
    log("nemotron-experiment start")

    wait_for_downloads()

    # ── Shootout ──
    shootout = {}
    shootout["Q4_K_M (llama.cpp)"] = run_llamacpp(MODEL_Q4, "Q4_K_M")
    shootout["Q5_K_M (llama.cpp)"] = run_llamacpp(MODEL_Q5, "Q5_K_M")
    shootout["FP8 (vllm TP=2)"]    = run_vllm_fp8("FP8_vllm")

    log("=" * 60)
    log("SHOOTOUT FINAL STANDINGS")
    valid = {k: v for k, v in shootout.items() if v}
    if not valid:
        log("ALL EXPERIMENTS FAILED — check individual logs in /tmp/nemotron-*.log")
        sys.exit(1)

    ranked = sorted(valid.items(), key=lambda x: x[1]["median"], reverse=True)
    for name, r in ranked:
        log(f"  {name}: {r['median']:.2f} t/s median, {r['peak']:.2f} peak")

    winner_name   = ranked[0][0]
    winner_result = ranked[0][1]
    log(f"\nWINNER: {winner_name} — {winner_result['median']:.2f} t/s")

    # ── Autoresearch on winner ──
    if "vllm" in winner_name:
        ar_results = autoresearch_vllm(winner_result)
        ar_model   = "vllm FP8"
    elif "Q4" in winner_name:
        ar_results = autoresearch_llamacpp(MODEL_Q4, "Q4_K_M", winner_result)
        ar_model   = "Q4_K_M llama.cpp"
    else:
        ar_results = autoresearch_llamacpp(MODEL_Q5, "Q5_K_M", winner_result)
        ar_model   = "Q5_K_M llama.cpp"

    ar_valid  = {k: v for k, v in ar_results.items() if v}
    ar_ranked = sorted(ar_valid.items(), key=lambda x: x[1]["median"], reverse=True)

    log("=" * 60)
    log("AUTORESEARCH FINAL STANDINGS")
    for name, r in ar_ranked:
        delta = r["median"] - winner_result["median"]
        log(f"  {name}: {r['median']:.2f} t/s ({delta:+.2f})")

    ar_winner_name   = ar_ranked[0][0]
    ar_winner_result = ar_ranked[0][1]
    log(f"\nAUTORESEARCH WINNER: {ar_winner_name} — {ar_winner_result['median']:.2f} t/s")

    # ── Write winner start script ──
    if "vllm" not in winner_name:
        model_path = MODEL_Q4 if "Q4" in winner_name else MODEL_Q5
        # Reconstruct flags for ar winner
        ar_flag_map = {
            "baseline":     [],
            "ctx_16k":      ["--ctx-size", "16384"],
            "ctx_64k":      ["--ctx-size", "65536"],
            "threads_4":    ["--threads", "4"],
            "threads_16":   ["--threads", "16"],
            "kv_q8":        ["--cache-type-k", "q8_0", "--cache-type-v", "q8_0"],
            "kv_q4":        ["--cache-type-k", "q4_0", "--cache-type-v", "q4_0"],
            "ubatch_2048":  ["--ubatch-size", "2048"],
            "batch_8192":   ["--batch-size", "8192", "--ubatch-size", "2048"],
            "flash_attn":   ["--flash-attn"],
            "kv_q8_b8192":  ["--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
                              "--batch-size", "8192", "--ubatch-size", "2048"],
        }
        extra = ar_flag_map.get(ar_winner_name, [])
        base_flags = ["--n-gpu-layers", "999", "--ctx-size", "32768", "--threads", "8"]
        all_flags  = base_flags + extra
        flag_str   = " \\\n  ".join(
            f"{all_flags[i]} {all_flags[i+1]}" if not all_flags[i].startswith("--flash") else all_flags[i]
            for i in range(0, len(all_flags), 2) if i < len(all_flags))
        sh = (f"#!/bin/bash\nexport LD_LIBRARY_PATH={LLAMA_LIB}\n"
              f"exec {LLAMA_BIN} \\\n"
              f"  --model {model_path} \\\n"
              f"  --host 0.0.0.0 --port {PORT} \\\n"
              f"  {flag_str}\n")
        Path(WINNER_SH).write_text(sh)
        subprocess.run(["chmod", "+x", WINNER_SH])
        log(f"Winner start script: {WINNER_SH}")

    write_results(shootout, winner_name, ar_results, ar_winner_name)

    log("")
    log("nemotron-experiment complete")

if __name__ == "__main__":
    main()
