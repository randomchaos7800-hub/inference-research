#!/usr/bin/env python3
"""
Karpathy-style autoresearch loop for GLM-4.7-Flash dual-GPU inference optimization.
Improvements over v1:
  - LLM reads full results history (name + delta + outcome) each iteration
  - program.md for human-steerable research direction
  - Scores clamped to binary 0/1 (model often returns 0-10 scale)
  - LLM waits for prod server healthy before generating next seed
  - results.tsv structured log alongside markdown log
"""

import json
import subprocess
import time
import sys
import os
import requests
import csv
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASELINE = {
    "gen_tps": 95.9,
    "prompt_tps": 149.7,
    "n_gpu_layers": 999,
    "tensor_split": "1,1",
    "ctx_size": 65536,
    "ctk": "q4_0",
    "ctv": "q4_0",
    "ubatch_size": 1024,
    "threads": 8,
    "threads_batch": 8,
    "cpu_range": "0-7",
    "mlock": True,
    "flash_attn": True,
}

MODEL_PATH   = "/home/dino/models/GLM-4.7-Flash-Q5_K_M.gguf"
SERVER_BIN   = "/home/dino/llama.cpp/build/bin/llama-server"
PROGRAM_MD   = Path("/home/dino/inference-research/program-glm47.md")
TEST_PORT    = 8090
PROD_PORT    = 8081
MAX_ITERS    = 10
SCORE_GATE   = 5
LOG_FILE     = Path("/home/dino/inference-research/autoresearch-glm47-log.md")
RESULTS_TSV  = Path("/home/dino/inference-research/autoresearch-glm47-results.tsv")
ENV          = {**os.environ, "PATH": f"/usr/local/cuda-12.8/bin:{os.environ['PATH']}"}

BENCH_PROMPT = "Explain in detail how transformer attention mechanisms work, including the mathematical formulation of scaled dot-product attention and multi-head attention."
BENCH_TOKENS = 400
BENCH_RUNS   = 3

CRITERIA = ["novelty", "feasibility", "impact", "safety", "measurable", "orthogonality"]

# ── Results history (loaded from TSV if exists, seeded with known-bad) ────────

SEED_TRIED = [
    {"name": "tensor-split 1,1 baseline",       "delta_gen": 0.0,  "outcome": "BASELINE"},
    {"name": "n-gpu-layers 999 all on GPU",      "delta_gen": 0.0,  "outcome": "BASELINE"},
    {"name": "flash-attn enabled",               "delta_gen": 0.0,  "outcome": "BASELINE"},
    {"name": "q4_0 kv cache baseline",           "delta_gen": 0.0,  "outcome": "BASELINE"},
    {"name": "mlock enabled",                    "delta_gen": 0.0,  "outcome": "BASELINE"},
    {"name": "ubatch-size 1024 baseline",        "delta_gen": 0.0,  "outcome": "BASELINE"},
    {"name": "threads 8 p-core affinity",        "delta_gen": 0.0,  "outcome": "BASELINE"},
    {"name": "ctx-size 65536",                   "delta_gen": 0.0,  "outcome": "BASELINE"},
]

results_history = list(SEED_TRIED)
best = dict(BASELINE)

# ── TSV logging ───────────────────────────────────────────────────────────────

def init_tsv():
    if not RESULTS_TSV.exists():
        with open(RESULTS_TSV, "w", newline="") as f:
            csv.writer(f, delimiter="\t").writerow(
                ["timestamp", "iteration", "name", "gen_tps", "delta_gen", "prompt_tps", "outcome", "hypothesis"]
            )

def append_tsv(iteration, name, gen_tps, delta_gen, prompt_tps, outcome, hypothesis):
    with open(RESULTS_TSV, "a", newline="") as f:
        csv.writer(f, delimiter="\t").writerow([
            datetime.now().strftime("%H:%M:%S"), iteration, name,
            f"{gen_tps:.2f}", f"{delta_gen:+.2f}", f"{prompt_tps:.2f}", outcome, hypothesis
        ])

# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg, also_print=True):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    if also_print:
        print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def log_section(title):
    log(f"\n{'─'*60}")
    log(f"  {title}")
    log(f"{'─'*60}")

# ── Server management ─────────────────────────────────────────────────────────

def build_server_cmd(flags: dict, port=TEST_PORT) -> list:
    cmd = [
        SERVER_BIN,
        "--model", MODEL_PATH,
        "--host", "127.0.0.1",
        "--port", str(port),
        "--n-gpu-layers", str(flags.get("n_gpu_layers", 999)),
        "--tensor-split", str(flags.get("tensor_split", "1,1")),
        "--flash-attn", "on" if flags.get("flash_attn", True) else "off",
        "-ctk", flags.get("ctk", "q4_0"),
        "-ctv", flags.get("ctv", "q4_0"),
        "--ctx-size", str(flags.get("ctx_size", 65536)),
        "--ubatch-size", str(flags.get("ubatch_size", 1024)),
        "--threads", str(flags.get("threads", 8)),
        "--threads-batch", str(flags.get("threads_batch", 8)),
        "--cpu-range", flags.get("cpu_range", "0-7"),
        "--cpu-range-batch", flags.get("cpu_range_batch", flags.get("cpu_range", "0-7")),
        "--alias", "glm47flash",
    ]
    if flags.get("mlock", True):
        cmd.append("--mlock")
    if flags.get("cpu_strict", True):
        cmd += ["--cpu-strict", "1"]
    for extra in flags.get("extra_flags", []):
        cmd += extra.split()
    return cmd

def kill_port(port):
    try:
        result = subprocess.run(["sudo", "lsof", "-ti", f":{port}"],
                                capture_output=True, text=True)
        pids = result.stdout.strip().split()
        for pid in pids:
            subprocess.run(["sudo", "kill", "-9", pid], capture_output=True)
        if pids:
            time.sleep(2)
    except Exception:
        pass

def free_vram():
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader"],
            capture_output=True, text=True)
        for line in r.stdout.strip().splitlines():
            parts = line.split(", ")
            if len(parts) >= 2 and "llama-server" in parts[1]:
                pid = parts[0].strip()
                subprocess.run(["sudo", "kill", "-9", pid], capture_output=True)
                log(f"  Freed leaked VRAM from pid {pid}")
        time.sleep(2)
    except Exception:
        pass

def wait_healthy(port, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
            if r.ok and "ok" in r.text:
                return True
        except Exception:
            pass
        time.sleep(3)
    return False

def start_test_server(flags: dict):
    kill_port(TEST_PORT)
    free_vram()
    cmd = build_server_cmd(flags, port=TEST_PORT)
    log(f"Starting test server: {' '.join(cmd[cmd.index('--n-gpu-layers'):])}")
    proc = subprocess.Popen(cmd, env=ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if wait_healthy(TEST_PORT, timeout=90):
        return proc
    proc.kill()
    proc.wait()
    kill_port(TEST_PORT)
    return None

def stop_server(proc, port=TEST_PORT):
    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    kill_port(port)
    time.sleep(2)

# ── Benchmarking ──────────────────────────────────────────────────────────────

def bench_once(port=TEST_PORT):
    try:
        r = requests.post(
            f"http://127.0.0.1:{port}/completion",
            json={"prompt": BENCH_PROMPT, "n_predict": BENCH_TOKENS, "stream": False},
            timeout=120,
        )
        t = r.json().get("timings", {})
        return {
            "gen_tps":    t.get("predicted_per_second", 0),
            "prompt_tps": t.get("prompt_per_second", 0),
        }
    except Exception as e:
        log(f"  bench error: {e}")
        return None

def bench_server(port=TEST_PORT, runs=BENCH_RUNS):
    results = []
    for i in range(runs):
        r = bench_once(port)
        if r is None:
            return None
        log(f"  run {i+1}: gen={r['gen_tps']:.1f} tok/s  prompt={r['prompt_tps']:.1f} tok/s")
        results.append(r)
    return {
        "gen_tps":    sum(x["gen_tps"]    for x in results) / len(results),
        "prompt_tps": sum(x["prompt_tps"] for x in results) / len(results),
    }

# ── LLM brain ─────────────────────────────────────────────────────────────────

def llm(system: str, user: str, port=PROD_PORT, max_tokens=1000) -> str:
    try:
        r = requests.post(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            json={
                "model": "glm47flash",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "stream": False,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=120,
        )
        msg = r.json()["choices"][0]["message"]
        return (msg.get("content") or msg.get("reasoning_content") or "").strip()
    except Exception as e:
        log(f"LLM call failed: {e}")
        return ""

def results_history_str() -> str:
    lines = []
    for r in results_history:
        delta = f"{r['delta_gen']:+.1f}" if isinstance(r['delta_gen'], float) else r['delta_gen']
        lines.append(f"  [{r['outcome']:10s}] {r['name']}  (Δgen={delta} tok/s)")
    return "\n".join(lines)

def generate_hypothesis(iteration: int):
    program = PROGRAM_MD.read_text() if PROGRAM_MD.exists() else ""

    system = """You are an expert in llama.cpp inference optimization for large language models on consumer GPU hardware.
Your job is to propose novel, feasible experiments to improve generation speed (tok/s).
Always respond with valid JSON only. No prose outside the JSON object.
CRITICAL: every score value must be exactly the integer 0 or 1. No other values allowed."""

    user = f"""## Research Program
{program}

## Current Best
gen: {best['gen_tps']:.1f} tok/s | prompt: {best['prompt_tps']:.1f} tok/s

## Full Results History (read carefully before proposing)
{results_history_str()}

## Task
Propose ONE new experiment for iteration {iteration}/{MAX_ITERS} that has NOT been tried above.
Study the results history — learn from what improved and what failed.

Respond with JSON only — no comments inside the JSON:
{{
  "name": "short experiment name",
  "hypothesis": "one sentence: what you expect and why",
  "flags_changed": {{"key": "value"}},
  "extra_flags": ["--flag value"],
  "scores": {{
    "novelty": 0,
    "feasibility": 0,
    "impact": 0,
    "safety": 0,
    "measurable": 0,
    "orthogonality": 0
  }},
  "score_reasoning": "one line per criterion"
}}"""

    raw = llm(system, user, port=PROD_PORT, max_tokens=1200)
    if not raw:
        return None
    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start == -1:
            return None
        blob = raw[start:end]
        # Strip // comments (invalid JSON but model often adds them)
        import re
        blob = re.sub(r'//[^\n]*', '', blob)
        return json.loads(blob)
    except json.JSONDecodeError as e:
        log(f"  JSON parse error: {e}\n  Raw: {raw[:300]}")
        return None

def score_hypothesis(hyp: dict) -> int:
    scores = hyp.get("scores", {})
    # Clamp to binary — model often returns 0-10 scale despite instructions
    return sum(min(1, max(0, int(float(scores.get(c, 0))))) for c in CRITERIA)

# ── Experiment runner ─────────────────────────────────────────────────────────

FLAG_ALIASES = {
    # LLM often generates these wrong names — map to correct build_server_cmd keys
    "kv_cache_type":     None,  # ignore — use ctk/ctv instead
    "kv_cache":          None,
    "cache_type":        None,
    "cache_type_k":      "ctk",
    "cache_type_v":      "ctv",
    "ctk":               "ctk",
    "ctv":               "ctv",
    "kv_type":           None,
    "n_gpu_layers":      "n_gpu_layers",
    "tensor_split":      "tensor_split",
    "ubatch_size":       "ubatch_size",
    "ctx_size":          "ctx_size",
    "threads":           "threads",
    "threads_batch":     "threads_batch",
    "cpu_range":         "cpu_range",
    "flash_attn":        "flash_attn",
    "mlock":             "mlock",
}

def run_experiment(hyp: dict, iteration: int) -> dict:
    flags = dict(best)
    for k, v in hyp.get("flags_changed", {}).items():
        normalized = k.lstrip("-").replace("-", "_")
        mapped = FLAG_ALIASES.get(normalized, normalized)
        if mapped is None:
            log(f"  Ignoring unrecognized flag key: {k}")
            continue
        flags[mapped] = v
    flags["extra_flags"] = hyp.get("extra_flags", [])

    log(f"\n  Flags delta: {hyp.get('flags_changed', {})}  extras: {flags['extra_flags']}")

    log("  Stopping prod server...")
    subprocess.run(["sudo", "systemctl", "stop", "llama-server"], capture_output=True)
    time.sleep(3)

    proc = start_test_server(flags)
    if proc is None:
        log("  Server failed to start — restarting prod...")
        subprocess.run(["sudo", "systemctl", "start", "llama-server"], capture_output=True)
        wait_healthy(PROD_PORT, timeout=120)
        return {"success": False, "reason": "server failed to start"}

    log("  Server up — running benchmark...")
    result = bench_server(TEST_PORT)
    stop_server(proc, TEST_PORT)

    log("  Restarting prod server...")
    subprocess.run(["sudo", "systemctl", "start", "llama-server"], capture_output=True)
    wait_healthy(PROD_PORT, timeout=120)

    if result is None:
        return {"success": False, "reason": "bench failed"}

    delta_gen    = result["gen_tps"]    - best["gen_tps"]
    delta_prompt = result["prompt_tps"] - best["prompt_tps"]
    improved     = delta_gen > 0.5

    return {
        "success":      True,
        "gen_tps":      result["gen_tps"],
        "prompt_tps":   result["prompt_tps"],
        "delta_gen":    delta_gen,
        "delta_prompt": delta_prompt,
        "improved":     improved,
        "flags":        flags,
    }

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    init_tsv()
    log_section(f"AUTORESEARCH LOOP v2 — GLM-4.7-Flash  ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    log(f"Baseline: gen={BASELINE['gen_tps']} tok/s  prompt={BASELINE['prompt_tps']} tok/s")
    log(f"Gate: {SCORE_GATE}/{len(CRITERIA)}  |  Max iterations: {MAX_ITERS}\n")

    seed_rejections = 0

    for iteration in range(MAX_ITERS):
        log_section(f"ITERATION {iteration+1}/{MAX_ITERS}")

        # Wait for prod server before generating seed
        if not wait_healthy(PROD_PORT, timeout=60):
            log("  Prod server not healthy — waiting longer...")
            wait_healthy(PROD_PORT, timeout=120)

        hyp = None
        attempts = 0
        while True:
            attempts += 1
            log(f"  Generating seed (attempt {attempts})...")
            candidate = generate_hypothesis(iteration + 1)
            if candidate is None:
                log("  LLM returned nothing, retrying...")
                time.sleep(5)
                continue

            score = score_hypothesis(candidate)
            log(f"  Seed: \"{candidate.get('name','?')}\"")
            log(f"  Score: {score}/{len(CRITERIA)}  |  {candidate.get('scores', {})}")
            log(f"  Hypothesis: {candidate.get('hypothesis','')}")

            if score >= SCORE_GATE:
                log(f"  Seed accepted ({score}/{len(CRITERIA)})")
                hyp = candidate
                break
            else:
                seed_rejections += 1
                log(f"  Seed rejected ({score}/{len(CRITERIA)} < {SCORE_GATE}) — regenerating")
                results_history.append({
                    "name": f"REJECTED: {candidate.get('name','?')}",
                    "delta_gen": 0.0,
                    "outcome": "REJECTED",
                })

        log(f"\n  Running: {hyp['name']}")
        log(f"  Hypothesis: {hyp['hypothesis']}")
        result = run_experiment(hyp, iteration + 1)

        name      = hyp["name"]
        hypothesis = hyp.get("hypothesis", "")

        if not result["success"]:
            log(f"\n  FAILED ({result['reason']})")
            results_history.append({"name": name, "delta_gen": 0.0, "outcome": "FAILED"})
            append_tsv(iteration+1, name, best["gen_tps"], 0.0, best["prompt_tps"], "FAILED", hypothesis)
        elif result["improved"]:
            log(f"\n  IMPROVEMENT")
            log(f"  gen: {result['gen_tps']:.1f} tok/s  (Delta {result['delta_gen']:+.1f})")
            log(f"  prompt: {result['prompt_tps']:.1f} tok/s  (Delta {result['delta_prompt']:+.1f})")
            best.update(result["flags"])
            best["gen_tps"]    = result["gen_tps"]
            best["prompt_tps"] = result["prompt_tps"]
            log(f"  New best: {best['gen_tps']:.1f} tok/s gen")
            results_history.append({"name": name, "delta_gen": result["delta_gen"], "outcome": "IMPROVED"})
            append_tsv(iteration+1, name, result["gen_tps"], result["delta_gen"], result["prompt_tps"], "IMPROVED", hypothesis)
        else:
            log(f"\n  NO IMPROVEMENT")
            log(f"  gen: {result['gen_tps']:.1f} tok/s  (Delta {result['delta_gen']:+.1f})")
            results_history.append({"name": name, "delta_gen": result["delta_gen"], "outcome": "NO_CHANGE"})
            append_tsv(iteration+1, name, result["gen_tps"], result["delta_gen"], result["prompt_tps"], "NO_CHANGE", hypothesis)

    # Final summary
    log_section("FINAL SUMMARY")
    log(f"Iterations: {MAX_ITERS}  |  Seeds rejected: {seed_rejections}")
    log(f"Baseline gen:  {BASELINE['gen_tps']:.1f} tok/s")
    log(f"Final best:    {best['gen_tps']:.1f} tok/s  (Delta {best['gen_tps']-BASELINE['gen_tps']:+.1f})")
    log(f"Baseline prompt: {BASELINE['prompt_tps']:.1f} tok/s")
    log(f"Final prompt:    {best['prompt_tps']:.1f} tok/s")

    best_path = Path("/home/dino/inference-research/current-best-flags-glm47.sh")
    with open(best_path, "w") as f:
        f.write(f"#!/bin/bash\n# BEST from autoresearch-glm47 v2 loop\n")
        f.write(f"# Gen: {best['gen_tps']:.1f} tok/s\n\n")
        f.write(f"export PATH=/usr/local/cuda-12.8/bin:$PATH\n\n")
        f.write(f"exec {SERVER_BIN} \\\n")
        f.write(f"  --model {MODEL_PATH} \\\n")
        f.write(f"  --host 0.0.0.0 --port 8081 \\\n")
        f.write(f"  --n-gpu-layers {best['n_gpu_layers']} \\\n")
        f.write(f"  --tensor-split {best['tensor_split']} \\\n")
        f.write(f"  --flash-attn on \\\n")
        f.write(f"  -ctk {best['ctk']} \\\n")
        f.write(f"  -ctv {best['ctv']} \\\n")
        f.write(f"  --ctx-size {best['ctx_size']} \\\n")
        f.write(f"  --ubatch-size {best['ubatch_size']} \\\n")
        f.write(f"  --threads {best['threads']} \\\n")
        f.write(f"  --threads-batch {best['threads_batch']} \\\n")
        f.write(f"  --cpu-range {best['cpu_range']} \\\n")
        f.write(f"  --cpu-range-batch {best.get('cpu_range_batch', best['cpu_range'])} \\\n")
        f.write(f"  --cpu-strict 1 \\\n")
        if best.get("mlock"):
            f.write(f"  --mlock \\\n")
        for ef in best.get("extra_flags", []):
            f.write(f"  {ef} \\\n")
        f.write(f"  --alias glm47flash\n")
    best_path.chmod(0o755)
    log(f"\nBest flags written to {best_path}")


if __name__ == "__main__":
    with open(LOG_FILE, "a") as f:
        f.write(f"\n\n{'='*70}\n")
        f.write(f"# Autoresearch GLM-4.7-Flash v2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"{'='*70}\n")
    try:
        main()
    except KeyboardInterrupt:
        log("\n  Loop interrupted by user")
        sys.exit(0)
