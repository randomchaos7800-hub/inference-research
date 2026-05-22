#!/usr/bin/env python3
"""
Karpathy-style autoresearch for Qwen3.6-35B-A3B UD-Q4_K_M on dual RTX 5060 Ti.

Architecture notes (inform experiment design):
  - qwen35moe: 35B total, 3B active params (MoE routing)
  - 64 layers: 3x GDN → FFN, 1x Gated Attention → FFN repeating (16 attn + 48 GDN)
  - GDN (Gated DeltaNet) = SSM-style — sequential state update, not parallelizable like attention
  - tg bottleneck is GDN sequential compute, NOT memory bandwidth
  - KV cache type (f16 vs q4_0) confirmed irrelevant to tg speed
  - pp is extremely fast (2436 t/s) because MoE skips 90%+ of experts per token during prefill batching
  - VRAM: 14.7 + 13.9 = 28.6 GB loaded (f16 KV, 65536 ctx), ~3.6 GB headroom
"""

import json, subprocess, time, sys, os, re, requests, csv
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASELINE = {
    "gen_tgs512":    100.24,
    "gen_tgs128":    100.24,   # measured same pass — will update after first bench
    "prompt_pp512":  2436.19,
    "ctk":           "f16",
    "ctv":           "f16",
    "ubatch_size":   4096,
    "batch_size":    2048,
    "threads":       8,
    "cpu_range":     "0-7",
    "n_depth":       0,
    "mlock":         True,
    "flash_attn":    True,
    "split_mode":    "layer",
}

MODEL_PATH  = "/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
SERVER_BIN  = "/home/dino/llama.cpp/build/bin/llama-server"
BENCH_BIN   = "/home/dino/llama.cpp/build/bin/llama-bench"
PROD_PORT   = 8081
MAX_ITERS   = 20
BENCH_REPS  = 3
IMPROVE_THRESHOLD = 1.0   # tok/s — ~1% of 100 t/s baseline

LOG_FILE    = Path("/home/dino/inference-research/autoresearch-qwen36moe-log.md")
RESULTS_TSV = Path("/home/dino/inference-research/autoresearch-qwen36moe-results.tsv")
BEST_FLAGS  = Path("/home/dino/inference-research/current-best-flags-qwen36moe.sh")
ENV         = {**os.environ, "PATH": f"/usr/local/cuda-12.8/bin:{os.environ['PATH']}"}

# ── State ─────────────────────────────────────────────────────────────────────

best          = dict(BASELINE)
best_extra    = []
# Pre-populate with results from prior aborted run (11:05 session)
tried_names   = {"threads 4", "split-mode tensor", "ubatch 8192"}
results_history = [
    {"name": "threads 4",       "delta": -0.73,  "outcome": "NO_CHANGE"},
    {"name": "split-mode tensor","delta": -15.20, "outcome": "NO_CHANGE"},
    {"name": "ubatch 8192",     "delta": 0.0,    "outcome": "FAILED"},
]

# ── Candidate menu ────────────────────────────────────────────────────────────
# ONE variable changed per experiment.
# tg bottleneck = GDN sequential compute. Focus on batching, scheduling, routing.
# VRAM headroom ~3.6 GB (tight) — flag vram costs.

CANDIDATE_MENU = [
    # KV cache quant — baseline f16. q4_0 confirmed same tg speed on 27B sibling,
    # but frees ~7 GB VRAM headroom for other experiments. Test first to unlock headroom.
    {"name": "ctk/ctv q4_0",     "var": "ctk_ctv",    "val": "q4_0",  "desc": "free ~7GB VRAM (confirmed same tg speed on GDN arch)", "vram": -7000},
    {"name": "ctk/ctv q8_0",     "var": "ctk_ctv",    "val": "q8_0",  "desc": "8-bit KV — slightly more VRAM than q4_0, less than f16", "vram": 500},

    # ubatch-size — GDN processes tokens sequentially per layer; batching affects expert routing
    {"name": "ubatch 512",       "var": "ubatch_size", "val": 512,    "desc": "smaller ubatch — less GDN state overhead per batch pass", "vram": 0},
    {"name": "ubatch 1024",      "var": "ubatch_size", "val": 1024,   "desc": "mid ubatch — test if 4096 is over-batching for MoE routing", "vram": 0},
    {"name": "ubatch 2048",      "var": "ubatch_size", "val": 2048,   "desc": "mid-large ubatch", "vram": 0},
    {"name": "ubatch 8192",      "var": "ubatch_size", "val": 8192,   "desc": "larger ubatch — maximize MoE expert co-batching", "vram": 200},

    # batch-size (prefill)
    {"name": "batch 4096",       "var": "batch_size",  "val": 4096,   "desc": "larger prefill batch — already fast pp but worth testing", "vram": 0},
    {"name": "batch 8192",       "var": "batch_size",  "val": 8192,   "desc": "max prefill batch", "vram": 0},

    # Threading — GDN state update has some CPU-side bookkeeping
    {"name": "threads 4",        "var": "threads",     "val": 4,      "desc": "fewer threads — reduce scheduling contention on GDN compute", "vram": 0},
    {"name": "threads 12 all",   "var": "threads",     "val": 12,     "desc": "include E-cores for any CPU-side GDN work",
     "vram": 0, "also": {"cpu_range": "0-19"}},
    {"name": "threads 16 all",   "var": "threads",     "val": 16,     "desc": "more E-cores",
     "vram": 0, "also": {"cpu_range": "0-19"}},
    {"name": "threads 20 all",   "var": "threads",     "val": 20,     "desc": "all 20 cores",
     "vram": 0, "also": {"cpu_range": "0-19"}},

    # Tensor split — MoE layers may benefit from explicit GPU bias
    {"name": "tensor-split 1/1", "var": "extra",       "val": ["-ts", "1/1"], "desc": "explicit equal split (vs current auto)", "vram": 0},
    {"name": "tensor-split 2/1", "var": "extra",       "val": ["-ts", "2/1"], "desc": "bias 2/3 of layers to GPU0 (x8 PCIe vs x4)", "vram": 0},
    {"name": "tensor-split 3/2", "var": "extra",       "val": ["-ts", "3/2"], "desc": "slight bias to GPU0 for PCIe asymmetry", "vram": 0},

    # Split mode — layer is current; tensor split may suit MoE weight matrices
    # WARNING: row split crashes on MoE (GGML_ASSERT view_src). Tensor worth testing.
    {"name": "split-mode tensor","var": "split_mode",  "val": "tensor", "desc": "tensor split distributes weight matrix rows — may suit MoE experts", "vram": 0},

    # n-cpu-moe — bench supports -ncmoe; route MoE expert layers to CPU
    {"name": "n-cpu-moe 1",      "var": "extra",       "val": ["-ncmoe", "1"], "desc": "route 1 MoE expert to CPU — frees GPU mem bandwidth at PCIe cost", "vram": -500},
    {"name": "n-cpu-moe 2",      "var": "extra",       "val": ["-ncmoe", "2"], "desc": "route 2 MoE experts to CPU", "vram": -1000},

    # mmap
    {"name": "no-mmap",          "var": "extra",       "val": ["-mmp", "0"],    "desc": "disable mmap — test if pinned model load is faster for MoE routing", "vram": 0},

    # Context depth experiments — use llama-bench -d (n-depth) to pre-fill KV cache
    # and measure tg speed at that context depth. Also validates VRAM fits.
    # GDN (SSM) layers are O(1) in context — only 16/64 attention layers scale with depth.
    # With q4_0 KV (confirmed no tg penalty), KV is 4x smaller → large ctx feasible.
    # KV estimate (16 attn layers, 4 KV heads, 256 head_dim, q4_0 = 0.5 bytes/elem):
    #   16 * 2 * 4 * 256 * ctx * 0.5 = 16384 * ctx bytes
    # Model = 20.6 GB, total VRAM = 32 GB → KV headroom ≈ 11.4 GB → max ctx ≈ 700K tokens
    # BUT GDN state also grows: ssm.inner_size=6144, state_size=128 per layer ~= 48 layers
    #   48 * 6144 * 128 * ctx * 2 bytes ≈ much larger — this is likely chunked, not full ctx
    # Safe test targets: 131072 (doubles current), 262144 (native max)
    {"name": "depth 131072 q4_0kv","var": "n_depth",   "val": 131072, "desc": "tg speed at 131K depth with q4_0 KV — tests 2x context, mostly O(1) on GDN layers", "vram": 0,
     "also": {"ctk": "q4_0", "ctv": "q4_0"}},
    {"name": "depth 262144 q4_0kv","var": "n_depth",   "val": 262144, "desc": "tg speed at native 262K depth with q4_0 KV — full context window test", "vram": 0,
     "also": {"ctk": "q4_0", "ctv": "q4_0"}},

    # mlock
    {"name": "no mlock",         "var": "mlock",       "val": False,  "desc": "allow OS to manage model pages — saves a tiny bit of RAM pressure", "vram": 0},
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
                        "tg512", "delta_tg512", "pp512", "outcome"])

def append_tsv(iter, name, var, val, tg512, delta, pp512, outcome):
    with open(RESULTS_TSV, "a", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow([iter, name, var, val, f"{tg512:.2f}", f"{delta:+.2f}", f"{pp512:.0f}", outcome])

# ── llama-bench evaluation ────────────────────────────────────────────────────

def build_bench_cmd(cfg: dict, extra: list) -> list:
    cmd = [BENCH_BIN,
           "--model", MODEL_PATH,
           "--n-gpu-layers", "999",
           "--flash-attn", "1",
           "-ctk", cfg["ctk"],
           "-ctv", cfg["ctv"],
           "--threads", str(cfg["threads"]),
           "--cpu-mask", "0xFF" if cfg["cpu_range"] == "0-7" else "0xFFFFF",
           "--cpu-strict", "1",
           "--ubatch-size", str(cfg["ubatch_size"]),
           "-b", str(cfg["batch_size"]),
           "--split-mode", cfg["split_mode"],
           "-p", "512",
           "-n", "512",
           "-d", str(cfg.get("n_depth", 0)),
           "-r", str(BENCH_REPS),
           "-o", "md",
    ]
    cmd.extend(extra)
    return cmd

def parse_bench_output(output: str) -> dict | None:
    tg512 = pp512 = None
    for line in output.splitlines():
        if "| " not in line or "model" in line or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        test_col = next((p for p in parts if p in ("tg512", "tg128", "pp512", "pp2048")), None)
        if not test_col:
            continue
        val_str = parts[-2] if parts[-1] == "" else parts[-1]
        try:
            val = float(val_str.split("±")[0].strip())
        except ValueError:
            continue
        if test_col == "tg512":  tg512 = val
        elif test_col == "pp512": pp512 = val

    if tg512 is None:
        return None
    return {"tg512": tg512, "pp512": pp512 or 0.0}

def run_bench(cfg: dict, extra: list) -> dict | None:
    cmd = build_bench_cmd(cfg, extra)
    log(f"  bench cmd: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=480, env=ENV)
        output = result.stdout + result.stderr
        if result.returncode != 0:
            log(f"  bench failed (exit {result.returncode})")
            log(f"  stderr: {result.stderr[-600:]}")
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
    # Kill the LISTENING server only (-sTCP:LISTEN avoids killing our own HTTP connections)
    subprocess.run("lsof -ti:8081 -sTCP:LISTEN | xargs -r kill -9", shell=True, capture_output=True)
    subprocess.run(["sudo", "systemctl", "stop", "llama-server"], capture_output=True)
    # Wait for VRAM to actually free (model is 20+ GB, OS needs a moment)
    for _ in range(15):
        time.sleep(1)
        try:
            out = subprocess.check_output(
                "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits",
                shell=True, text=True
            )
            used = sum(int(x.strip()) for x in out.strip().splitlines())
            if used < 5000:   # < 5 GB means model fully unloaded
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

    prompt = f"""## Current best config
tg512: {best['gen_tgs512']:.2f} tok/s | pp512: {best['prompt_pp512']:.0f} tok/s
extra flags: {best_extra}
ctk/ctv: {best['ctk']}/{best['ctv']}
ubatch: {best['ubatch_size']} | batch: {best['batch_size']}
threads: {best['threads']} | cpu_range: {best['cpu_range']} | split-mode: {best['split_mode']}

## Architecture notes
- Qwen3.6-35B-A3B: MoE (35B total, 3B active) with GDN/SSM hybrid (64 layers: 48 GDN + 16 attention)
- tg bottleneck = GDN sequential state update (NOT memory bandwidth)
- f16 vs q4_0 KV confirmed same tg speed on sibling model — KV quant irrelevant to tg
- VRAM headroom: ~3.6 GB (tight). Candidates with negative vram_delta_mib free space.
- GPU0: PCIe x8 Gen5 | GPU1: PCIe x4 Gen4

## Results so far
{history_str}

## Candidate experiments (each changes ONE variable)
{candidates_json}

## Task
Pick the ONE candidate most likely to improve tg512 given the GDN architecture constraints.
Prefer experiments that address CPU-GPU sync (poll), thread scheduling, or MoE expert batching.
Avoid candidates that have already been tried.
Respond with JSON only:
{{"index": <0-based>, "reasoning": "one sentence"}}"""

    try:
        r = requests.post(f"http://127.0.0.1:{PROD_PORT}/v1/chat/completions", json={
            "model": "qwen36moe",
            "messages": [
                {"role": "system", "content":
                    "You are an expert in llama.cpp inference optimization for MoE and SSM/GDN hybrid models. "
                    "Pick ONE experiment from the candidate list to maximize tg512 tok/s. "
                    "Respond with valid JSON only. No prose outside JSON."},
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

# ── Write best-flags script ───────────────────────────────────────────────────

def write_best_flags():
    cpu_mask = "0xFF" if best["cpu_range"] == "0-7" else "0xFFFFF"
    lines = [
        "#!/bin/bash",
        f"# Qwen3.6-35B-A3B — best from autoresearch",
        f"# tg512: {best['gen_tgs512']:.2f} tok/s  |  pp512: {best['prompt_pp512']:.0f} tok/s",
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
        f"  --threads-batch {best['threads']} \\",
        f"  --cpu-range 0-7 \\",
        f"  --cpu-range-batch 0-7 \\",
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

def main():
    init_tsv()
    log_section(f"AUTORESEARCH Qwen3.6-35B-A3B  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log(f"Baseline: tg512={BASELINE['gen_tgs512']} tok/s  pp512={BASELINE['prompt_pp512']:.0f} tok/s")
    log(f"Iterations: {MAX_ITERS}  |  One variable per experiment  |  Improve threshold: {IMPROVE_THRESHOLD} tok/s")
    log(f"Hardware: 2x RTX 5060 Ti (32 GB total), ~3.6 GB VRAM headroom at f16 KV\n")

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
            idx = int(pick.get("index", 0))
            if idx >= len(available): idx = 0
            candidate = available[idx]
            log(f"  LLM picked [{idx}]: {candidate['name']}")
            log(f"  Reasoning: {pick.get('reasoning', '')}")

        tried_names.add(candidate["name"])

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
            for k, v in candidate.get("also", {}).items():
                cfg[k] = v
        elif var == "n_depth":
            cfg["n_depth"] = val
            for k, v in candidate.get("also", {}).items():
                cfg[k] = v
        elif var == "mlock":
            cfg["mlock"] = val
        else:
            cfg[var] = val

        log(f"  Changing: {var} → {val}  extra: {extra}")

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
                       best["gen_tgs512"], 0.0, best["prompt_pp512"], "FAILED")
            continue

        delta = result["tg512"] - best["gen_tgs512"]
        improved = delta > IMPROVE_THRESHOLD
        outcome = "IMPROVED" if improved else "NO_CHANGE"

        log(f"  tg512: {result['tg512']:.2f} tok/s  (Δ{delta:+.2f})  pp512: {result['pp512']:.0f}")

        if improved:
            log(f"  NEW BEST: {result['tg512']:.2f} tok/s  (+{delta:.2f} from previous best)")
            best.update(cfg)
            best["gen_tgs512"]   = result["tg512"]
            best["prompt_pp512"] = result["pp512"]
            best_extra[:] = extra
            write_best_flags()
        else:
            log(f"  No improvement ({delta:+.2f}) — reverting to best")

        results_history.append({"name": candidate["name"], "delta": delta, "outcome": outcome})
        append_tsv(iteration+1, candidate["name"], var, str(val),
                   result["tg512"], delta, result["pp512"], outcome)

        log("")

    log_section("FINAL SUMMARY")
    log(f"Baseline:   tg512={BASELINE['gen_tgs512']:.2f} tok/s")
    log(f"Final best: tg512={best['gen_tgs512']:.2f} tok/s  (Δ{best['gen_tgs512']-BASELINE['gen_tgs512']:+.2f})")
    log(f"Best config: ctk/ctv={best['ctk']}  ubatch={best['ubatch_size']}  batch={best['batch_size']}  "
        f"threads={best['threads']}  max_depth_tested={best.get('n_depth',0)}  split={best['split_mode']}  extra={best_extra}")
    improved_list = [r for r in results_history if r["outcome"] == "IMPROVED"]
    log(f"Improvements found: {len(improved_list)}/{len(results_history)} experiments")
    for r in improved_list:
        log(f"  + {r['name']}: Δ{r['delta']:+.2f} tok/s")
    write_best_flags()

if __name__ == "__main__":
    import traceback, signal

    def _crash_handler(sig, frame):
        msg = f"FATAL: received signal {sig} — autoresearch killed externally"
        print(msg, flush=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"\n[FATAL] {msg}\n")
        sys.exit(1)

    for _sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(_sig, _crash_handler)

    with open(LOG_FILE, "a") as f:
        f.write(f"\n\n{'='*70}\n"
                f"# Autoresearch Qwen3.6-35B-A3B — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"{'='*70}\n")
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted by user")
        log_section("PARTIAL SUMMARY")
        log(f"Best reached: tg512={best['gen_tgs512']:.2f} tok/s")
        write_best_flags()
        sys.exit(0)
    except Exception as e:
        tb = traceback.format_exc()
        msg = f"FATAL EXCEPTION: {e}\n{tb}"
        print(msg, flush=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"\n[FATAL] {msg}\n")
        sys.exit(1)
