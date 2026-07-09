#!/usr/bin/env python3
"""
Karpathy-style autoresearch for supergemma4-26b single-GPU.
Principles:
  - ONE variable changed per experiment
  - LLM picks from an explicit candidate menu, not open-ended invention
  - Auto-revert: best config only advances on confirmed improvement
  - Fast-fail OOM detection
  - 20 iterations, patient and methodical
"""

import json, shlex, subprocess, time, sys, os, re, select, requests, csv
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASELINE = {
    "gen_tps":       61.7,
    "prompt_tps":    281.9,
    "n_gpu_layers":  999,
    "ctk":           "q4_0",
    "ctv":           "q4_0",
    "ctx_size":      32768,
    "ubatch_size":   1024,
    "threads":       8,
    "threads_batch": 8,
    "cpu_range":     "0-7",
    "cpu_range_batch": "0-7",
    "mlock":         True,
    "flash_attn":    True,
    "override_layers": "2[4-9]",   # regex range for blk expert CPU offload
}

MODEL_PATH = "/home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf"
SERVER_BIN = "/home/dino/llama.cpp/build/bin/llama-server"
TEST_PORT  = 8090
PROD_PORT  = 8081
MAX_ITERS  = 20
SCORE_GATE = 4
LOG_FILE   = Path("/home/dino/inference-research/autoresearch-supergemma-log.md")
RESULTS_TSV= Path("/home/dino/inference-research/autoresearch-supergemma-results.tsv")
ENV        = {**os.environ, "PATH": f"/usr/local/cuda-12.8/bin:{os.environ['PATH']}", "CUDA_VISIBLE_DEVICES": "0"}

BENCH_PROMPT = "Explain in detail how transformer attention mechanisms work, including the mathematical formulation of scaled dot-product attention and multi-head attention."
BENCH_TOKENS = 400
BENCH_RUNS   = 3
CRITERIA     = ["novelty", "feasibility", "impact", "safety", "measurable", "orthogonality"]

# ── Explicit candidate menu — LLM picks from this, one per experiment ─────────
# Each candidate changes exactly ONE logical thing from current best.
# Format: {name, variable, value, description, vram_delta_estimate_mib}
CANDIDATE_MENU = [
    # ubatch-size
    {"name": "ubatch 512",         "var": "ubatch_size",      "val": 512,    "desc": "smaller ubatch — less memory pressure per batch", "vram": 0},
    {"name": "ubatch 2048",        "var": "ubatch_size",      "val": 2048,   "desc": "larger ubatch — more SM utilization if not bandwidth-bound", "vram": 0},
    {"name": "ubatch 4096",        "var": "ubatch_size",      "val": 4096,   "desc": "maximum ubatch — saturate GPU compute", "vram": 0},
    # Threading — P-cores only variants
    {"name": "threads 4",          "var": "threads",          "val": 4,      "desc": "fewer threads — reduce scheduling overhead for CPU expert layers", "vram": 0},
    {"name": "threads 6",          "var": "threads",          "val": 6,      "desc": "moderate thread count for CPU experts", "vram": 0},
    # E-core threading (cpu_range change is paired with threads)
    {"name": "threads 12 all-core","var": "threads",          "val": 12,     "desc": "include E-cores for CPU-offloaded expert computation", "vram": 0,
     "also": {"cpu_range": "0-19", "cpu_range_batch": "0-19"}},
    {"name": "threads 16 all-core","var": "threads",          "val": 16,     "desc": "all 20 cores for CPU experts", "vram": 0,
     "also": {"cpu_range": "0-19", "cpu_range_batch": "0-19"}},
    # CPU expert layer count — fewer layers on CPU means more GPU work but less PCIe transfer
    {"name": "cpu layers 4 (26-29)","var": "override_layers", "val": "2[6-9]",       "desc": "only 4 layers on CPU — more GPU parallelism", "vram": 150},
    {"name": "cpu layers 8 (22-29)","var": "override_layers", "val": "2[2-9]",       "desc": "8 layers on CPU — slightly more offload than baseline 6", "vram": -150},
    {"name": "cpu layers 10 (20-29)","var":"override_layers", "val": "2[0-9]",       "desc": "10 layers on CPU — more offload, less GPU VRAM", "vram": -300},
    # defrag-thold
    {"name": "defrag 0.1",         "var": "extra",            "val": ["--defrag-thold", "0.1"], "desc": "light KV cache defrag — reduce fragmentation overhead", "vram": 0},
    {"name": "defrag 0.5",         "var": "extra",            "val": ["--defrag-thold", "0.5"], "desc": "aggressive KV cache defrag", "vram": 0},
    # no-mmap
    {"name": "no-mmap",            "var": "extra",            "val": ["--no-mmap"],  "desc": "disable memory-mapped loading — may improve runtime locality", "vram": 0},
    # parallel slots
    {"name": "parallel 2",         "var": "extra",            "val": ["--parallel", "2"], "desc": "2 parallel slots — tests if pre-allocation changes MoE routing throughput", "vram": 200},
    # cpu-strict off (allow scheduler to use any core)
    {"name": "cpu-strict off",     "var": "extra",            "val": ["--cpu-strict", "0"], "desc": "let OS scheduler use any core for CPU experts", "vram": 0},
]

# ── Results tracking ──────────────────────────────────────────────────────────

tried_names = {
    "ubatch-size 2048 (dual-GPU no improvement)",
    "Aggressive CPU Offload + Context Reduction for Q8 KV",
    "Aggressive CPU Offload with Context Reduction for Q4 KV",
    "Context Reduction for High-Precision KV",
    "Deep CPU Offload + Context Compression + Q4_NL KV",
    "Moderate CPU Offload + Q5_0 KV with 16k Context",
    "Deep CPU Offload + 16k Context + Q8 KV",
}
results_history = []
best = dict(BASELINE)
best_extra = []   # extra flags that are part of current best

# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def log_section(title):
    log(f"\n{'─'*60}\n  {title}\n{'─'*60}")

def init_tsv():
    if not RESULTS_TSV.exists():
        with open(RESULTS_TSV, "w", newline="") as f:
            csv.writer(f, delimiter="\t").writerow(
                ["ts", "iter", "name", "variable", "value", "gen_tps", "delta_gen", "prompt_tps", "outcome"])

def append_tsv(i, name, var, val, gen, delta, prompt, outcome):
    with open(RESULTS_TSV, "a", newline="") as f:
        csv.writer(f, delimiter="\t").writerow([
            datetime.now().strftime("%H:%M:%S"), i, name, var, str(val),
            f"{gen:.2f}", f"{delta:+.2f}", f"{prompt:.2f}", outcome])

# ── Server management ─────────────────────────────────────────────────────────

def override_tensor_flag(layer_range: str) -> list:
    return ["--override-tensor", f"blk\\.({layer_range})\\..*exps.*=CPU"]

def build_cmd(cfg: dict, extra: list, port=TEST_PORT) -> list:
    cmd = [
        SERVER_BIN, "--model", MODEL_PATH,
        "--host", "127.0.0.1", "--port", str(port),
        "--n-gpu-layers", str(cfg.get("n_gpu_layers", 999)),
        "--flash-attn", "on",
        "-ctk", cfg.get("ctk", "q4_0"),
        "-ctv", cfg.get("ctv", "q4_0"),
        "--ctx-size", str(cfg.get("ctx_size", 32768)),
        "--ubatch-size", str(cfg.get("ubatch_size", 1024)),
        "--threads", str(cfg.get("threads", 8)),
        "--threads-batch", str(cfg.get("threads_batch", cfg.get("threads", 8))),
        "--cpu-range", cfg.get("cpu_range", "0-7"),
        "--cpu-range-batch", cfg.get("cpu_range_batch", cfg.get("cpu_range", "0-7")),
        "--cpu-strict", "1",
        "--mlock", "--alias", "gemma4",
    ]
    cmd += override_tensor_flag(cfg.get("override_layers", "2[4-9]"))
    cmd += extra
    return cmd

OOM_MARKERS = [b"cudaMalloc failed", b"out of memory", b"failed to allocate",
               b"CUDA error", b"alloc_tensor_range: failed"]

def kill_port(port):
    r = subprocess.run(["sudo", "lsof", "-ti", f":{port}"], capture_output=True, text=True)
    for pid in r.stdout.strip().split():
        subprocess.run(["sudo", "kill", "-9", pid], capture_output=True)
    if r.stdout.strip():
        time.sleep(2)

def free_vram():
    r = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader"],
                       capture_output=True, text=True)
    for line in r.stdout.strip().splitlines():
        parts = line.split(", ")
        if len(parts) >= 2 and "llama-server" in parts[1]:
            subprocess.run(["sudo", "kill", "-9", parts[0].strip()], capture_output=True)
            log(f"  freed VRAM from pid {parts[0].strip()}")
    time.sleep(2)

def start_server(cfg, extra, port=TEST_PORT):
    kill_port(port)
    free_vram()
    cmd = build_cmd(cfg, extra, port)
    log(f"  $ {' '.join(cmd[5:])}")  # skip bin+model+host+port
    proc = subprocess.Popen(cmd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    buf = b""
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            if requests.get(f"http://127.0.0.1:{port}/health", timeout=1).ok:
                return proc
        except Exception:
            pass
        if proc.poll() is not None:
            buf += proc.stdout.read()
            reason = next((s.decode() for s in OOM_MARKERS if s in buf), "unexpected exit")
            log(f"  fast-fail: {reason}")
            kill_port(port); free_vram()
            return None
        ready, _, _ = select.select([proc.stdout], [], [], 0.2)
        if ready:
            chunk = proc.stdout.read1(8192)
            buf += chunk
            if any(s in buf for s in OOM_MARKERS):
                log(f"  fast-fail: OOM detected")
                proc.kill(); proc.wait()
                kill_port(port); free_vram()
                return None
        time.sleep(0.8)
    proc.kill(); proc.wait()
    kill_port(port); free_vram()
    return None

def stop_server(proc, port=TEST_PORT):
    if proc:
        proc.terminate()
        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    kill_port(port)
    free_vram()
    time.sleep(2)

def wait_healthy(port, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(f"http://127.0.0.1:{port}/health", timeout=2).ok:
                return True
        except Exception:
            pass
        time.sleep(3)
    return False

# ── Benchmarking ──────────────────────────────────────────────────────────────

def bench(port=TEST_PORT, runs=BENCH_RUNS):
    results = []
    for i in range(runs):
        try:
            r = requests.post(f"http://127.0.0.1:{port}/completion",
                json={"prompt": BENCH_PROMPT, "n_predict": BENCH_TOKENS, "stream": False},
                timeout=120)
            t = r.json().get("timings", {})
            gen = t.get("predicted_per_second", 0)
            if gen == 0:
                log(f"  run {i+1}: zero result — aborting bench"); return None
            prompt = t.get("prompt_per_second", 0)
            log(f"  run {i+1}: gen={gen:.1f}  prompt={prompt:.1f}")
            results.append((gen, prompt))
        except Exception as e:
            log(f"  run {i+1}: error {e}"); return None
    return {
        "gen_tps":    sum(x[0] for x in results) / len(results),
        "prompt_tps": sum(x[1] for x in results) / len(results),
    }

# ── LLM brain ─────────────────────────────────────────────────────────────────

def llm_pick(candidates_json: str, history_str: str, iteration: int) -> dict | None:
    try:
        r = requests.post(f"http://127.0.0.1:{PROD_PORT}/v1/chat/completions", json={
            "model": "gemma4",
            "messages": [
                {"role": "system", "content":
                    "You are an expert in llama.cpp inference optimization. "
                    "Pick ONE experiment from the provided candidate list. "
                    "Respond with valid JSON only. No prose outside JSON."},
                {"role": "user", "content": f"""
## Current best
gen: {best['gen_tps']:.1f} tok/s | prompt: {best['prompt_tps']:.1f} tok/s
active extra flags: {best_extra}
override_layers: {best.get('override_layers', '2[4-9]')}

## Results so far
{history_str}

## Candidate experiments (each changes ONE variable from current best)
{candidates_json}

## Task
Pick the ONE candidate most likely to improve gen tok/s that has NOT been tried yet.
Prefer candidates that are VRAM-neutral (vram_delta=0) since headroom is only ~900 MiB.
Respond with JSON:
{{"index": <0-based index into candidates list>, "reasoning": "one sentence"}}
"""}],
            "max_tokens": 200, "temperature": 0.4,
            "chat_template_kwargs": {"enable_thinking": False},
        }, timeout=60)
        content = r.json()["choices"][0]["message"].get("content", "")
        blob = content[content.find("{"):content.rfind("}")+1]
        return json.loads(blob)
    except Exception as e:
        log(f"  LLM pick failed: {e}")
        return None

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    init_tsv()
    log_section(f"AUTORESEARCH supergemma4-26b single-GPU  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log(f"Baseline: gen={BASELINE['gen_tps']} tok/s  prompt={BASELINE['prompt_tps']} tok/s")
    log(f"Iterations: {MAX_ITERS}  |  One variable per experiment\n")

    for iteration in range(MAX_ITERS):
        log_section(f"ITERATION {iteration+1}/{MAX_ITERS}  (best so far: {best['gen_tps']:.1f} tok/s)")

        if not wait_healthy(PROD_PORT, timeout=60):
            log("  prod not healthy — skip"); continue

        # Build available candidates (exclude already tried)
        available = [c for c in CANDIDATE_MENU if c["name"] not in tried_names]
        if not available:
            log("  All candidates exhausted — done"); break

        candidates_json = json.dumps([
            {"index": i, "name": c["name"], "variable": c["var"],
             "value": str(c["val"]), "description": c["desc"],
             "vram_delta_mib": c.get("vram", 0)}
            for i, c in enumerate(available)
        ], indent=2)

        history_str = "\n".join(
            f"  [{r['outcome']:10s}] {r['name']}  Δgen={r['delta']:+.1f}"
            for r in results_history
        ) or "  (none yet)"

        pick = llm_pick(candidates_json, history_str, iteration + 1)
        if pick is None:
            # fallback: pick first untried
            candidate = available[0]
            log(f"  LLM failed — falling back to: {candidate['name']}")
        else:
            idx = int(pick.get("index", 0))
            if idx >= len(available): idx = 0
            candidate = available[idx]
            log(f"  LLM picked [{idx}]: {candidate['name']}")
            log(f"  Reasoning: {pick.get('reasoning', '')}")

        tried_names.add(candidate["name"])

        # Build config for this experiment
        cfg = dict(best)
        extra = list(best_extra)

        var = candidate["var"]
        val = candidate["val"]

        if var == "extra":
            extra = extra + val
        elif var == "threads":
            cfg["threads"] = val
            cfg["threads_batch"] = val
            for k, v in candidate.get("also", {}).items():
                cfg[k] = v
        else:
            cfg[var] = val

        log(f"  Changing: {var} → {val}  (extra: {extra})")

        # Run experiment
        log("  Stopping prod...")
        subprocess.run(["sudo", "systemctl", "stop", "llama-server"], capture_output=True)
        time.sleep(3)

        proc = start_server(cfg, extra)
        if proc is None:
            log("  Server failed — restarting prod, marking FAILED")
            subprocess.run(["sudo", "systemctl", "start", "llama-server"], capture_output=True)
            wait_healthy(PROD_PORT)
            results_history.append({"name": candidate["name"], "delta": 0.0, "outcome": "FAILED"})
            append_tsv(iteration+1, candidate["name"], var, val, best["gen_tps"], 0.0, best["prompt_tps"], "FAILED")
            continue

        result = bench(TEST_PORT)
        stop_server(proc)

        log("  Restarting prod...")
        subprocess.run(["sudo", "systemctl", "start", "llama-server"], capture_output=True)
        wait_healthy(PROD_PORT)

        if result is None:
            log("  Bench failed")
            results_history.append({"name": candidate["name"], "delta": 0.0, "outcome": "BENCH_FAIL"})
            append_tsv(iteration+1, candidate["name"], var, val, best["gen_tps"], 0.0, best["prompt_tps"], "BENCH_FAIL")
            continue

        delta = result["gen_tps"] - best["gen_tps"]
        improved = delta > 0.5
        outcome = "IMPROVED" if improved else "NO_CHANGE"

        log(f"  gen: {result['gen_tps']:.1f} tok/s  (Δ{delta:+.1f})  prompt: {result['prompt_tps']:.1f}")

        if improved:
            log(f"  ✓ NEW BEST: {result['gen_tps']:.1f} tok/s")
            best.update(cfg)
            best["gen_tps"] = result["gen_tps"]
            best["prompt_tps"] = result["prompt_tps"]
            best_extra[:] = extra
        else:
            log(f"  ✗ No improvement — reverting to best")

        results_history.append({"name": candidate["name"], "delta": delta, "outcome": outcome})
        append_tsv(iteration+1, candidate["name"], var, val, result["gen_tps"], delta, result["prompt_tps"], outcome)

    # ── Summary ────────────────────────────────────────────────────────────────
    log_section("FINAL SUMMARY")
    log(f"Baseline:   {BASELINE['gen_tps']:.1f} tok/s gen")
    log(f"Final best: {best['gen_tps']:.1f} tok/s gen  (Δ{best['gen_tps']-BASELINE['gen_tps']:+.1f})")
    log(f"Best extra flags: {best_extra}")

    best_path = Path("/home/dino/inference-research/current-best-flags-supergemma-1gpu.sh")
    with open(best_path, "w") as f:
        f.write("#!/bin/bash\n# Best from autoresearch-supergemma single-GPU\n")
        f.write(f"# Gen: {best['gen_tps']:.1f} tok/s\n\n")
        f.write(f"export PATH=/usr/local/cuda-12.8/bin:$PATH\nexport CUDA_VISIBLE_DEVICES=0\n\n")
        f.write(f"exec {SERVER_BIN} \\\n  --model {MODEL_PATH} \\\n")
        f.write(f"  --host 0.0.0.0 --port 8081 \\\n  --n-gpu-layers {best['n_gpu_layers']} \\\n")
        f.write(f"  --flash-attn on \\\n  -ctk {best['ctk']} \\\n  -ctv {best['ctv']} \\\n")
        f.write(f"  --ctx-size {best['ctx_size']} \\\n  --ubatch-size {best['ubatch_size']} \\\n")
        f.write(f"  --threads {best['threads']} \\\n  --threads-batch {best.get('threads_batch', best['threads'])} \\\n")
        f.write(f"  --cpu-range {best['cpu_range']} \\\n  --cpu-range-batch {best['cpu_range_batch']} \\\n")
        f.write(f"  --cpu-strict 1 --mlock \\\n")
        f.write(f"  --override-tensor \"blk\\.({best['override_layers']})\\..*exps.*=CPU\" \\\n")
        for ef in best_extra:
            f.write(f"  {ef} \\\n")
        f.write(f"  --alias gemma4\n")
    best_path.chmod(0o755)
    log(f"Written to {best_path}")

if __name__ == "__main__":
    with open(LOG_FILE, "a") as f:
        f.write(f"\n\n{'='*70}\n# Autoresearch supergemma4-26b single-GPU — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{'='*70}\n")
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted"); sys.exit(0)
