#!/usr/bin/env python3
"""
Autoresearch: GDN CUDA kernel fix for Blackwell (sm_120 / RTX 5060 Ti)

Problem:
  Qwopus3.6-27B-Coder (Gated DeltaNet hybrid, jackrong/llama.cpp fork) generates
  all '?' tokens (NaN logits, token ID 30) on RTX 5060 Ti (Blackwell sm_120) when
  fused_gdn_ar / fused_gdn_ch = true. Non-fused CPU math path works but is ~3.7 tok/s.

  Current state:
    - Build: llama.cpp b9625 (f05cf4676), CUDA 13.0, CMAKE_CUDA_ARCHITECTURES=120
    - Source: /home/dino/llama.cpp (jackrong fork of llama.cpp)
    - Binary: /home/dino/llama-build/bin/llama-server
    - Workaround: fused_gdn_ar=false; fused_gdn_ch=false in src/llama-context.cpp:200-201
    - Target speed: ideally 15-25 tok/s (2x RTX 5060 Ti 16GB each)
    - Current speed: ~3.7 tok/s (non-fused CPU math path via ggml ops on GPU)

  Key files:
    - /home/dino/llama.cpp/ggml/src/ggml-cuda/gated_delta_net.cu  (CUDA GDN kernel)
    - /home/dino/llama.cpp/src/models/qwen35.cpp                   (model def + GDN graph build)
    - /home/dino/llama.cpp/src/models/delta-net-base.cpp           (fused vs non-fused dispatch)
    - /home/dino/llama.cpp/src/llama-context.cpp                   (fused_gdn defaults, sched_reserve)

  Known facts about the kernel:
    - gated_delta_net.cu: 312 lines, kernel gated_delta_net_cuda<S_v, KDA, keep_rs>
    - S_v=128, KDA=false (GDA mode), H=48 v-heads, H_k=16 q/k-heads (GQA)
    - Grid: (H=48, n_seqs, 32), Block: (32, 4, 1)
    - ggml_cuda_pdl_sync() calls cudaGridDependencySynchronize() for sm_120
    - PDL (Programmatic Dependent Launch) is active on Blackwell when GGML_CUDA_PDL is set
    - State layout was changed in commit e95dae18d (June 10): offset = seq * H * S_v * S_v
    - All 16 template variants confirmed compiled in libggml-cuda.so

  Hypothesis backlog (not yet tested):
    1. PDL sync bug: cudaGridDependencySynchronize() may behave differently on sm_120
       if PDL is unintentionally active. Test: GGML_CUDA_PDL=0 env var.
    2. CUDA 13.0 codegen bug: sm_120 SASS may have a warp-shuffle or shared-mem issue
       in the GDN kernel. Test: compile with --ptxas-options=-v and check register usage.
    3. Blackwell warp-sync semantics: __syncwarp() or cooperative group sync may differ.
    4. Missing __syncthreads() between shared mem write and read in the kernel.
    5. Wrong template instantiation: maybe the dispatch picks wrong S_v or KDA template.

Goal of this research:
  Find the MINIMAL code change to /home/dino/llama.cpp that makes the fused GDN CUDA
  kernel produce correct tokens on RTX 5060 Ti (sm_120).

  Priority order:
    1. Search github.com/ggml-org/llama.cpp and github.com/jackrong for recent issues/PRs
       related to: GDN, DeltaNet, Blackwell, sm_120, RTX 5060
    2. Read the actual gated_delta_net.cu kernel and identify Blackwell-incompatible patterns
    3. Check if GGML_CUDA_PDL env var being unset (default) avoids the PDL sync issue
    4. Check CUDA warp/block sync primitives used in the kernel vs sm_120 requirements
    5. Look for any test or diagnostic that could confirm root cause without a full rebuild

  Deliverable: A specific, actionable code diff or env var change with confidence level.
  If a code change is found, also provide the exact shell commands to apply and rebuild.
"""

import subprocess
import sys
import time
from pathlib import Path

RESEARCH_PROMPT = """
You are researching a CUDA kernel bug affecting Qwopus (Gated DeltaNet hybrid model) on Blackwell RTX 5060 Ti (sm_120).

## The Problem
The fused GDN CUDA kernel in llama.cpp (jackrong fork) produces all '?' tokens (NaN logits) on RTX 5060 Ti when `fused_gdn_ar=true`. The non-fused CPU fallback path works correctly but is slow (~3.7 tok/s).

## Build Environment
- GPU: RTX 5060 Ti (Blackwell, sm_120, 16GB GDDR7 × 2)
- CUDA: 13.0 (/usr/local/cuda-13.0/bin/nvcc)
- CMAKE_CUDA_ARCHITECTURES=120
- llama.cpp fork: jackrong/llama.cpp, version b9625 (f05cf4676)
- Key file: /home/dino/llama.cpp/ggml/src/ggml-cuda/gated_delta_net.cu

## Current Workaround
In /home/dino/llama.cpp/src/llama-context.cpp lines 200-201:
```cpp
cparams.fused_gdn_ar = false; // DIAG: force non-fused path
cparams.fused_gdn_ch = false; // DIAG: force non-fused path
```
This bypasses the CUDA GDN kernel entirely and uses CPU-compatible ggml math ops.

## Research Tasks (in priority order)

1. Read the actual GDN CUDA kernel:
   `file_read /home/dino/llama.cpp/ggml/src/ggml-cuda/gated_delta_net.cu`
   Look for: __syncthreads(), __syncwarp(), shared memory patterns, PDL-related code,
   any Blackwell-specific issues.

2. Check for env vars that might fix it without a rebuild:
   - Does GGML_CUDA_PDL being unset (it is unset by default) affect anything?
   - Is there a GGML_CUDA_FORCE_* env var that could help?

3. Search for known issues:
   `web_search "llama.cpp GDN DeltaNet Blackwell sm_120 NaN tokens fix"`
   `web_search "gated_delta_net.cu RTX 5060 wrong output"`
   `web_search "llama.cpp b9625 GDN fused kernel bug"`
   `web_search site:github.com/ggml-org/llama.cpp "gated_delta_net" "blackwell" OR "sm_120"`

4. Check recent llama.cpp commits and PRs related to GDN:
   shell: `cd /home/dino/llama.cpp && git log --oneline --since='2026-05-01' -- ggml/src/ggml-cuda/gated_delta_net.cu`
   shell: `cd /home/dino/llama.cpp && git log --oneline --since='2026-05-01' -- src/models/delta-net-base.cpp src/models/qwen35.cpp`

5. Check ggml_cuda_pdl_sync behavior:
   file_read /home/dino/llama.cpp/ggml/src/ggml-cuda/common.cuh
   Look for ggml_cuda_pdl_sync() and whether it's triggered on sm_120 without GGML_CUDA_PDL env var.

6. Read delta-net-base.cpp to understand the dispatch:
   `file_read /home/dino/llama.cpp/src/models/delta-net-base.cpp`

7. Test the quick hypothesis: set GGML_CUDA_PDL=0 explicitly and restart — does that fix the '?' bug?
   shell: `systemctl --user show-environment | grep GGML || echo 'no GGML env vars set'`

## Deliverable
Provide a specific, minimal fix. Options in order of preference:
A) An env var to set in /home/dino/bin/qwopus-start.sh (no rebuild needed)
B) A 1-5 line code patch + rebuild commands
C) A different build flag for cmake

Be specific about file:line and exact change. Confidence level required for each suggestion.
"""

def run_frank_research(prompt: str, log_file: Path) -> str:
    """Submit research task to the frank harness via CLI."""
    cmd = [
        "/home/dino/harness/frank/run.sh", "run",
        "--persona", "interactive",
        "--prompt", prompt,
        "--frontier",
    ]

    print(f"[autoresearch-gdn] Submitting to harness frontier model...", flush=True)
    print(f"[autoresearch-gdn] Log: {log_file}", flush=True)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        output = result.stdout + result.stderr
        return output
    except subprocess.TimeoutExpired:
        return "TIMEOUT: research task exceeded 600s"
    except Exception as e:
        return f"ERROR: {e}"


def main():
    log_file = Path("/home/dino/inference-research/autoresearch-gdn-blackwell.log")

    print("=" * 70)
    print("GDN Blackwell Autoresearch")
    print("Target: fix fused GDN CUDA kernel on RTX 5060 Ti (sm_120)")
    print("=" * 70)
    print()

    start = time.time()
    result = run_frank_research(RESEARCH_PROMPT, log_file)
    elapsed = time.time() - start

    # Write log
    with open(log_file, "w") as f:
        f.write(f"# GDN Blackwell Autoresearch\n")
        f.write(f"# Run: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Elapsed: {elapsed:.1f}s\n\n")
        f.write(result)

    print(result)
    print(f"\n[autoresearch-gdn] Done in {elapsed:.1f}s. Log: {log_file}")


if __name__ == "__main__":
    main()
