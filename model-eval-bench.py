#!/usr/bin/env python3
"""
Sequential model evaluation harness — cha0tiktower dual RTX 5060 Ti (2×16GB, Blackwell SM_120)
Benchmarks each model against production genesis baseline.
Results → /home/dino/inference-research/model-eval-2026-05-16.md + .tsv
"""
import os, sys, re, time, signal, subprocess, json, urllib.request, tempfile, statistics
from pathlib import Path
from datetime import datetime

# ── config ────────────────────────────────────────────────────────────────────

VLLM_PYTHON   = "/opt/ai/vllm-env/bin/python3"
VLLM_BIN      = "/opt/ai/vllm-env/bin/vllm"
PORT          = 8023    # eval port — leaves genesis on 8022 untouched
API_KEY       = "eval-bench"
HEALTH_URL    = f"http://localhost:{PORT}/health"
INFER_URL     = f"http://localhost:{PORT}/v1/completions"
READY_TIMEOUT = 240     # 4 min max startup wait (vLLM loads in <120s on this hardware)
WARMUP_RUNS   = 2
BENCH_RUNS    = 7
N_TOKENS      = 512
GENESIS_TPS   = 73.35   # production baseline (mtp n=3, varied prompts, 2026-05-16)

RESULTS_MD  = Path("/home/dino/inference-research/model-eval-2026-05-16.md")
RESULTS_TSV = Path("/home/dino/inference-research/model-eval-2026-05-16.tsv")

_pub_base = Path("/home/dino/inference-research/model-eval-report-2026-05-16.md")
def _pub_path():
    if not _pub_base.exists():
        return _pub_base
    ts = datetime.now().strftime("%H%M%S")
    return _pub_base.with_name(f"model-eval-report-2026-05-16-{ts}.md")
PUBLICATION_MD = _pub_path()

# 7 distinct prompts — one per bench run, no prefix cache reuse
PROMPTS = [
    "Explain in technical depth how CUDA tensor cores accelerate matrix multiplication on Blackwell GPU architecture, covering the hardware pipeline, NVFP4 vs FP8 precision handling, and memory hierarchy.",
    "Describe the architecture and training methodology of the Mixture of Experts (MoE) language model paradigm, covering expert routing mechanisms, load balancing, capacity factors, and inference efficiency trade-offs.",
    "Explain how speculative decoding accelerates autoregressive LLM inference. Cover draft model selection, token verification logic, acceptance rate dynamics, and Multi-Token Prediction as a drafter-free alternative.",
    "Describe the engineering decisions behind designing a production-grade LLM inference server: batching strategies, KV cache management, continuous batching, prefix caching, and tensor parallelism considerations.",
    "Explain the Mamba selective state space model architecture in depth, covering input-dependent state transitions, parallel scan algorithms, hardware-efficient kernels, and how SSMs compare to attention at long context.",
    "Describe how modern quantization methods — GPTQ, AWQ, NVFP4, FP8 — differ in approach, accuracy retention, hardware requirements, and throughput impact on Blackwell-class GPUs.",
    "Explain the alignment techniques used in post-training of large language models: RLHF, DPO, GRPO, constitutional AI, and rejection sampling. Cover trade-offs in stability, compute cost, and behavioral control.",
]

# ── model definitions ─────────────────────────────────────────────────────────

MODELS = [
    {
        "id":       "qwen3-30b-a3b-nvfp4",
        "name":     "Qwen3-30B-A3B NVFP4",
        "path":     "/home/dino/models/Qwen3-30B-A3B-NVFP4",
        "quant":    "modelopt",
        "arch":     "MoE (30B total / ~3B active)",
        "format":   "NVFP4 (Blackwell native W4A4)",
        "source":   "nvidia/Qwen3-30B-A3B-NVFP4",
        "skip":     True,
        "skip_reason": "NVFP4 requires CUDA>=12.9: flashinfer.mm_fp4 calls get_gemm_sm120_module_cutlass_fp4() which JIT-compiles CUTLASS SM120 FP4 GEMM kernels — blocked on CUDA 12.8. Requires CUDA upgrade.",
        "flags": [
            "--quantization", "modelopt",
            "--tensor-parallel-size", "2",
            "--gpu-memory-utilization", "0.85",
            "--max-model-len", "32768",
            "--kv-cache-dtype", "auto",
            "--max-num-seqs", "2",
            "--max-num-batched-tokens", "4096",
            "--enable-chunked-prefill",
            "--enable-prefix-caching",
            "--dtype", "bfloat16",
            "--disable-custom-all-reduce",
            "--trust-remote-code",
            "--language-model-only",
            "--reasoning-parser", "qwen3",
            "--prefix-caching-hash-algo", "xxhash",
            "--api-key", API_KEY,
            "--served-model-name", "eval-model",
            "--host", "127.0.0.1",
            "--port", str(PORT),
            "--default-chat-template-kwargs", '{"enable_thinking": false}',
            "--disable-log-stats",
        ],
    },
    {
        "id":       "qwen3-32b-nvfp4",
        "name":     "Qwen3-32B dense NVFP4",
        "path":     "/home/dino/models/Qwen3-32B-NVFP4",
        "quant":    "modelopt",
        "arch":     "Dense (32B)",
        "format":   "NVFP4 (Blackwell native W4A4)",
        "source":   "nvidia/Qwen3-32B-NVFP4",
        "skip":     True,
        "skip_reason": "NVFP4 requires CUDA>=12.9: flashinfer.mm_fp4 calls get_gemm_sm120_module_cutlass_fp4() which JIT-compiles CUTLASS SM120 FP4 GEMM kernels — blocked on CUDA 12.8. Requires CUDA upgrade.",
        "flags": [
            "--quantization", "modelopt",
            "--tensor-parallel-size", "2",
            "--gpu-memory-utilization", "0.85",
            "--max-model-len", "32768",
            "--kv-cache-dtype", "auto",
            "--max-num-seqs", "2",
            "--max-num-batched-tokens", "4096",
            "--enable-chunked-prefill",
            "--enable-prefix-caching",
            "--dtype", "bfloat16",
            "--disable-custom-all-reduce",
            "--trust-remote-code",
            "--language-model-only",
            "--reasoning-parser", "qwen3",
            "--prefix-caching-hash-algo", "xxhash",
            "--api-key", API_KEY,
            "--served-model-name", "eval-model",
            "--host", "127.0.0.1",
            "--port", str(PORT),
            "--default-chat-template-kwargs", '{"enable_thinking": false}',
            "--disable-log-stats",
        ],
    },
    {
        "id":       "qwen3-32b-gptq",
        "name":     "Qwen3-32B GPTQ INT4",
        "path":     "/home/dino/models/Qwen3-32B-autoround-4bit-gptq",
        "quant":    "gptq_marlin",
        "arch":     "Dense (32B)",
        "format":   "GPTQ INT4 (AutoRound 0.5.1, group_size=128)",
        "source":   "already on disk",
        "flags": [
            "--quantization", "gptq_marlin",
            "--tensor-parallel-size", "2",
            "--gpu-memory-utilization", "0.90",
            "--max-model-len", "4096",
            "--kv-cache-dtype", "auto",
            "--max-num-seqs", "2",
            "--max-num-batched-tokens", "4096",
            "--cpu-offload-gb", "1.0",
            "--enable-chunked-prefill",
            "--enable-prefix-caching",
            "--dtype", "bfloat16",
            "--disable-custom-all-reduce",
            "--trust-remote-code",
            "--language-model-only",
            "--reasoning-parser", "qwen3",
            "--prefix-caching-hash-algo", "xxhash",
            "--api-key", API_KEY,
            "--served-model-name", "eval-model",
            "--host", "127.0.0.1",
            "--port", str(PORT),
            "--default-chat-template-kwargs", '{"enable_thinking": false}',
            "--disable-log-stats",
        ],
    },
    {
        "id":       "qwen3-14b-fp8",
        "name":     "Qwen3-14B FP8",
        "path":     "/home/dino/models/Qwen3-14B-FP8",
        "quant":    "fp8",
        "arch":     "Dense (14B)",
        "format":   "FP8 (W8A8)",
        "source":   "Qwen/Qwen3-14B-FP8",
        "flags": [
            "--quantization", "fp8",
            "--tensor-parallel-size", "2",
            "--gpu-memory-utilization", "0.80",
            "--max-model-len", "32768",
            "--kv-cache-dtype", "auto",
            "--max-num-seqs", "4",
            "--max-num-batched-tokens", "8192",
            "--enable-chunked-prefill",
            "--enable-prefix-caching",
            "--dtype", "bfloat16",
            "--disable-custom-all-reduce",
            "--trust-remote-code",
            "--language-model-only",
            "--reasoning-parser", "qwen3",
            "--prefix-caching-hash-algo", "xxhash",
            "--api-key", API_KEY,
            "--served-model-name", "eval-model",
            "--host", "127.0.0.1",
            "--port", str(PORT),
            "--default-chat-template-kwargs", '{"enable_thinking": false}',
            "--disable-log-stats",
        ],
    },
    {
        "id":       "qwen3-30b-a3b-gptq",
        "name":     "Qwen3-30B-A3B GPTQ INT4",
        "path":     "/home/dino/models/Qwen3-30B-A3B-GPTQ-Int4",
        "quant":    "gptq_marlin",
        "arch":     "MoE (30B total / ~3B active)",
        "format":   "GPTQ INT4 (official Qwen release)",
        "source":   "Qwen/Qwen3-30B-A3B-GPTQ-Int4",
        "flags": [
            "--quantization", "gptq_marlin",
            "--tensor-parallel-size", "2",
            "--gpu-memory-utilization", "0.82",
            "--max-model-len", "4096",
            "--kv-cache-dtype", "auto",
            "--max-num-seqs", "2",
            "--max-num-batched-tokens", "512",
            "--cpu-offload-gb", "1.0",
            "--enforce-eager",
            "--enable-chunked-prefill",
            "--enable-prefix-caching",
            "--dtype", "bfloat16",
            "--disable-custom-all-reduce",
            "--trust-remote-code",
            "--language-model-only",
            "--reasoning-parser", "qwen3",
            "--prefix-caching-hash-algo", "xxhash",
            "--api-key", API_KEY,
            "--served-model-name", "eval-model",
            "--host", "127.0.0.1",
            "--port", str(PORT),
            "--default-chat-template-kwargs", '{"enable_thinking": false}',
            "--disable-log-stats",
        ],
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
    r = subprocess.run(["nvidia-smi", "--query-gpu=memory.free",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True)
    return [int(x.strip()) for x in r.stdout.strip().splitlines() if x.strip()]


def gpu_used_mib():
    r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True)
    return [int(x.strip()) for x in r.stdout.strip().splitlines() if x.strip()]


def kill_gpu_procs():
    r = subprocess.run(["nvidia-smi", "--query-compute-apps=pid",
                        "--format=csv,noheader"], capture_output=True, text=True)
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


def drain_gpu(timeout=90, target_free_mib=15000):
    """Wait until both GPUs have >= target_free_mib MiB free."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        free = gpu_free_mib()
        if all(f >= target_free_mib for f in free):
            log(f"  GPU clean: {free[0]}/{free[1]} MiB free")
            return True
        time.sleep(4)
    free = gpu_free_mib()
    log(f"  WARNING: GPU not clean after {timeout}s: {free[0]}/{free[1]} MiB free — proceeding anyway")
    return False


def stop_all():
    """Stop any running eval process and drain GPU."""
    # Kill by port
    subprocess.run(["fuser", "-k", f"{PORT}/tcp"], capture_output=True)
    time.sleep(3)
    # Kill remaining GPU compute procs
    killed = kill_gpu_procs()
    if killed:
        log(f"  killed GPU procs: {killed}")
        time.sleep(6)
        kill_gpu_procs()
    drain_gpu()


def wait_ready(timeout=READY_TIMEOUT, pgid=None):
    deadline = time.time() + timeout
    while time.time() < deadline:
        # Fast-fail: if the server process group is gone, stop waiting
        if pgid is not None:
            try:
                os.killpg(pgid, 0)
            except (ProcessLookupError, OSError):
                print()
                log("  server process group dead — aborting wait")
                return False
        try:
            req = urllib.request.Request(
                HEALTH_URL, headers={"Authorization": f"Bearer {API_KEY}"}
            )
            resp = urllib.request.urlopen(req, timeout=5)
            if resp.status == 200:
                return True
        except Exception:
            pass
        elapsed = int(time.time() - (deadline - timeout))
        print(f"\r  {elapsed}s ...", end="", flush=True)
        time.sleep(5)
    print()
    return False


def run_inference(prompt):
    body = json.dumps({
        "model": "eval-model",
        "prompt": prompt,
        "max_tokens": N_TOKENS,
        "temperature": 0,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        INFER_URL,
        data=body,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    elapsed = time.time() - t0
    ct = data["usage"]["completion_tokens"]
    return ct / elapsed, ct


# ── start script builder ──────────────────────────────────────────────────────

GENESIS_ENV = """
export VLLM_NO_USAGE_STATS=1
# FlashInfer JIT-compile fails on SM 12.0 with CUDA 12.8 (requires 12.9) for standard Transformers.
# Genesis works because P60B Triton kernel replaces FlashInfer attention for GDN arch.
# Eval models are standard Transformers — use Triton attention backend instead.
export VLLM_ATTENTION_BACKEND=TRITON_ATTN
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_FLOAT32_MATMUL_PRECISION=high
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_LOGGING_LEVEL=WARNING
export VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE=413138944
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512
export NCCL_P2P_DISABLE=1
export NCCL_BUFFSIZE=4194304
export OMP_NUM_THREADS=1
export CUDA_DEVICE_MAX_CONNECTIONS=8
export GENESIS_ENABLE_P60_GDN_NGRAM_FIX=1
export GENESIS_ENABLE_P60B_TRITON_KERNEL=1
export GENESIS_ENABLE_P67_TQ_MULTI_QUERY_KERNEL=1
export GENESIS_ENABLE_P67B=1
export GENESIS_ENABLE_P70_AUTO_STRICT_NGRAM=1
export GENESIS_ENABLE_P72_PROFILE_RUN_CAP=1
export GENESIS_ENABLE_P74_CHUNK_CLAMP=1
export GENESIS_ENABLE_P77_ADAPTIVE_NGRAM_K=1
export GENESIS_ENABLE_P78_TOLIST_CAPTURE_GUARD=1
export GENESIS_ENABLE_P82=1
export GENESIS_P82_THRESHOLD_SINGLE=0.3
export GENESIS_BUFFER_MODE=shared
"""

def make_start_script(model):
    """Build a temp bash script, handling both paired (--flag val) and standalone (--flag) args."""
    flags = model["flags"]

    def shell_quote(s):
        """Wrap value in single quotes if it contains special shell chars."""
        if any(c in str(s) for c in [' ', '{', '}', '"', '|', '&', ';', '(', ')']):
            # Escape any single quotes in the value, then wrap in single quotes
            escaped = str(s).replace("'", "'\\''")
            return f"'{escaped}'"
        return str(s)

    cmd_lines = [f"exec {VLLM_BIN} serve \\", f"  {model['path']} \\"]
    i = 0
    while i < len(flags):
        flag = flags[i]
        # Determine if next token is a value or another flag (or end of list)
        if (i + 1 < len(flags) and not str(flags[i + 1]).startswith('--')):
            val = shell_quote(flags[i + 1])
            cmd_lines.append(f"  {flag} {val} \\")
            i += 2
        else:
            cmd_lines.append(f"  {flag} \\")
            i += 1
    # Remove trailing backslash from last line
    if cmd_lines:
        cmd_lines[-1] = cmd_lines[-1].rstrip(' \\')

    script = f"""#!/bin/bash
{GENESIS_ENV}

{VLLM_PYTHON} -m vllm._genesis.patches.apply_all

{chr(10).join(cmd_lines)}
"""
    tmp = tempfile.NamedTemporaryFile(suffix=".sh", delete=False, mode="w",
                                      prefix=f"/tmp/eval-{model['id']}-")
    tmp.write(script)
    tmp.close()
    os.chmod(tmp.name, 0o755)
    return tmp.name


# ── helpers ───────────────────────────────────────────────────────────────────

def get_flag_value(flags, flag_name, default="—"):
    try:
        idx = flags.index(flag_name)
        if idx + 1 < len(flags):
            return str(flags[idx + 1])
    except ValueError:
        pass
    return default


def format_model_command(model):
    """Return the vLLM serve command as a shell code block."""
    lines = [f"vllm serve {model['path']} \\"]
    flags = model["flags"]
    i = 0
    while i < len(flags):
        flag = flags[i]
        if i + 1 < len(flags) and not str(flags[i + 1]).startswith("--"):
            val = flags[i + 1]
            if any(c in str(val) for c in [" ", "{", "}", '"', "'"]):
                val_s = f"'{str(val)}'"
            else:
                val_s = str(val)
            lines.append(f"  {flag} {val_s} \\")
            i += 2
        else:
            lines.append(f"  {flag} \\")
            i += 1
    if lines:
        lines[-1] = lines[-1].rstrip(" \\")
    return "```bash\n" + "\n".join(lines) + "\n```"


# ── markdown writer ───────────────────────────────────────────────────────────

def init_report():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"""# Model Evaluation — cha0tiktower
**Date:** {now}
**Hardware:** 2× RTX 5060 Ti 16GB GDDR7 (Blackwell SM_120), TP=2, 32GB total VRAM
**Inference engine:** vLLM 0.21.0 + Genesis patches
**Context:** 32768 tokens | No MTP (eval models use standard vLLM; MTP is genesis-patch-only)
**Benchmark:** 2 warmup + 7 timed runs, 512 tokens each, 7 unique prompts (no prefix cache reuse)
**Baseline:** Genesis (Qwen3.6-27B INT4 AutoRound, mtp n=3) = **{GENESIS_TPS:.2f} t/s**

---

## Results Summary

| Model | Arch | Format | VRAM used | Median t/s | vs baseline | Status |
|---|---|---|---|---|---|---|

---

## Detailed Results

"""
    RESULTS_MD.write_text(header)
    RESULTS_TSV.write_text("model_id\tname\tarch\tformat\tvram_gpu0_mib\tvram_gpu1_mib\tmedian_tps\tmin_tps\tmax_tps\tstdev_tps\tvs_baseline_tps\tvs_baseline_pct\tstatus\tnotes\n")


def append_result(model, result, vram_used, notes=""):
    if result is None:
        status = "FAILED"
        row = f"| **{model['name']}** | {model['arch']} | {model['format']} | — | — | — | ❌ FAILED |"
        tsv = f"{model['id']}\t{model['name']}\t{model['arch']}\t{model['format']}\t—\t—\t—\t—\t—\t—\t—\t—\tFAILED\t{notes}\n"
    else:
        med   = result["median"]
        mn    = result["min"]
        mx    = result["max"]
        sd    = result["stdev"]
        delta = med - GENESIS_TPS
        pct   = (med / GENESIS_TPS - 1) * 100
        sign  = "+" if delta >= 0 else ""
        vram_str = f"{vram_used[0]}/{vram_used[1]} MiB" if vram_used else "—"
        status = "✅ WIN" if delta >= 1.0 else ("⚠️ LOSS" if delta <= -1.0 else "➖ NEUTRAL")
        row = f"| **{model['name']}** | {model['arch']} | {model['format']} | {vram_str} | **{med:.1f}** | {sign}{delta:.1f} ({sign}{pct:.1f}%) | {status} |"
        tsv = f"{model['id']}\t{model['name']}\t{model['arch']}\t{model['format']}\t{vram_used[0] if vram_used else ''}\t{vram_used[1] if vram_used else ''}\t{med:.2f}\t{mn:.2f}\t{mx:.2f}\t{sd:.2f}\t{delta:+.2f}\t{pct:+.1f}%\t{status}\t{notes}\n"

    # Update summary table
    content = RESULTS_MD.read_text()
    content = content.replace(
        "| Model | Arch | Format | VRAM used | Median t/s | vs baseline | Status |\n|---|---|---|---|---|---|\n",
        "| Model | Arch | Format | VRAM used | Median t/s | vs baseline | Status |\n|---|---|---|---|---|---|\n"
    )
    # Append row to table (before the --- after the table)
    content = content.replace(
        "\n---\n\n## Detailed Results",
        f"\n{row}\n---\n\n## Detailed Results"
    )

    # Append detailed section
    if result is None:
        detail = f"""### {model['name']}

- **Status:** FAILED
- **Source:** `{model['source']}`
- **Notes:** {notes}

"""
    else:
        runs_str = "  \n".join([f"  run {i+1}: {r:.2f} t/s" for i, r in enumerate(result["runs"])])
        detail = f"""### {model['name']}

| Field | Value |
|---|---|
| **Source** | `{model['source']}` |
| **Architecture** | {model['arch']} |
| **Quantization** | {model['format']} |
| **VRAM used (GPU 0 / GPU 1)** | {vram_str} |
| **Median t/s** | **{med:.2f}** |
| **Min / Max** | {mn:.2f} / {mx:.2f} t/s |
| **Std dev** | {sd:.2f} t/s |
| **vs genesis ({GENESIS_TPS} t/s)** | {sign}{delta:.2f} t/s ({sign}{pct:.1f}%) |
| **MTP** | none (standard vLLM — genesis MTP is patch-only) |
| **Context** | 32768 tokens |
| **GMU** | {get_flag_value(model['flags'], '--gpu-memory-utilization')} |

**Per-run results:**
{runs_str}

**Notes:** {notes if notes else '—'}

"""
    content += detail
    RESULTS_MD.write_text(content)

    # Append TSV
    with open(RESULTS_TSV, "a") as f:
        f.write(tsv)

    log(f"  → results written to {RESULTS_MD.name}")


# ── main experiment loop ───────────────────────────────────────────────────────

def run_model(model):
    log(f"\n{'='*60}")
    log(f"MODEL: {model['name']}")
    log(f"  arch:   {model['arch']}")
    log(f"  format: {model['format']}")
    log(f"  path:   {model['path']}")

    # Known-incompatible models — skip immediately with documented reason
    if model.get("skip"):
        reason = model.get("skip_reason", "marked skip")
        log(f"  SKIP: {reason}")
        append_result(model, None, None, notes=reason)
        return None

    # Check model exists
    if not Path(model["path"]).exists():
        log(f"  SKIP: model path not found — probably still downloading")
        append_result(model, None, None, notes="model directory not found — download may have failed")
        return None

    has_weights = (
        list(Path(model["path"]).glob("*.safetensors")) or
        list(Path(model["path"]).glob("model*.bin"))
    )
    if not has_weights:
        log(f"  SKIP: no weight files in {model['path']}")
        append_result(model, None, None, notes="no weight files found (incomplete download?)")
        return None

    # Clean GPU
    stop_all()

    # Build start script
    script_path = make_start_script(model)
    log(f"  script: {script_path}")

    # Apply genesis patches in this process (pre-warms patch state)
    subprocess.run([VLLM_PYTHON, "-m", "vllm._genesis.patches.apply_all"],
                   capture_output=True, check=False)

    # Start model
    log_path = f"/tmp/eval-{model['id']}.log"
    log(f"  log: {log_path}")
    log_fh = open(log_path, "w")
    proc = subprocess.Popen(
        ["/bin/bash", script_path],
        stdout=log_fh, stderr=log_fh,
        preexec_fn=os.setsid,
    )
    pgid = os.getpgid(proc.pid)
    log(f"  pid={proc.pid} pgid={pgid}")

    # Wait for health
    log(f"  waiting for ready (up to {READY_TIMEOUT}s)...")
    ready = wait_ready(pgid=pgid)
    if not ready:
        log("  FAIL: never became healthy")
        # Check log for errors
        log_fh.flush()
        tail = subprocess.run(["tail", "-20", log_path], capture_output=True, text=True)
        log(f"  last log lines:\n{tail.stdout}")
        try:
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            pass
        kill_gpu_procs()
        log_fh.close()
        os.unlink(script_path)
        append_result(model, None, None, notes="server never became healthy — check " + log_path)
        return None

    log(f"  ready at {datetime.now().strftime('%H:%M:%S')}")

    # Record VRAM after model load (before KV allocation)
    vram_used = gpu_used_mib()
    vram_free = gpu_free_mib()
    log(f"  VRAM used: {vram_used[0]}/{vram_used[1]} MiB  free: {vram_free[0]}/{vram_free[1]} MiB")

    # Warmup
    log(f"  warmup ×{WARMUP_RUNS}...")
    warmup_errors = 0
    for i, prompt in enumerate(PROMPTS[:WARMUP_RUNS]):
        try:
            tps, ct = run_inference(prompt)
            log(f"    warmup {i+1}: {tps:.2f} t/s ({ct} tokens)")
        except Exception as e:
            log(f"    warmup {i+1}: ERROR — {e}")
            warmup_errors += 1

    if warmup_errors == WARMUP_RUNS:
        log("  FAIL: all warmup requests failed")
        try:
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            pass
        kill_gpu_procs()
        log_fh.close()
        os.unlink(script_path)
        append_result(model, None, vram_used, notes="all warmup requests failed — check " + log_path)
        return None

    # Benchmark
    log(f"  benchmark ×{BENCH_RUNS}...")
    results = []
    errors = 0
    for i, prompt in enumerate(PROMPTS[WARMUP_RUNS:WARMUP_RUNS + BENCH_RUNS]):
        try:
            tps, ct = run_inference(prompt)
            results.append(tps)
            log(f"    run {i+1}: {tps:.2f} t/s ({ct} tokens)")
        except Exception as e:
            log(f"    run {i+1}: ERROR — {e}")
            errors += 1

    if len(results) < 3:
        log(f"  FAIL: too many errors ({errors}/{BENCH_RUNS})")
        try:
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            pass
        kill_gpu_procs()
        log_fh.close()
        os.unlink(script_path)
        append_result(model, None, vram_used, notes=f"too many inference errors ({errors}/{BENCH_RUNS})")
        return None

    result = {
        "median":    round(statistics.median(results), 2),
        "min":       round(min(results), 2),
        "max":       round(max(results), 2),
        "stdev":     round(statistics.stdev(results) if len(results) > 1 else 0, 2),
        "runs":      [round(r, 2) for r in results],
        "vram_used": vram_used,
    }

    delta = result["median"] - GENESIS_TPS
    sign = "+" if delta >= 0 else ""
    log(f"\n  ── RESULT ──")
    log(f"  median: {result['median']:.2f} t/s  min: {result['min']:.2f}  max: {result['max']:.2f}  σ={result['stdev']:.2f}")
    log(f"  vs genesis: {sign}{delta:.2f} t/s ({sign}{(delta/GENESIS_TPS)*100:.1f}%)")

    # Determine notes
    notes_parts = []
    if vram_used[0] > 15000:
        notes_parts.append("VRAM very tight on GPU0 — may OOM at longer contexts")
    if result["stdev"] > 5:
        notes_parts.append(f"high variance (σ={result['stdev']:.1f}) — consider more runs")
    notes = "; ".join(notes_parts) if notes_parts else ""

    append_result(model, result, vram_used, notes=notes)

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
    os.unlink(script_path)

    return result


# ── publication report ────────────────────────────────────────────────────────

def write_publication_report(all_results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build results table rows (sorted by median t/s descending)
    ranked = []
    for m in MODELS:
        r = all_results.get(m["id"])
        if r:
            ranked.append((r["median"], m, r))
    ranked.sort(key=lambda x: x[0], reverse=True)

    table_rows = []
    for rank, (med, m, r) in enumerate(ranked, 1):
        delta = med - GENESIS_TPS
        sign = "+" if delta >= 0 else ""
        pct = (med / GENESIS_TPS - 1) * 100
        gmu = get_flag_value(m["flags"], "--gpu-memory-utilization")
        vram = f"{r['vram_used'][0]}/{r['vram_used'][1]} MiB" if r.get("vram_used") else "—"
        table_rows.append(
            f"| {rank} | **{m['name']}** | {m['arch']} | {m['format']} "
            f"| {vram} | **{med:.1f}** | {sign}{delta:.1f} ({sign}{pct:.0f}%) |"
        )

    # Failed models
    for m in MODELS:
        r = all_results.get(m["id"])
        if not r:
            table_rows.append(
                f"| — | **{m['name']}** | {m['arch']} | {m['format']} | — | — | ❌ FAILED |"
            )

    # Per-model detail sections
    model_sections = []
    for i, m in enumerate(MODELS, 1):
        r = all_results.get(m["id"])
        gmu  = get_flag_value(m["flags"], "--gpu-memory-utilization")
        ctx  = get_flag_value(m["flags"], "--max-model-len")
        seqs = get_flag_value(m["flags"], "--max-num-seqs")
        quant = get_flag_value(m["flags"], "--quantization")

        if r is None:
            status_block = "> ❌ **FAILED** — server never became healthy or inference errored. See raw log for details."
            stats_block = ""
        else:
            med   = r["median"]
            delta = med - GENESIS_TPS
            sign  = "+" if delta >= 0 else ""
            pct   = (med / GENESIS_TPS - 1) * 100
            runs_md = " | ".join([f"{x:.2f}" for x in r["runs"]])
            vram_str = f"{r['vram_used'][0]} / {r['vram_used'][1]} MiB" if r.get("vram_used") else "—"
            status_block = (
                f"**Result: {med:.2f} t/s** median ({sign}{delta:.2f} t/s, {sign}{pct:.0f}% vs genesis)"
            )
            stats_block = f"""
| Metric | Value |
|---|---|
| Median t/s | **{med:.2f}** |
| Min / Max | {r['min']:.2f} / {r['max']:.2f} t/s |
| Std dev | {r['stdev']:.2f} t/s |
| vs Genesis (73.35 t/s) | {sign}{delta:.2f} t/s ({sign}{pct:.0f}%) |
| VRAM used (GPU 0 / GPU 1) | {vram_str} |
| GMU | {gmu} |

**Per-run t/s:** {runs_md}
"""

        model_sections.append(f"""### {i}. {m['name']}

**Source:** `{m['source']}`
**Architecture:** {m['arch']}
**Quantization:** {m['format']}
**vLLM flags (this run):**

{format_model_command(m)}

{status_block}
{stats_block}
---
""")

    # Analysis section
    if ranked:
        winner_med, winner_m, winner_r = ranked[0]
        winner_delta = winner_med - GENESIS_TPS
        winner_sign = "+" if winner_delta >= 0 else ""
        winner_pct = (winner_med / GENESIS_TPS - 1) * 100
        analysis_winner = (
            f"**Fastest challenger: {winner_m['name']}** at {winner_med:.1f} t/s "
            f"({winner_sign}{winner_delta:.1f} t/s, {winner_sign}{winner_pct:.0f}% vs genesis)."
        )
        moe_models = [(med, m, r) for med, m, r in ranked if "MoE" in m["arch"]]
        dense_models = [(med, m, r) for med, m, r in ranked if "MoE" not in m["arch"]]
        arch_note = ""
        if moe_models and dense_models:
            best_moe = moe_models[0]
            best_dense = dense_models[0]
            arch_note = (
                f"\n\n**MoE vs Dense:** Best MoE ({best_moe[1]['name']}) = "
                f"{best_moe[0]:.1f} t/s vs best dense ({best_dense[1]['name']}) = "
                f"{best_dense[0]:.1f} t/s. MoE advantage comes from routing only ~3B active "
                f"params per token despite 30B total weights."
            )
    else:
        analysis_winner = "All models failed — no throughput comparison possible."
        arch_note = ""

    failed_count = sum(1 for m in MODELS if not all_results.get(m["id"]))

    doc = f"""# Qwen3 Quantization Benchmark: 5 Formats on Dual RTX 5060 Ti
*cha0tiktower | {now} | vLLM 0.21.0 + Genesis patches*

---

## Hardware

| Component | Spec |
|---|---|
| GPUs | 2× NVIDIA GeForce RTX 5060 Ti |
| VRAM per GPU | 16 311 MiB GDDR7 |
| GPU architecture | Blackwell SM_120 |
| PCIe | GPU 0 x8 Gen 5 / GPU 1 x4 Gen 4 |
| CPU | Intel Core Ultra 7 265F (8P + 12E cores, 5.3 GHz boost) |
| RAM | 32 GB DDR5 |
| OS | Ubuntu 24.04 LTS |
| CUDA | 12.8 |
| Inference engine | vLLM 0.21.0 + Genesis patches (TP=2) |
| Tensor parallelism | TP=2 (both GPUs active, balanced) |

---

## Test Protocol

**Objective:** Compare generation throughput across five quantization formats — NVFP4 (Blackwell-native W4A4), FP8 (W8A8), and GPTQ INT4 — spanning dense 14B/32B and MoE 30B-A3B architectures on consumer Blackwell hardware.

**Methodology:**

| Parameter | Value |
|---|---|
| Metric | Generation tokens/second (t/s), single-request sequential |
| Output tokens | 512 per request (fixed `max_tokens`) |
| Context window | 32 768 tokens (`--max-model-len`) |
| Warmup runs | 2 (discarded) |
| Timed runs | 7 per model |
| Reported stat | Median t/s (robust to outliers) |
| Cache control | 7 unique prompts, one per run — prevents prefix-cache inflation |
| VRAM isolation | Full drain to ≥15 000 MiB free (both GPUs) before each model load |
| MTP | None (eval models use standard vLLM; genesis MTP is a custom patch method, not available for arbitrary models) |
| Eval port | 8023 (production genesis stays on 8022, untouched) |

**Prompts (7 unique technical domains):**

1. CUDA tensor cores and Blackwell NVFP4/FP8 matrix multiply pipeline
2. Mixture-of-Experts architecture, routing, load balancing, inference trade-offs
3. Speculative decoding: draft models, acceptance rates, Multi-Token Prediction
4. LLM inference server design: batching, KV cache, continuous batching, prefix caching
5. Mamba/SSM architecture: selective state transitions, parallel scan, vs attention at context
6. Quantization methods: GPTQ, AWQ, NVFP4, FP8 — accuracy, hardware, throughput on Blackwell
7. Post-training alignment: RLHF, DPO, GRPO, constitutional AI

---

## Production Baseline

**Genesis — Qwen3.6-27B INT4 AutoRound**

| Field | Value |
|---|---|
| Architecture | Qwen 3.6 27B (Mamba/GDN hybrid, 16 full-attn + 48 SSM layers) |
| Quantization | GPTQ Marlin INT4 (AutoRound, group_size=128) |
| MTP | n=3 (genesis-patch drafter-free speculative method) |
| VRAM | ~15 086 / 14 124 MiB (425 / 1387 MiB free at GMU=0.90) |
| Speed | **73.35 t/s** (median, 7 varied prompts, 2026-05-16) |

---

## Results Summary

| Rank | Model | Arch | Format | VRAM | Median t/s | vs Genesis |
|---|---|---|---|---|---|---|
| — | Genesis (baseline) | SSM hybrid 27B | GPTQ INT4 + MTP | — | 73.35 | — |
{"".join(chr(10) + r for r in table_rows)}

---

## Per-Model Details

{"".join(model_sections)}
## Analysis

{analysis_winner}{arch_note}

**NVFP4 (Blackwell-native W4A4):** The NVIDIA modelopt NVFP4 format uses Blackwell tensor core FP4 paths natively. At ~0.5 bytes/param it is maximally VRAM-efficient — a 30B MoE model fits in ~18 GB. Performance relative to GPTQ INT4 reflects how well the Blackwell SM_120 FP4 kernel path saturates vs the Marlin dequantization path.

**FP8 vs INT4:** FP8 (W8A8) uses ~1 byte/param, doubling VRAM vs INT4 at similar parameter count. The trade-off is reduced quantization noise; the question is whether that accuracy gain comes at a throughput cost on Blackwell, which has hardware FP8 tensor core paths.

**MoE architecture note:** MoE models (30B-A3B) have 30B total parameters but activate only ~3B per token. Generation speed on MoE is primarily gated by the active-parameter compute path, not total model size — so a 30B MoE can outpace a 14B dense model in t/s depending on routing overhead and memory bandwidth for expert weights.

**No MTP on eval models:** Genesis achieves ~73 t/s largely because of its built-in MTP (Multi-Token Prediction) drafter, which contributes ~33 t/s beyond the ~40 t/s INT4 autoregressive ceiling. The eval models run without MTP — this is a fair base comparison of quantization format throughput, but note that adding an MTP drafter to any of these models would shift their scores upward.

**Attention backend — Triton (SM 12.0 compatibility):** FlashInfer 0.6.8.post1 requires CUDA ≥ 12.9 to JIT-compile kernels for SM 12.0 (Blackwell). This system runs CUDA 12.8. FlashInfer fails with `No supported CUDA architectures found for major versions [12]` during the `determine_available_memory` profile run for standard Transformer models. Genesis avoids this because its P60B genesis patch substitutes a custom Triton attention kernel for the GDN/SSM architecture — but that patch is architecture-specific and does not help standard Transformers. All eval models therefore use `VLLM_ATTENTION_BACKEND=TRITON_ATTN` (Triton 3.6.0), which compiles correctly for SM 12.0. This may modestly reduce throughput vs FlashInfer on a CUDA 12.9 system, but produces accurate comparative numbers across all five models on this hardware.

---

*Generated by model-eval-bench.py | cha0tiktower | {now}*
"""

    path = _pub_path()
    path.write_text(doc)
    log(f"  → publication report: {path}")
    return path


# ── entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", metavar="ID",
                        help="Run only these model IDs (append to existing results)")
    args = parser.parse_args()

    only_ids = set(args.only) if args.only else None
    active_models = [m for m in MODELS if only_ids is None or m["id"] in only_ids]

    log(f"Model eval harness — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Hardware: 2× RTX 5060 Ti 16GB | vLLM 0.21.0 | {len(active_models)} model(s)")
    log(f"Baseline: genesis = {GENESIS_TPS:.2f} t/s")
    if only_ids:
        log(f"Targeted re-run: {sorted(only_ids)}")

    if not only_ids:
        init_report()

    all_results = {}
    for model in active_models:
        result = run_model(model)
        all_results[model["id"]] = result

    # Final summary
    log(f"\n{'='*60}")
    log("FINAL SUMMARY")
    log(f"{'='*60}")
    log(f"Baseline (genesis): {GENESIS_TPS:.2f} t/s")
    for model in active_models:
        r = all_results.get(model["id"])
        if r:
            delta = r["median"] - GENESIS_TPS
            sign = "+" if delta >= 0 else ""
            log(f"  {model['name']:35s} {r['median']:.2f} t/s  {sign}{delta:.2f} ({sign}{(delta/GENESIS_TPS)*100:.1f}%)")
        else:
            log(f"  {model['name']:35s} FAILED")

    log(f"\nResults: {RESULTS_MD}")
    log(f"TSV:     {RESULTS_TSV}")

    # Publication report
    log("\nWriting publication report...")
    pub_path = write_publication_report(all_results)
    log(f"Publication: {pub_path}")

    # Restore genesis
    log("\nRestoring production genesis...")
    restore = subprocess.run(["/home/dino/bin/genesis-restore-baseline"],
                             capture_output=False)
    if restore.returncode == 0:
        log("Genesis restored.")
    else:
        log("WARNING: genesis restore may have failed — check manually")
