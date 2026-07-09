#!/usr/bin/env python3
"""
Karpathy-style autoresearch for supergemma4-26b dual-GPU (Z890, 2x RTX 5060 Ti).
Principles:
  - ONE variable changed per experiment
  - LLM picks from an explicit candidate menu, not open-ended invention
  - llama-bench as evaluator (reproducible, no server needed during bench)
  - Auto-revert: best config only advances on confirmed improvement
  - Greedy ratchet: only forward progress stacks
"""

import json, subprocess, time, sys, os, re, requests, csv
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASELINE = {
    "gen_tgs512":    99.2,
    "gen_tgs128":    97.4,
    "prompt_pp2048": 4502.0,
    "prompt_pp8192": 5569.0,
    "ctk":           "q4_0",
    "ctv":           "q4_0",
    "ubatch_size":   1024,
    "batch_size":    2048,
    "threads":       8,
    "threads_batch": 8,
    "cpu_range":     "0-7",
    "cpu_range_batch": "0-7",
    "mlock":         True,
    "flash_attn":    True,
    "split_mode":    "layer",
}

MODEL_PATH  = "/home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf"
SERVER_BIN  = "/home/dino/llama.cpp/build/bin/llama-server"
BENCH_BIN   = "/home/dino/llama.cpp/build/bin/llama-bench"
PROD_PORT   = 8081
MAX_ITERS   = 20
BENCH_REPS  = 3
IMPROVE_THRESHOLD = 0.8   # tok/s — must beat this to count as improvement (~1%)

LOG_FILE    = Path("/home/dino/inference-research/autoresearch-supergemma-dualGPU-log.md")
RESULTS_TSV = Path("/home/dino/inference-research/autoresearch-supergemma-dualGPU-results.tsv")
BEST_FLAGS  = Path("/home/dino/inference-research/current-best-flags-supergemma-dualGPU.sh")
ENV         = {**os.environ, "PATH": f"/usr/local/cuda-12.8/bin:{os.environ['PATH']}"}

# ── State ─────────────────────────────────────────────────────────────────────

best          = dict(BASELINE)
best_extra    = []          # list of extra flag strings
tried_names   = set()
results_history = []

# ── Candidate menu ────────────────────────────────────────────────────────────
# Each entry changes exactly ONE logical thing from current best.
# VRAM headroom is generous (~12 GB free with current config) — no tight constraints.

CANDIDATE_MENU = [
    # KV cache quantization
    {"name": "ctk/ctv q8_0",       "var": "ctk_ctv",    "val": "q8_0",  "desc": "higher-quality KV cache — may improve cache hit efficiency", "vram": 500},
    {"name": "ctk/ctv q5_0",       "var": "ctk_ctv",    "val": "q5_0",  "desc": "mid-quality KV between q4 and q8", "vram": 200},
    {"name": "ctk/ctv iq4_nl",     "var": "ctk_ctv",    "val": "iq4_nl","desc": "non-linear q4 KV — better quality than q4_0 at same size", "vram": 0},
    {"name": "ctk/ctv f16",        "var": "ctk_ctv",    "val": "f16",   "desc": "full-precision KV cache — maximum quality, tests if quantization hurts speed", "vram": 2000},

    # ubatch-size
    {"name": "ubatch 512",         "var": "ubatch_size", "val": 512,    "desc": "smaller ubatch — less GPU scheduling overhead per batch", "vram": 0},
    {"name": "ubatch 2048",        "var": "ubatch_size", "val": 2048,   "desc": "larger ubatch — more SM utilization on dual GPU", "vram": 0},
    {"name": "ubatch 4096",        "var": "ubatch_size", "val": 4096,   "desc": "maximum ubatch — saturate GPU compute", "vram": 0},

    # batch-size
    {"name": "batch 4096",         "var": "batch_size",  "val": 4096,   "desc": "larger prompt batch for better GPU utilization during prefill", "vram": 0},
    {"name": "batch 8192",         "var": "batch_size",  "val": 8192,   "desc": "maximum batch size for prompt processing", "vram": 0},

    # Threading
    {"name": "threads 4",          "var": "threads",     "val": 4,      "desc": "fewer threads — reduce OS scheduling overhead", "vram": 0},
    {"name": "threads 12 all-core","var": "threads",     "val": 12,     "desc": "include E-cores (0-19) for any CPU-side work", "vram": 0,
     "also": {"cpu_range": "0-19", "cpu_range_batch": "0-19"}},
    {"name": "threads 16 all-core","var": "threads",     "val": 16,     "desc": "all 20 cores for CPU-side operations", "vram": 0,
     "also": {"cpu_range": "0-19", "cpu_range_batch": "0-19"}},
    {"name": "threads 20 all-core","var": "threads",     "val": 20,     "desc": "all 20 threads max utilization", "vram": 0,
     "also": {"cpu_range": "0-19", "cpu_range_batch": "0-19"}},

    # Split mode — row and tensor crash on Gemma4 MoE (GGML_ASSERT view_src==nullptr)
    # Only layer split is supported for this model architecture

    # mlock
    {"name": "no mlock",           "var": "mlock",       "val": False,  "desc": "disable mlock — allow OS to manage model pages", "vram": 0},

    # poll
    {"name": "poll 0",             "var": "extra",       "val": ["--poll", "0"],   "desc": "no CPU polling — pure event-driven scheduling", "vram": 0},
    {"name": "poll 100",           "var": "extra",       "val": ["--poll", "100"], "desc": "maximum CPU polling — lowest latency at cost of CPU", "vram": 0},

    # NUMA
    {"name": "numa distribute",    "var": "extra",       "val": ["--numa", "distribute"], "desc": "distribute memory across NUMA nodes for Arrow Lake", "vram": 0},

    # mmap (llama-bench uses --mmap 0/1)
    {"name": "no-mmap",           "var": "extra",       "val": ["--mmap", "0"], "desc": "disable memory-mapped loading — tests runtime locality", "vram": 0},

    # Explicit tensor split skewing (GPU 0 is x8 PCIe, GPU 1 is x4 — slight bias to GPU 0)
    {"name": "tensor-split 2/1",  "var": "extra",       "val": ["-ts", "2/1"], "desc": "bias 2/3 of layers to GPU 0 (x8 PCIe) vs GPU 1 (x4 PCIe)", "vram": 0},
    {"name": "tensor-split 3/2",  "var": "extra",       "val": ["-ts", "3/2"], "desc": "slight bias toward GPU 0 to account for PCIe bandwidth asymmetry", "vram": 0},
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

# ── TSV results ───────────────────────────────────────────────────────────────

def init_tsv():
    if not RESULTS_TSV.exists():
        with open(RESULTS_TSV, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["iter", "name", "variable", "value",
                        "tg512", "delta_tg512", "pp2048", "outcome"])

def append_tsv(iter, name, var, val, tg512, delta, pp2048, outcome):
    with open(RESULTS_TSV, "a", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow([iter, name, var, val, f"{tg512:.2f}", f"{delta:+.2f}", f"{pp2048:.0f}", outcome])

# ── llama-bench evaluation ────────────────────────────────────────────────────

def build_bench_cmd(cfg: dict, extra: list) -> list:
    cmd = [BENCH_BIN,
           "--model", MODEL_PATH,
           "--n-gpu-layers", "999",
           "--flash-attn", "1",
           "-ctk", cfg["ctk"],
           "-ctv", cfg["ctv"],
           "--threads", str(cfg["threads"]),
           "--cpu-mask", "0xFF",
           "--cpu-strict", "1",
           "--ubatch-size", str(cfg["ubatch_size"]),
           "-b", str(cfg["batch_size"]),
           "--split-mode", cfg["split_mode"],
           "-p", "2048",
           "-n", "512",
           "-r", str(BENCH_REPS),
           "-o", "md",
    ]
    # Note: --mlock, --threads-batch, --defrag-thold are server-only — not passed to bench
    cmd.extend(extra)
    return cmd

def parse_bench_output(output: str) -> dict | None:
    tg512 = tg128 = pp2048 = pp8192 = None
    for line in output.splitlines():
        if "| " not in line or "model" in line or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        test_col = next((p for p in parts if p in ("tg512", "tg128", "pp2048", "pp8192", "pp512")), None)
        if not test_col:
            continue
        val_str = parts[-2] if parts[-1] == "" else parts[-1]
        try:
            val = float(val_str.split("±")[0].strip())
        except ValueError:
            continue
        if test_col == "tg512":  tg512 = val
        elif test_col == "tg128": tg128 = val
        elif test_col == "pp2048": pp2048 = val
        elif test_col == "pp8192": pp8192 = val

    if tg512 is None:
        return None
    return {
        "tg512":  tg512,
        "tg128":  tg128  or 0.0,
        "pp2048": pp2048 or 0.0,
        "pp8192": pp8192 or 0.0,
    }

def run_bench(cfg: dict, extra: list) -> dict | None:
    cmd = build_bench_cmd(cfg, extra)
    log(f"  bench cmd: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=480, env=ENV)
        output = result.stdout + result.stderr
        if result.returncode != 0:
            log(f"  bench failed (exit {result.returncode})")
            log(f"  stderr: {result.stderr[-500:]}")
            return None
        parsed = parse_bench_output(output)
        if parsed is None:
            log(f"  bench parse failed — raw tail:\n{output[-500:]}")
        return parsed
    except subprocess.TimeoutExpired:
        log("  bench timed out")
        return None

# ── Server control ────────────────────────────────────────────────────────────

def stop_prod():
    subprocess.run(["sudo", "systemctl", "stop", "llama-server"],
                   capture_output=True)
    time.sleep(4)

def start_prod():
    subprocess.run(["sudo", "systemctl", "start", "llama-server"],
                   capture_output=True)

def wait_healthy(timeout=90):
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

# ── LLM brain — uses prod server to pick next experiment ─────────────────────

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

    prompt = f"""## Current best
tg512: {best['gen_tgs512']:.2f} tok/s | tg128: {best['gen_tgs128']:.2f} tok/s
pp2048: {best['prompt_pp2048']:.0f} tok/s | pp8192: {best['prompt_pp8192']:.0f} tok/s
active extra flags: {best_extra}
ctk/ctv: {best['ctk']}/{best['ctv']}
ubatch: {best['ubatch_size']} | batch: {best['batch_size']}
threads: {best['threads']} | split-mode: {best['split_mode']}

## Results so far
{history_str}

## Candidate experiments (each changes ONE variable from current best)
{candidates_json}

## Task
Pick the ONE candidate most likely to improve tg512 (generation tok/s) that has NOT been tried.
VRAM headroom is ~12 GB — no tight memory constraints on this run.
Respond with JSON only:
{{"index": <0-based index into candidates list>, "reasoning": "one sentence"}}"""

    try:
        r = requests.post(f"http://127.0.0.1:{PROD_PORT}/v1/chat/completions", json={
            "model": "gemma4",
            "messages": [
                {"role": "system", "content":
                    "You are an expert in llama.cpp inference optimization for dual-GPU setups. "
                    "Pick ONE experiment from the provided candidate list. "
                    "Respond with valid JSON only. No prose outside JSON."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 150, "temperature": 0.3,
            "chat_template_kwargs": {"enable_thinking": False},
        }, timeout=60)
        content = r.json()["choices"][0]["message"].get("content", "")
        blob = content[content.find("{"):content.rfind("}")+1]
        return json.loads(blob)
    except Exception as e:
        log(f"  LLM pick failed: {e}")
        return None

# ── Write best-flags script ───────────────────────────────────────────────────

def write_best_flags():
    lines = [
        "#!/bin/bash",
        f"# Best from autoresearch-supergemma-dualGPU",
        f"# tg512: {best['gen_tgs512']:.2f} tok/s  |  pp2048: {best['prompt_pp2048']:.0f} tok/s",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "export PATH=/usr/local/cuda-12.8/bin:$PATH",
        "",
        f"exec {SERVER_BIN} \\",
        f"  --model {MODEL_PATH} \\",
        "  --host 0.0.0.0 --port 8081 \\",
        "  --n-gpu-layers 999 \\",
        "  --flash-attn on \\",
        f"  -ctk {best['ctk']} \\",
        f"  -ctv {best['ctv']} \\",
        f"  --ctx-size 65536 \\",
        f"  --ubatch-size {best['ubatch_size']} \\",
        f"  -b {best['batch_size']} \\",
        f"  --split-mode {best['split_mode']} \\",
        f"  --threads {best['threads']} \\",
        f"  --threads-batch {best['threads_batch']} \\",
        f"  --cpu-range {best['cpu_range']} \\",
        f"  --cpu-range-batch {best['cpu_range_batch']} \\",
        "  --cpu-strict 1 \\",
    ]
    if best.get("mlock"):
        lines.append("  --mlock \\")
    for ef in best_extra:
        lines.append(f"  {ef} \\")
    lines.append("  --chat-template-kwargs '{\"enable_thinking\":false}' \\")
    lines.append("  --alias gemma4")

    with open(BEST_FLAGS, "w") as f:
        f.write("\n".join(lines) + "\n")
    BEST_FLAGS.chmod(0o755)
    log(f"  Best flags written to {BEST_FLAGS}")

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    init_tsv()
    log_section(f"AUTORESEARCH supergemma4-26b dual-GPU  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log(f"Baseline: tg512={BASELINE['gen_tgs512']} tok/s  pp2048={BASELINE['prompt_pp2048']:.0f} tok/s")
    log(f"Iterations: {MAX_ITERS}  |  One variable per experiment  |  Improve threshold: {IMPROVE_THRESHOLD} tok/s")
    log(f"Hardware: 2x RTX 5060 Ti (32 GB total), ~12 GB VRAM headroom\n")

    # Verify prod server is up before starting
    log("Checking prod server health...")
    if not wait_healthy(timeout=30):
        log("ERROR: prod server not healthy — start it first")
        sys.exit(1)
    log("Prod server healthy. Starting research loop.\n")

    for iteration in range(MAX_ITERS):
        log_section(f"ITERATION {iteration+1}/{MAX_ITERS}  (best so far: {best['gen_tgs512']:.2f} tok/s)")

        available = [c for c in CANDIDATE_MENU if c["name"] not in tried_names]
        if not available:
            log("All candidates exhausted — done")
            break

        # Ask LLM while prod is still up
        pick = llm_pick(available)
        if pick is None:
            candidate = available[0]
            log(f"  LLM failed — falling back to: {candidate['name']}")
        else:
            idx = int(pick.get("index", 0))
            if idx >= len(available): idx = 0
            candidate = available[idx]
            log(f"  LLM picked [{idx}]: {candidate['name']}")
            log(f"  Reasoning: {pick.get('reasoning', '')}")

        tried_names.add(candidate["name"])

        # Build experimental config
        cfg = dict(best)
        extra = list(best_extra)

        var = candidate["var"]
        val = candidate["val"]

        if var == "extra":
            extra = extra + val
        elif var == "ctk_ctv":
            cfg["ctk"] = val
            cfg["ctv"] = val
        elif var == "threads":
            cfg["threads"] = val
            cfg["threads_batch"] = val
            for k, v in candidate.get("also", {}).items():
                cfg[k] = v
        elif var == "mlock":
            cfg["mlock"] = val
        else:
            cfg[var] = val

        log(f"  Changing: {var} → {val}  extra: {extra}")

        # Stop prod, bench, restart prod
        log("  Stopping prod server for bench...")
        stop_prod()

        result = run_bench(cfg, extra)

        log("  Restarting prod server...")
        start_prod()
        wait_healthy()

        if result is None:
            log("  Bench failed — marking FAILED")
            results_history.append({"name": candidate["name"], "delta": 0.0, "outcome": "FAILED"})
            append_tsv(iteration+1, candidate["name"], var, str(val),
                       best["gen_tgs512"], 0.0, best["prompt_pp2048"], "FAILED")
            continue

        delta = result["tg512"] - best["gen_tgs512"]
        improved = delta > IMPROVE_THRESHOLD
        outcome = "IMPROVED" if improved else "NO_CHANGE"

        log(f"  tg512: {result['tg512']:.2f} tok/s  (Δ{delta:+.2f})  "
            f"tg128: {result['tg128']:.2f}  pp2048: {result['pp2048']:.0f}")

        if improved:
            log(f"  NEW BEST: {result['tg512']:.2f} tok/s  (+{delta:.2f} from previous best)")
            best.update(cfg)
            best["gen_tgs512"]    = result["tg512"]
            best["gen_tgs128"]    = result["tg128"]
            best["prompt_pp2048"] = result["pp2048"]
            best["prompt_pp8192"] = result["pp8192"]
            best_extra[:] = extra
            write_best_flags()
        else:
            log(f"  No improvement ({delta:+.2f}) — reverting to best")

        results_history.append({"name": candidate["name"], "delta": delta, "outcome": outcome})
        append_tsv(iteration+1, candidate["name"], var, str(val),
                   result["tg512"], delta, result["pp2048"], outcome)

        log("")

    # ── Final summary ──────────────────────────────────────────────────────────
    log_section("FINAL SUMMARY")
    log(f"Baseline:   tg512={BASELINE['gen_tgs512']:.2f} tok/s")
    log(f"Final best: tg512={best['gen_tgs512']:.2f} tok/s  (Δ{best['gen_tgs512']-BASELINE['gen_tgs512']:+.2f})")
    log(f"Best config: ctk/ctv={best['ctk']}  ubatch={best['ubatch_size']}  batch={best['batch_size']}  "
        f"threads={best['threads']}  split={best['split_mode']}  extra={best_extra}")
    log("")
    improved_list = [r for r in results_history if r["outcome"] == "IMPROVED"]
    log(f"Improvements found: {len(improved_list)}/{len(results_history)} experiments")
    for r in improved_list:
        log(f"  + {r['name']}: Δ{r['delta']:+.2f} tok/s")
    write_best_flags()

if __name__ == "__main__":
    with open(LOG_FILE, "a") as f:
        f.write(f"\n\n{'='*70}\n"
                f"# Autoresearch supergemma4-26b dual-GPU — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"{'='*70}\n")
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted by user")
        log_section("PARTIAL SUMMARY")
        log(f"Best reached: tg512={best['gen_tgs512']:.2f} tok/s")
        write_best_flags()
        sys.exit(0)
