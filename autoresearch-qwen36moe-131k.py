#!/usr/bin/env python3
"""
Karpathy-style autoresearch — Qwen3.6-35B-A3B, 131K context pass.

Context: first pass (65K, f16 KV) exhausted the standard knobs with zero improvement.
This pass uses the locked config: ctx=131072, q4_0 KV, which is the new production default.
Baseline: tg512=97.34 t/s (q4_0 KV costs ~3 t/s vs f16 but is required for 131K to fit).

New experiments this pass:
  - Flash-attn off: at 131K ctx, O(n²) attention trades memory for different compute patterns
  - No-KV-offload: puts 4GB q4_0 KV on CPU RAM — frees GPU bandwidth, adds PCIe reads
  - Depth characterization: d=4096/16384/32768/65536 — map the speed curve as ctx fills
  - Threads at depth: at d=65536 the 16 attention layers are O(n), more threads may help there
  - Main-gpu swap: GPU1 as main affects layer scheduling
  - Confirmed-skip: tensor split, n-cpu-moe, split-mode tensor (all hurt in pass 1)

Parser fix: handles 'tg512 @ d{N}' test names from depth runs.
"""

import json, subprocess, time, sys, os, signal, traceback, re, requests, csv
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASELINE = {
    "gen_tgs512":    97.34,
    "prompt_pp512":  2426.0,
    "ctk":           "q4_0",
    "ctv":           "q4_0",
    "ubatch_size":   4096,
    "batch_size":    2048,
    "threads":       8,
    "cpu_range":     "0-7",
    "n_depth":       0,
    "flash_attn":    1,
    "nkvo":          0,
    "main_gpu":      0,
    "mlock":         True,
    "split_mode":    "layer",
}

MODEL_PATH  = "/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
SERVER_BIN  = "/home/dino/llama.cpp/build/bin/llama-server"
BENCH_BIN   = "/home/dino/llama.cpp/build/bin/llama-bench"
PROD_PORT   = 8081
MAX_ITERS   = 20
BENCH_REPS  = 3
IMPROVE_THRESHOLD = 0.8   # tok/s — tighter (~1%) since we're squeezing

LOG_FILE    = Path("/home/dino/inference-research/autoresearch-qwen36moe-131k-log.md")
RESULTS_TSV = Path("/home/dino/inference-research/autoresearch-qwen36moe-131k-results.tsv")
BEST_FLAGS  = Path("/home/dino/inference-research/current-best-flags-qwen36moe-131k.sh")
ENV         = {**os.environ, "PATH": f"/usr/local/cuda-12.8/bin:{os.environ['PATH']}"}

# ── State ─────────────────────────────────────────────────────────────────────

best            = dict(BASELINE)
best_extra      = []
tried_names     = set()
results_history = []

# ── Candidate menu ────────────────────────────────────────────────────────────

CANDIDATE_MENU = [
    # Flash-attn — pass 1 always had it on. At 131K ctx, O(n²) vs flash may differ.
    # Risk: without flash-attn at 131K, VRAM for attn scores could OOM. Test at d=0 first.
    {"name": "flash-attn off",    "var": "flash_attn",  "val": 0,
     "desc": "disable flash-attn — at 131K ctx tests if standard O(n²) attn paths are faster for this MoE", "vram": 500},

    # No-KV-offload — keeps 4GB KV cache in CPU RAM instead of GPU VRAM
    # Frees ~4GB GPU bandwidth pressure; adds PCIe reads per token for the 16 attn layers
    {"name": "no-kv-offload",     "var": "nkvo",        "val": 1,
     "desc": "KV cache in CPU RAM — frees 4GB GPU VRAM, trades PCIe bandwidth for attn layers", "vram": -4000},

    # Main GPU — currently auto (GPU0). Swapping to GPU1 changes layer routing.
    {"name": "main-gpu 1",        "var": "main_gpu",    "val": 1,
     "desc": "set GPU1 as main — different layer distribution may suit asymmetric PCIe (x4 vs x8)", "vram": 0},

    # ubatch — pass 1 tested these but with f16 KV at d=0. q4_0 KV + 131K ctx may differ slightly.
    {"name": "ubatch 2048",       "var": "ubatch_size", "val": 2048,
     "desc": "re-test 2048 ubatch with q4_0 KV baseline", "vram": 0},
    {"name": "ubatch 1024",       "var": "ubatch_size", "val": 1024,
     "desc": "re-test 1024 ubatch with q4_0 KV baseline", "vram": 0},

    # Threads — pass 1 showed no gain at d=0. But at long depth, attn layers do O(n) work.
    # These tests run at d=32768 to stress the attention path specifically.
    {"name": "threads 16 d32k",   "var": "threads",     "val": 16,
     "desc": "16 threads at 32K depth — O(n) attn layers may parallelize better with more cores",
     "vram": 0, "also": {"cpu_range": "0-19", "n_depth": 32768}},
    {"name": "threads 12 d32k",   "var": "threads",     "val": 12,
     "desc": "12 threads at 32K depth", "vram": 0,
     "also": {"cpu_range": "0-19", "n_depth": 32768}},
    {"name": "threads 20 d32k",   "var": "threads",     "val": 20,
     "desc": "all 20 cores at 32K depth", "vram": 0,
     "also": {"cpu_range": "0-19", "n_depth": 32768}},

    # Depth characterization — these are informational benchmarks that map the speed curve.
    # Wins here don't update the baseline config (depth is not a tunable), but inform ctx choice.
    {"name": "depth 4096",        "var": "n_depth",     "val": 4096,
     "desc": "tg speed at 4K depth — typical short doc/chat", "vram": 0},
    {"name": "depth 16384",       "var": "n_depth",     "val": 16384,
     "desc": "tg speed at 16K depth", "vram": 0},
    {"name": "depth 32768",       "var": "n_depth",     "val": 32768,
     "desc": "tg speed at 32K depth — old ctx ceiling", "vram": 0},
    {"name": "depth 65536",       "var": "n_depth",     "val": 65536,
     "desc": "tg speed at 65K depth — half new ctx", "vram": 0},
    {"name": "depth 98304",       "var": "n_depth",     "val": 98304,
     "desc": "tg speed at 96K depth — 3/4 new ctx", "vram": 0},
    {"name": "depth 131000",      "var": "n_depth",     "val": 131000,
     "desc": "tg speed near 131K depth — full ctx ceiling", "vram": 0},

    # Batch size
    {"name": "batch 4096",        "var": "batch_size",  "val": 4096,
     "desc": "larger prefill batch", "vram": 0},

    # mlock off
    {"name": "no mlock",          "var": "mlock",       "val": False,
     "desc": "disable mlock", "vram": 0},

    # mmap off
    {"name": "no-mmap",           "var": "extra",       "val": ["-mmp", "0"],
     "desc": "disable mmap — re-test with q4_0 baseline", "vram": 0},
]

# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def log_section(title: str):
    line = f"\n## {title}\n"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── TSV ───────────────────────────────────────────────────────────────────────

def init_tsv():
    if not RESULTS_TSV.exists():
        with open(RESULTS_TSV, "w", newline="") as f:
            csv.writer(f, delimiter="\t").writerow(
                ["iter", "name", "variable", "value", "depth",
                 "tg512", "delta_tg512", "pp512", "outcome"])

def append_tsv(iter, name, var, val, depth, tg512, delta, pp512, outcome):
    with open(RESULTS_TSV, "a", newline="") as f:
        csv.writer(f, delimiter="\t").writerow(
            [iter, name, var, val, depth,
             f"{tg512:.2f}", f"{delta:+.2f}", f"{pp512:.0f}", outcome])

# ── llama-bench ───────────────────────────────────────────────────────────────

def build_bench_cmd(cfg: dict, extra: list) -> list:
    cpu_mask = "0xFF" if cfg["cpu_range"] == "0-7" else "0xFFFFF"
    cmd = [BENCH_BIN,
           "--model", MODEL_PATH,
           "--n-gpu-layers", "999",
           "--flash-attn", str(cfg["flash_attn"]),
           "-ctk", cfg["ctk"], "-ctv", cfg["ctv"],
           "--threads", str(cfg["threads"]),
           "--cpu-mask", cpu_mask, "--cpu-strict", "1",
           "--ubatch-size", str(cfg["ubatch_size"]),
           "-b", str(cfg["batch_size"]),
           "--split-mode", cfg["split_mode"],
           "-nkvo", str(cfg["nkvo"]),
           "-mg", str(cfg["main_gpu"]),
           "-d", str(cfg.get("n_depth", 0)),
           "-p", "512", "-n", "512",
           "-r", str(BENCH_REPS), "-o", "md",
    ]
    cmd.extend(extra)
    return cmd

def parse_bench_output(output: str) -> dict | None:
    """Parse llama-bench markdown output. Handles 'tg512 @ d{N}' depth variants."""
    tg512 = pp512 = None
    for line in output.splitlines():
        if "| " not in line or "model" in line or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        # Match test column: bare 'tg512'/'pp512' or 'tg512 @ d{N}'
        test_col = None
        for p in parts:
            if re.match(r'^tg512', p):
                test_col = "tg512"
                break
            if re.match(r'^pp512', p):
                test_col = "pp512"
                break
        if not test_col:
            continue
        val_str = parts[-2] if parts[-1] == "" else parts[-1]
        try:
            val = float(val_str.split("±")[0].strip())
        except ValueError:
            continue
        if test_col == "tg512":
            tg512 = val
        elif test_col == "pp512":
            pp512 = val

    if tg512 is None:
        return None
    return {"tg512": tg512, "pp512": pp512 or 0.0}

def run_bench(cfg: dict, extra: list) -> dict | None:
    cmd = build_bench_cmd(cfg, extra)
    log(f"  bench cmd: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=ENV)
        output = result.stdout + result.stderr
        if result.returncode != 0:
            log(f"  bench failed (exit {result.returncode})")
            log(f"  stderr: {result.stderr[-600:]}")
            return None
        parsed = parse_bench_output(output)
        if parsed is None:
            log(f"  bench parse failed — raw tail:\n{output[-600:]}")
        return parsed
    except subprocess.TimeoutExpired:
        log("  bench timed out")
        return None

# ── Server control ────────────────────────────────────────────────────────────

def stop_prod():
    subprocess.run("lsof -ti:8081 -sTCP:LISTEN | xargs -r kill -9",
                   shell=True, capture_output=True)
    subprocess.run(["sudo", "systemctl", "stop", "llama-server"], capture_output=True)
    for _ in range(20):
        time.sleep(1)
        try:
            out = subprocess.check_output(
                "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits",
                shell=True, text=True)
            if sum(int(x.strip()) for x in out.strip().splitlines()) < 5000:
                break
        except Exception:
            pass
    time.sleep(2)

def start_prod():
    subprocess.run(["sudo", "systemctl", "start", "llama-server"], capture_output=True)

def wait_healthy(timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"http://127.0.0.1:{PROD_PORT}/health", timeout=3)
            if r.json().get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(3)
    return False

# ── LLM brain ────────────────────────────────────────────────────────────────

def llm_pick(available: list) -> dict | None:
    history_str = "\n".join(
        f"  [{r['outcome']:12s}] {r['name']}  Δtg512={r['delta']:+.2f}"
        for r in results_history
    ) or "  (none yet)"

    candidates_json = json.dumps([
        {"index": i, "name": c["name"], "variable": c["var"],
         "value": str(c["val"]), "description": c["desc"],
         "vram_delta_mib": c.get("vram", 0)}
        for i, c in enumerate(available)
    ], indent=2)

    prompt = f"""## Current best config (pass 2 — 131K context, q4_0 KV locked)
tg512 (d=0): {best['gen_tgs512']:.2f} tok/s | pp512: {best['prompt_pp512']:.0f} tok/s
extra: {best_extra}
ubatch: {best['ubatch_size']} | batch: {best['batch_size']}
threads: {best['threads']} | cpu_range: {best['cpu_range']}
flash_attn: {best['flash_attn']} | nkvo: {best['nkvo']} | main_gpu: {best['main_gpu']}

## Architecture (Qwen3.6-35B-A3B)
- MoE: 35B total, 3B active | 64 layers: 48 GDN (O(1) in ctx) + 16 full-attn (O(n) in ctx)
- ctx=131072, q4_0 KV locked (f16 would OOM). VRAM headroom ~6.6GB.
- Pass 1 ruled out: tensor-split bias (≤0.7 t/s), thread counts (≤0.9 t/s), ubatch variants,
  split-mode tensor (-15 t/s), n-cpu-moe (-13 to -22 t/s), batch/mmap/mlock tweaks.
- Depth tests: each 2x ctx depth roughly halves tg speed (attn layers dominate at depth).

## Results so far
{history_str}

## Candidates
{candidates_json}

## Task
Pick the ONE candidate most likely to improve tg512 at d=0 (baseline speed), or if all
speed candidates are exhausted, pick the most informative depth characterization.
Respond with JSON only: {{"index": <int>, "reasoning": "one sentence"}}"""

    try:
        r = requests.post(f"http://127.0.0.1:{PROD_PORT}/v1/chat/completions", json={
            "model": "qwen36moe",
            "messages": [
                {"role": "system", "content":
                    "You are an expert in llama.cpp inference optimization. "
                    "Pick ONE experiment. JSON only, no prose outside JSON."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 150, "temperature": 0.3,
        }, timeout=60)
        content = r.json()["choices"][0]["message"].get("content", "")
        blob = content[content.find("{"):content.rfind("}")+1]
        return json.loads(blob)
    except Exception as e:
        log(f"  LLM pick failed: {e}")
        return None

# ── Best flags writer ─────────────────────────────────────────────────────────

def write_best_flags():
    cpu_mask = "0xFF" if best["cpu_range"] == "0-7" else "0xFFFFF"
    fa = "on" if best["flash_attn"] else "off"
    lines = [
        "#!/bin/bash",
        f"# Qwen3.6-35B-A3B 131K — best from autoresearch pass 2",
        f"# tg512: {best['gen_tgs512']:.2f} tok/s  |  pp512: {best['prompt_pp512']:.0f} tok/s",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "export PATH=/usr/local/cuda-12.8/bin:$PATH",
        "",
        f"exec {SERVER_BIN} \\",
        f"  --model {MODEL_PATH} \\",
        "  --host 0.0.0.0 --port 8081 \\",
        "  --n-gpu-layers 999 \\",
        f"  --flash-attn {fa} \\",
        f"  -ctk {best['ctk']} -ctv {best['ctv']} \\",
        f"  --ctx-size 131072 \\",
        f"  --ubatch-size {best['ubatch_size']} \\",
        f"  -b {best['batch_size']} \\",
        f"  --split-mode {best['split_mode']} \\",
        f"  -nkvo {best['nkvo']} \\",
        f"  -mg {best['main_gpu']} \\",
        f"  --threads {best['threads']} \\",
        f"  --threads-batch {best['threads']} \\",
        f"  --cpu-range 0-7 --cpu-range-batch 0-7 \\",
        "  --cpu-strict 1 \\",
    ]
    if best.get("mlock"):
        lines.append("  --mlock \\")
    for ef in best_extra:
        lines.append(f"  {ef} \\")
    lines.append("  --chat-template-kwargs '{\"enable_thinking\":false}' \\")
    lines.append("  --alias qwen36moe")
    with open(BEST_FLAGS, "w") as f:
        f.write("\n".join(lines) + "\n")
    BEST_FLAGS.chmod(0o755)
    log(f"  Best flags written to {BEST_FLAGS}")

# ── Main loop ─────────────────────────────────────────────────────────────────

# depth experiments are informational — don't update best config if they score well
DEPTH_ONLY_NAMES = {
    "depth 4096", "depth 16384", "depth 32768",
    "depth 65536", "depth 98304", "depth 131000",
}

def main():
    init_tsv()
    log_section(f"AUTORESEARCH Qwen3.6-35B-A3B 131K pass 2  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log(f"Baseline: tg512={BASELINE['gen_tgs512']} tok/s (q4_0 KV, ctx=131072)  pp512={BASELINE['prompt_pp512']:.0f} tok/s")
    log(f"Iterations: {MAX_ITERS}  |  Improve threshold: {IMPROVE_THRESHOLD} tok/s\n")

    log("Checking prod server health...")
    if not wait_healthy(timeout=60):
        log("ERROR: prod server not healthy — start it first")
        sys.exit(1)
    log("Prod server healthy. Starting research loop.\n")

    for iteration in range(MAX_ITERS):
        log_section(f"ITERATION {iteration+1}/{MAX_ITERS}  (best so far: {best['gen_tgs512']:.2f} tok/s)")

        available = [c for c in CANDIDATE_MENU if c["name"] not in tried_names]
        if not available:
            log("All candidates exhausted — done")
            break

        pick = llm_pick(available)
        if pick is None:
            candidate = available[0]
            log(f"  LLM failed — falling back to: {candidate['name']}")
        else:
            idx = min(int(pick.get("index", 0)), len(available) - 1)
            candidate = available[idx]
            log(f"  LLM picked [{idx}]: {candidate['name']}")
            log(f"  Reasoning: {pick.get('reasoning', '')}")

        tried_names.add(candidate["name"])

        cfg = dict(best)
        extra = list(best_extra)
        var, val = candidate["var"], candidate["val"]

        if var == "extra":
            extra = extra + val
        elif var == "threads":
            cfg["threads"] = val
            for k, v in candidate.get("also", {}).items():
                cfg[k] = v
        elif var == "n_depth":
            cfg["n_depth"] = val
        elif var == "mlock":
            cfg["mlock"] = val
        else:
            cfg[var] = val
            for k, v in candidate.get("also", {}).items():
                cfg[k] = v

        log(f"  Changing: {var} → {val}  depth={cfg.get('n_depth',0)}  extra={extra}")

        log("  Stopping prod server for bench...")
        stop_prod()
        result = run_bench(cfg, extra)
        log("  Restarting prod server...")
        start_prod()
        wait_healthy()

        depth = cfg.get("n_depth", 0)
        is_depth_only = candidate["name"] in DEPTH_ONLY_NAMES

        if result is None:
            log("  Bench failed — marking FAILED")
            results_history.append({"name": candidate["name"], "delta": 0.0, "outcome": "FAILED"})
            append_tsv(iteration+1, candidate["name"], var, str(val), depth,
                       best["gen_tgs512"], 0.0, best["prompt_pp512"], "FAILED")
            continue

        # For depth-only experiments, compare against baseline at d=0 (informational)
        ref_speed = BASELINE["gen_tgs512"] if is_depth_only else best["gen_tgs512"]
        delta = result["tg512"] - ref_speed
        improved = (not is_depth_only) and (delta > IMPROVE_THRESHOLD)
        outcome = "DEPTH_INFO" if is_depth_only else ("IMPROVED" if improved else "NO_CHANGE")

        log(f"  tg512: {result['tg512']:.2f} tok/s  (Δ{delta:+.2f} vs {'baseline' if is_depth_only else 'best'})  pp512: {result['pp512']:.0f}")

        if improved:
            log(f"  NEW BEST: {result['tg512']:.2f} tok/s")
            best.update(cfg)
            best["gen_tgs512"]   = result["tg512"]
            best["prompt_pp512"] = result["pp512"]
            best_extra[:] = extra
            write_best_flags()
        elif is_depth_only:
            log(f"  Depth info: {result['tg512']:.2f} tok/s at d={depth}")
        else:
            log(f"  No improvement ({delta:+.2f}) — reverting")

        results_history.append({"name": candidate["name"], "delta": delta, "outcome": outcome})
        append_tsv(iteration+1, candidate["name"], var, str(val), depth,
                   result["tg512"], delta, result["pp512"], outcome)
        log("")

    log_section("FINAL SUMMARY")
    log(f"Baseline:   tg512={BASELINE['gen_tgs512']:.2f} tok/s")
    log(f"Final best: tg512={best['gen_tgs512']:.2f} tok/s  (Δ{best['gen_tgs512']-BASELINE['gen_tgs512']:+.2f})")
    improved_list = [r for r in results_history if r["outcome"] == "IMPROVED"]
    depth_list    = [r for r in results_history if r["outcome"] == "DEPTH_INFO"]
    log(f"Speed improvements: {len(improved_list)}/{len(results_history)} experiments")
    for r in improved_list:
        log(f"  + {r['name']}: Δ{r['delta']:+.2f} tok/s")
    if depth_list:
        log("Depth characterization:")
        for r in depth_list:
            log(f"  {r['name']}: {BASELINE['gen_tgs512']+r['delta']:.2f} tok/s")
    write_best_flags()

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    def _crash_handler(sig, frame):
        msg = f"FATAL: received signal {sig}"
        print(msg, flush=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"\n[FATAL] {msg}\n")
        sys.exit(1)

    for _sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(_sig, _crash_handler)

    with open(LOG_FILE, "a") as f:
        f.write(f"\n\n{'='*70}\n"
                f"# Autoresearch Qwen3.6-35B-A3B 131K pass 2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"{'='*70}\n")
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted")
        log(f"Best reached: tg512={best['gen_tgs512']:.2f} tok/s")
        write_best_flags()
        sys.exit(0)
    except Exception as e:
        msg = f"FATAL EXCEPTION: {e}\n{traceback.format_exc()}"
        print(msg, flush=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"\n[FATAL] {msg}\n")
        sys.exit(1)
