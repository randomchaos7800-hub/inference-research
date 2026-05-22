#!/usr/bin/env python3
"""
Karpathy-style autoresearch loop for Llama 3.3 70B dual-GPU inference optimization.
Uses the local 70B model as the research brain (model improves itself).
Seed quality gate: must score 5/6 on evaluation criteria.
"""

import json
import subprocess
import time
import sys
import os
import signal
import requests
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASELINE = {
    "gen_tps": 55.6,
    "prompt_tps": 164.0,
    "n_gpu_layers": 60,
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

MODEL_PATH = "/home/dino/models/Llama-3.3-70B-Instruct-IQ4_XS.gguf"
SERVER_BIN = "/home/dino/llama.cpp/build/bin/llama-server"
TEST_PORT  = 8090
PROD_PORT  = 8081
MAX_ITERS  = 10
SCORE_GATE = 5
LOG_FILE   = Path("/home/dino/inference-research/autoresearch-70b-log.md")
ENV        = {**os.environ, "PATH": f"/usr/local/cuda-12.8/bin:{os.environ['PATH']}"}

BENCH_PROMPT  = "Explain in detail how transformer attention mechanisms work, including the mathematical formulation of scaled dot-product attention and multi-head attention."
BENCH_TOKENS  = 400
BENCH_RUNS    = 3

# ── Scoring criteria (6 total, need 5) ────────────────────────────────────────

CRITERIA = [
    "novelty",        # not tried before in this session
    "feasibility",    # doable via llama-server flags only, no recompile
    "impact",         # plausibly moves gen tok/s by >3%
    "safety",         # won't OOM or crash (low risk)
    "measurable",     # produces a clear numeric metric
    "orthogonality",  # independent from other experiments this session
]

# ── Already-tried experiments (seeded from prior loop knowledge) ──────────────

TRIED = [
    "p-core affinity threads 8",
    "ubatch-size 512",
    "ubatch-size 2048",
    "tensor-split 1,1.3 (OOM)",
    "tensor-split 0.8,1 (OOM)",
    "n-gpu-layers 68 (OOM)",
    "ctx-size 32768 baseline",
    "mlock enabled",
    "flash-attn enabled",
    "q4_0 kv cache",
    "q8_0 kv cache",
]

session_tried = list(TRIED)
best = dict(BASELINE)
best_flags_extra = ""  # extra flags on top of base

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
        "--n-gpu-layers", str(flags.get("n_gpu_layers", 60)),
        "--tensor-split", flags.get("tensor_split", "1,1"),
        "--flash-attn", "on" if flags.get("flash_attn", True) else "off",
        f"-ctk", flags.get("ctk", "q4_0"),
        f"-ctv", flags.get("ctv", "q4_0"),
        "--ctx-size", str(flags.get("ctx_size", 65536)),
        "--ubatch-size", str(flags.get("ubatch_size", 1024)),
        "--threads", str(flags.get("threads", 8)),
        "--threads-batch", str(flags.get("threads_batch", 8)),
        "--cpu-range", flags.get("cpu_range", "0-7"),
        "--cpu-range-batch", flags.get("cpu_range_batch", flags.get("cpu_range", "0-7")),
        "--alias", "llama70b",
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
    """Kill any leaked llama-server processes holding VRAM."""
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

def start_test_server(flags: dict) -> subprocess.Popen | None:
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

def stop_server(proc: subprocess.Popen, port=TEST_PORT):
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

def bench_once(port=TEST_PORT) -> dict | None:
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
            "gen_n":      t.get("predicted_n", 0),
        }
    except Exception as e:
        log(f"  bench error: {e}")
        return None

def bench_server(port=TEST_PORT, runs=BENCH_RUNS) -> dict | None:
    results = []
    for i in range(runs):
        r = bench_once(port)
        if r is None:
            return None
        log(f"  run {i+1}: gen={r['gen_tps']:.1f} tok/s  prompt={r['prompt_tps']:.1f} tok/s")
        results.append(r)
    avg_gen    = sum(x["gen_tps"]    for x in results) / len(results)
    avg_prompt = sum(x["prompt_tps"] for x in results) / len(results)
    return {"gen_tps": avg_gen, "prompt_tps": avg_prompt}

# ── LLM brain: generate + score hypothesis ────────────────────────────────────

def llm(system: str, user: str, port=PROD_PORT, max_tokens=800) -> str:
    """Call the local 70B model."""
    try:
        r = requests.post(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            json={
                "model": "llama70b",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "stream": False,
            },
            timeout=120,
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"LLM call failed: {e}")
        return ""

def generate_hypothesis(iteration: int) -> dict | None:
    """Ask the 70B model to propose a new experiment. Returns parsed hypothesis or None."""

    system = """You are an expert in llama.cpp inference optimization for large language models on consumer GPU hardware.
Your job is to propose novel, feasible experiments to improve generation speed (tok/s) for a specific setup.
Always respond with valid JSON only. No prose outside the JSON object."""

    tried_str = "\n".join(f"- {t}" for t in session_tried)

    user = f"""Current setup:
- Model: Llama 3.3 70B IQ4_XS (36GB), 80 transformer layers
- Hardware: 2x RTX 5060 Ti (15.8GB VRAM each, Blackwell SM120), Arrow Lake 8P+12E cores
- Current flags: --n-gpu-layers 60 --tensor-split 1,1 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-strict 1 --mlock
- Baseline gen: {best['gen_tps']:.1f} tok/s | prompt: {best['prompt_tps']:.1f} tok/s
- Constraint: 60 GPU layers is near the VRAM ceiling (both GPUs at ~60% utilization)
- 20 layers run on CPU (Arrow Lake P-cores), these are the current bottleneck

Already tried (do NOT repeat these):
{tried_str}

Propose ONE new experiment for iteration {iteration}/{MAX_ITERS}.
Focus on what's NOT been tried. Consider: CPU thread count for CPU layers, E-core utilization for CPU layers, ubatch tuning, batch-size, defrag-thold, NUMA, no-mmap, CPU scheduling, priority, KV cache type combinations, specific tensor-split ratios with reduced layers that balance VRAM.

Respond with JSON only:
{{
  "name": "short experiment name",
  "hypothesis": "one sentence: what you expect and why",
  "flags_changed": {{
    "key": "value"
  }},
  "extra_flags": ["--flag value", ...],
  "scores": {{
    "novelty": 1,
    "feasibility": 1,
    "impact": 1,
    "safety": 1,
    "measurable": 1,
    "orthogonality": 1
  }},
  // IMPORTANT: each score must be exactly integer 0 or 1, no floats
  "score_reasoning": "brief justification for each score"
}}"""

    raw = llm(system, user, port=PROD_PORT, max_tokens=800)
    if not raw:
        return None

    # Extract JSON from response
    try:
        # Find JSON block
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start == -1:
            return None
        data = json.loads(raw[start:end])
        return data
    except json.JSONDecodeError as e:
        log(f"  JSON parse error: {e}\n  Raw: {raw[:300]}")
        return None

def score_hypothesis(hyp: dict) -> int:
    scores = hyp.get("scores", {})
    # Floor each score so floats like 0.8 count as 0 — enforces strict 5/6 integer gate
    return sum(int(scores.get(c, 0)) for c in CRITERIA)

# ── Experiment runner ─────────────────────────────────────────────────────────

def run_experiment(hyp: dict, iteration: int) -> dict:
    """Apply hypothesis flags, bench, return result dict."""
    flags = dict(best)

    # Apply flag changes — normalize LLM keys: strip leading dashes, hyphens→underscores
    for k, v in hyp.get("flags_changed", {}).items():
        normalized = k.lstrip("-").replace("-", "_")
        flags[normalized] = v
    flags["extra_flags"] = hyp.get("extra_flags", [])

    log(f"\n  Flags delta: {hyp.get('flags_changed', {})}  extras: {flags['extra_flags']}")

    # Stop prod server to free VRAM for test server
    log("  Stopping prod server...")
    subprocess.run(["sudo", "systemctl", "stop", "llama-server"], capture_output=True)
    time.sleep(3)

    proc = start_test_server(flags)
    if proc is None:
        log("  ❌ Server failed to start (OOM or crash)")
        subprocess.run(["sudo", "systemctl", "start", "llama-server"], capture_output=True)
        return {"success": False, "reason": "server failed to start"}

    log("  Server up — running benchmark...")
    result = bench_server(TEST_PORT)
    stop_server(proc, TEST_PORT)

    # Restart prod server
    log("  Restarting prod server...")
    subprocess.run(["sudo", "systemctl", "start", "llama-server"], capture_output=True)
    wait_healthy(PROD_PORT, timeout=90)

    if result is None:
        return {"success": False, "reason": "bench failed"}

    delta_gen    = result["gen_tps"]    - best["gen_tps"]
    delta_prompt = result["prompt_tps"] - best["prompt_tps"]
    improved     = delta_gen > 0.5  # >0.5 tok/s is real

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
    log_section(f"AUTORESEARCH LOOP — Llama 3.3 70B dual GPU  ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    log(f"Baseline: gen={BASELINE['gen_tps']} tok/s  prompt={BASELINE['prompt_tps']} tok/s")
    log(f"Gate: {SCORE_GATE}/{len(CRITERIA)}  |  Max iterations: {MAX_ITERS}\n")

    iteration = 0
    seed_rejections = 0

    while iteration < MAX_ITERS:
        log_section(f"ITERATION {iteration+1}/{MAX_ITERS}")

        # Generate and score hypothesis — retry until 5/6 gate passed
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
                log(f"  ✅ Seed accepted ({score:.1f}/{len(CRITERIA)})")
                hyp = candidate
                break
            else:
                seed_rejections += 1
                log(f"  ❌ Seed rejected ({score:.1f}/{len(CRITERIA)} < {SCORE_GATE}/{len(CRITERIA)}) — regenerating")
                session_tried.append(f"REJECTED: {candidate.get('name','?')}")

        session_tried.append(hyp["name"])

        # Run experiment
        log(f"\n  Running: {hyp['name']}")
        log(f"  Hypothesis: {hyp['hypothesis']}")
        result = run_experiment(hyp, iteration + 1)

        # Log result
        if not result["success"]:
            verdict = f"❌ FAILED ({result['reason']})"
            log(f"\n  {verdict}")
        elif result["improved"]:
            verdict = "✅ IMPROVEMENT"
            log(f"\n  {verdict}")
            log(f"  gen: {result['gen_tps']:.1f} tok/s  (Δ {result['delta_gen']:+.1f})")
            log(f"  prompt: {result['prompt_tps']:.1f} tok/s  (Δ {result['delta_prompt']:+.1f})")
            # Update best
            best.update(result["flags"])
            best["gen_tps"]    = result["gen_tps"]
            best["prompt_tps"] = result["prompt_tps"]
            log(f"  New best: {best['gen_tps']:.1f} tok/s gen")
        else:
            verdict = "— NO IMPROVEMENT"
            log(f"\n  {verdict}")
            log(f"  gen: {result['gen_tps']:.1f} tok/s  (Δ {result['delta_gen']:+.1f})")

        iteration += 1

    # Final summary
    log_section("FINAL SUMMARY")
    log(f"Iterations completed: {iteration}/{MAX_ITERS}")
    log(f"Seeds rejected: {seed_rejections}")
    log(f"Baseline gen:  {BASELINE['gen_tps']:.1f} tok/s")
    log(f"Final best:    {best['gen_tps']:.1f} tok/s  (Δ {best['gen_tps']-BASELINE['gen_tps']:+.1f})")
    log(f"Baseline prompt: {BASELINE['prompt_tps']:.1f} tok/s")
    log(f"Final prompt:    {best['prompt_tps']:.1f} tok/s")

    # Write best flags
    best_path = Path("/home/dino/inference-research/current-best-flags-70b.sh")
    with open(best_path, "w") as f:
        f.write(f"#!/bin/bash\n# BEST from autoresearch-70b loop\n")
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
        f.write(f"  --alias llama70b\n")
    best_path.chmod(0o755)
    log(f"\nBest flags written to {best_path}")


if __name__ == "__main__":
    # Write header to log
    with open(LOG_FILE, "a") as f:
        f.write(f"\n\n{'='*70}\n")
        f.write(f"# Autoresearch 70B Loop — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"{'='*70}\n")
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️  Loop interrupted by user")
        sys.exit(0)
