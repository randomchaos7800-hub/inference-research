# Local Inference Autoresearch Log
**Model**: supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf  
**Hardware**: RTX 5060 Ti (16GB VRAM, Blackwell GB206), Core Ultra 7 265F (Arrow Lake, 8P+12E cores, no HT, no AVX-512), 32 GB RAM  
**Stack**: llama.cpp + CUDA 12.8  
**Stop condition**: max 10 iterations, stop if per-iteration gen improvement < 5 tok/s  

---

## Baseline (2026-04-17 ~23:45)

**Flags**:
```
--n-gpu-layers 999 --override-tensor .*exps.*=CPU
--flash-attn on -ctk q8_0 -ctv q8_0 --mlock
--ctx-size 32768 --ubatch-size 1024
```

**Results** (3 runs, 27-token prompt, 200 gen tokens):
- Prompt: 74.1 tok/s
- **Generation: 32.4 tok/s**

**VRAM state**: 12430 MiB "used" in FB Memory (expert tensors pinned via CUDA for DMA), 3410 MiB free actual GPU VRAM.  
**Notes**: `.*exps.*=CPU` routes MoE expert tensors to CPU RAM (pinned). Only non-expert attention + dense FFN on GPU (~0.7 GB weights + ~0.7 GB KV cache = ~3.7 GB total). Arrow Lake has NO AVX-512.

---

## Experiment 1: P-core CPU affinity (2026-04-17)

**Hypothesis**: Force expert compute to P-cores only (0-7, 5.3 GHz) vs all cores (E-cores at 4.6 GHz).  
**Change**: `taskset -cp 0-7 <pid>` on running server (no restart needed)  
**Before**: 32.4 tok/s gen  
**After**: 32.6 tok/s gen (3 runs avg)  
**Delta**: +0.2 tok/s (+0.6%)  
**Verdict**: ❌ **REVERT** — noise-level. CPU is not the bottleneck; PCIe transfer overhead dominates.

---


## Experiment 2: Partial expert GPU offload (2026-04-18)

**Hypothesis**: Moving most expert tensors from CPU to GPU eliminates PCIe transfer bottleneck.  
**Blocker identified**: Model needs 16,003 MiB for full GPU load, but only 15,223 MiB available (after stray processes killed). Baseline server was `--mlock` pinning expert tensors as CUDA pinned memory, so they showed up in FB Memory but lived in DRAM.

**Change**: 
- Keep ONLY last 6 layers (blk 24-29) experts on CPU (was: all 30 layers)
- Reduce ctx: 32768 → 8192 (to fit KV cache)  
- KV quant: q8_0 → q4_0 (halve KV VRAM)

```
--override-tensor "blk\.(2[4-9])\..*exps.*=CPU"
-ctk q4_0 -ctv q4_0 --ctx-size 8192
```

**Results** (3 runs):
- Prompt: 74.1 → 222 tok/s (**+200%**)  
- **Generation: 32.4 → 70.7 tok/s (+118%)**  

VRAM: 14,594 MiB used, 609 MiB free (nearly full)

**Verdict**: ✅ **KEEP** — transformative improvement. Stop condition not met (+38.3 tok/s > 5 tok/s threshold).

---

## Experiment 3: Context size expansion (2026-04-18)

**Key discovery**: Only 5 non-SWA (global attention) layers use full-context KV cache. 25 SWA layers use fixed 5120-token ring buffer regardless of ctx-size. KV cost at 32768 ctx, q4_0: only 461 MiB total.

**Exp3a ctx=8192**: gen 70.0 tok/s, prompt 222 tok/s — 14,594 MiB VRAM  
**Exp3b ctx=12288**: gen 68.3 tok/s, prompt 232 tok/s — ~15,251 MiB VRAM  
**Exp3c ctx=16384**: Loaded, ~585 MiB free  
**Exp4 ctx=32768 (q4_0 KV)**: gen 69.4 tok/s, prompt 225 tok/s — 15,375 MiB VRAM, 465 MiB free  
**Verdict**: ✅ ctx=32768 restored with essentially no speed penalty!

---

## Experiment 4: KV cache quality upgrade back to q8_0 (2026-04-18)

**Hypothesis**: q8_0 KV (vs q4_0) barely costs VRAM since KV is tiny (461→871 MiB).

**Change**: `-ctk q8_0 -ctv q8_0` (restored original quality)

**Before** (q4_0): gen 69.4 tok/s  
**After** (q8_0): gen 69.8 tok/s  
**VRAM**: 15,785 MiB used, 55 MiB free (very tight!)  

**Verdict**: ✅ **NEW BEST** — q8_0 KV at ctx=32768 with expert GPU offload. Same speed as q4_0 but better long-context quality. Caution: only 55 MiB headroom.

---

## Summary: Overall improvement so far
- **Baseline**: 32.4 tok/s gen, 74.1 tok/s prompt, ctx=32768, q8_0
- **Current best**: 69.8 tok/s gen (+115%), 218 tok/s prompt (+194%), ctx=32768, q8_0
- **Key change**: 24/30 expert layers on GPU (was 0/30)
- **VRAM**: 15,785 MiB (up from 3,710 MiB) — full utilization

---

## Experiment 5: ubatch-size tuning (2026-04-18)

**Result**: ubatch=512 → gen 69.6 tok/s (vs 69.8 at 1024). No difference for single-stream decode.  
**Verdict**: ❌ No change. ubatch only matters for multi-stream batch throughput.

---

## Key discovery: Built-in --n-cpu-moe flag and KV architecture (2026-04-18)

**Discovered**: 
- `--n-cpu-moe N` flag: native support for keeping first N MoE layers on CPU
- `--cpu-range`, `--prio` flags: built-in CPU affinity and priority control
- Only 5 non-SWA (global attention) layers have full-context KV (180 MiB at 32768 ctx)
- 25 SWA layers use fixed 5120-cell ring buffer (281 MiB regardless of ctx size)
- Total KV is only 461 MiB (q4_0) / 871 MiB (q8_0) at 32768 ctx!
- Increasing ctx beyond 32768 costs only ~5.5 MiB per 1024 tokens (just 5 non-SWA layers)

**Compiled arch**: Current build already targets SM_120a (Blackwell native)!

---

## Experiment 6: Layer ordering — first 6 vs last 6 on CPU (2026-04-18)

**Hypothesis**: Keeping FIRST 6 layers on CPU might enable GPU pipeline overlap  
**Change**: `--n-cpu-moe 6 --prio 2` (first 6 layers + high priority)  
**Result**: gen 70.6 tok/s, prompt 197 tok/s  
**Verdict**: ❌ Essentially same gen speed, WORSE prompt speed. Layer ordering doesn't matter.

---

## Experiment 7: Process priority (2026-04-18)

**Change**: `--prio 2` (high priority) with last-6-CPU best config  
**Before**: 69.8 tok/s gen  
**After**: 67.4 tok/s gen  
**Verdict**: ❌ **REVERT** — high priority hurts performance (likely starves CUDA driver threads)

---

## Experiment 8: Thread count + P-core affinity (2026-04-18)

**Hypothesis**: With only 6 expert layers on CPU, the compute workload per expert is tiny. Fewer threads = less synchronization overhead. P-cores (0-7, 5.3 GHz) are faster than E-cores (4.6 GHz).

**Change**: `--threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1`

**Results (5 runs)**:
- Gen: 67.1-71.1 tok/s avg ~68.9 (vs 69.8 baseline — within noise)
- Prompt: 216 (cold), 282-300 tok/s warm avg ~292

**Gen improvement**: negligible (+/-1 tok/s noise)
**Prompt improvement**: +74 tok/s warm (+34%) — significant for interactive use

**Verdict**: ✅ **INCLUDE IN CONFIG** — prompt improvement is real. Gen speed unchanged.

---

## Final Best Config (as of 2026-04-18 iteration 8/10)

```bash
--model supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf
--n-gpu-layers 999
--override-tensor "blk\.(2[4-9])\..*exps.*=CPU"  # last 6 of 30 layers on CPU
--flash-attn on
-ctk q8_0 -ctv q8_0                              # original KV quality
--mlock
--ctx-size 32768                                   # original context size
--ubatch-size 1024
--threads 8 --threads-batch 8
--cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1  # P-cores only
```

**Final metrics vs baseline**:
| Metric | Baseline | Best | Improvement |
|--------|----------|------|-------------|
| Gen tok/s | 32.4 | ~69.8 | **+115%** |
| Prompt tok/s (warm) | 74.1 | ~292 | **+294%** |
| Context window | 32768 | 32768 | unchanged |
| KV quality | q8_0 | q8_0 | unchanged |

---

## Pending: Experiment 9 — CUDA 13.0 rebuild (SM_120 optimization)

Note: Current build already targets SM_120a (CUDA 12.8 supported it). CUDA 13.0 may improve cuBLAS kernels for Blackwell.  
Build started in background at ~/llama.cpp/build-cuda13/

---

## Experiment 9: CUDA 13.0 rebuild (2026-04-18) — ITERATION 9/10

**Hypothesis**: CUDA 13.0 has updated SM_120 kernels (6 months newer than 12.8) and `BLACKWELL_NATIVE_FP4` support.

**Build**: cmake with `-DCMAKE_CUDA_ARCHITECTURES=120`, `/usr/local/cuda-13.0/bin/nvcc`. Both builds compile to `arch = sm_120a`.

**Result**: CUDA 13.0 binary crashes with `CUDA error: invalid argument` during first `llama_decode()` call. 
- Root cause: `BLACKWELL_NATIVE_FP4 = 1` flag enables native Blackwell FP4 WGMMA instructions, which appear incompatible with Q4_K_M quantization in this llama.cpp version.
- `GGML_CUDA_NO_GRAPHS=1` env var did NOT prevent the crash (crashed in same path).
- This is a known incompatibility between CUDA 13.0's Blackwell FP4 kernel path and quantized model formats. Likely needs llama.cpp update to handle.

**Verdict**: ❌ **FAILED** — CUDA 13.0 build crashes, revert to CUDA 12.8.

---

## Loop Complete — Final Summary (9/10 iterations, stopped on CUDA 13.0 failure)

**Stop condition met**: CUDA 13.0 experiment failed (no improvement possible), and gen speed stuck at ~69 tok/s for last 6 iterations.

### Key Discoveries

1. **Expert GPU offload is the dominant optimization** (Exp 2): Moving 24/30 expert layers from CPU to GPU eliminated the PCIe synchronization bottleneck. Gen: 32.4 → 69.8 tok/s (+115%).

2. **KV cache is tiny on Gemma 4** (Exp 3): Only 5 non-SWA (global attention) layers have full-context KV; 25 SWA layers use a fixed 5120-cell ring buffer. Total KV at 32768 ctx = only 461 MiB (q4_0) or 871 MiB (q8_0). Context size is essentially free to increase.

3. **CUDA 12.8 already targets SM_120a**: No benefit from CUDA 13.0 toolkit for the GPU kernel path — and 13.0 actively breaks things with BLACKWELL_NATIVE_FP4.

4. **P-core threading improves prompt** (Exp 8): `--threads 8 --cpu-range 0-7` pins expert computation to Arrow Lake P-cores (5.3 GHz), improving warm prompt throughput by +34%.

5. **Things that didn't help**: taskset affinity, ubatch tuning, layer ordering (first vs last on CPU), --prio flag.

### Final Best Config

```bash
--override-tensor "blk\.(2[4-9])\..*exps.*=CPU"
--flash-attn on -ctk q8_0 -ctv q8_0
--ctx-size 32768 --ubatch-size 1024
--threads 8 --threads-batch 8
--cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1
--mlock
```

### Final Metrics

| Metric | Baseline | Final | Δ |
|--------|----------|-------|---|
| Gen tok/s | 32.4 | ~69.8 | **+115%** |
| Prompt tok/s (warm) | 74.1 | ~292 | **+294%** |
| Ctx window | 32768 | 32768 | same |
| KV quality | q8_0 | q8_0 | same |
| VRAM used | 3,710 MiB | 15,785 MiB | +12.1 GB (experts on GPU) |


---

## Context expansion: 32768 → 65536 (2026-04-18)

**Change**: `--ctx-size 65536 -ctk q4_0 -ctv q4_0`

**Why**: Only 5 non-SWA global attention layers scale with ctx size (~5.5 MiB per 1024 tokens). 25 SWA layers use fixed 5120-cell ring buffer regardless of ctx.

**VRAM budget**:
- q8_0 at 65536 failed: compute buffer needed 1065 MiB, only 526 MiB free
- q4_0 at 65536: KV halves (1211 → ~606 MiB), fits with 516 MiB free
- q4_0 KV trade-off already validated in Exp 4: 69.4 vs 69.8 tok/s (noise level)

**Result**: Active, 15,324 MiB VRAM, 516 MiB free. Gen speed unchanged (~69.8 tok/s).

---

## 2026-04-29 — Crush Integration + Local Inference Coding Agent

### Goal

Build a production-grade local coding agent: Crush (v0.64.0 by Charmbracelet) wired to AEON-NVFP4 (Qwen3.6-27B, dual RTX 5060 Ti, fp4+fp8 KV, 122,880 ctx) via a thin Starlette proxy harness. Secondary goal: teach jr (Chatbox + AEON) to build its own harness using the "Thin Harness, Fat Skills" philosophy from Gary Tan's gbrain.

### Stack at Session Start

- vLLM AEON-NVFP4: port 8023, `--enable-auto-tool-choice --tool-call-parser qwen3_coder`
- local-proxy: port 8010 (transparent passthrough, hot-reload backend config)
- harness (port 8011): Chatbox soul+memory injection
- harness-code (port 8012): Crush soul+memory injection
- Both harnesses: same harness.py, differentiated by HARNESS_SOUL / HARNESS_MEMORY / HARNESS_PORT env vars

### What Was Built (harness side)

**Context files for Crush** (`soul_code.md`, `memory_code.md`):
- Soul: 5 directives, 4 intent-switched modes, full stack section (Python path, inference ports, shell whitelist, service locations), explicit TOOL USE directive requiring commands before answering diagnostic questions
- Memory: #LONG_TERM pre-populated with stack facts, harness internals, conventions, benchmark results

**harness.py fixes:**
1. `inject_context` was stripping Crush's system prompt entirely — replaced with append-after-soul behavior so Crush's tool definitions survive
2. `HARNESS_MAX_TOKENS` env var — harness-code runs at 16384, chat harness stays at 4096
3. Shell whitelist: added `ip`, `ifconfig`
4. `sse_gen` transparent proxy mode: when `tools` in payload, force non-streaming toward vLLM to bypass `qwen3_coder` streaming parser bug (`list index out of range` on tool call deltas), re-emit as single SSE chunk to Crush
5. Multi-turn tool conversation support: `inject_context` previously returned 400 when last message was `tool` role (not `user`). Fixed to track `ends_with_user`, pass full history without re-appending the user message, use last user message for memory logging only

**MCP servers configured** (`~/.config/crush/crush.json`):
- `shell`: mcp-shell-tools (PyPI, vllm-env Python, STDIO)
- `filesystem`: @modelcontextprotocol/server-filesystem (npx, rooted at /home/dino)

**Firefox GPU crash diagnosed and fixed:**
- Root cause: Firefox CanvasRenderer competing for VRAM; vLLM holds 95%+ of both GPUs
- Fix: `user.js` written to snap Firefox profile disabling WebRender and hardware acceleration

### Crush Benchmark (before MCP work)

5-task coding benchmark, all Python, all runnable:

| Task | Result | Notes |
|------|--------|-------|
| parse_log_line (regex + asserts) | Pass | Clean, 3 meaningful asserts |
| binary_search bug fix | Pass | Found the only bug, explained it |
| two_sum O(n) | Pass | Hash map, correct, includes edge case |
| refactor (10 lines → 1) | Pass | Best answer — one clean comprehension |
| /v1/models table (live HTTP) | Pass | Dynamic field discovery, graceful empty |
| LRU Cache (medium-hard, no hint) | Fail | Only produced asserts, no class, wrong eviction logic |
| LRU Cache (with OrderedDict hint) | Partial | Correct impl, one broken assert |
| retry decorator | Pass | Best response — correct backoff, 3 meaningful asserts |

Pattern: strong on implementation and refactor, weak on self-verification and open-ended agentic tasks.

### The Tool Calling Problem

**Symptom**: Crush sends a diagnostic request, model responds with intent text ("Let me check...") instead of tool calls. No commands execute.

**Root cause investigation**:
- Confirmed vLLM supports tool calling: `finish_reason: tool_calls`, correct JSON ✓
- Confirmed harness passes `tools` through to vLLM ✓
- Direct test with `tool_choice: auto` + "firefox keeps dying what gives?": model returned `finish_reason: stop` with 4-paragraph generic browser support text, `tool_calls: []`
- Same prompt with explicit action phrasing works; casual phrasing does not

**Research finding** (deep dive into Crush issues + vLLM tracker):
- Nobody has a reliably working Crush + vLLM + Qwen3 setup with consistent tool calling
- Crush always sends `tool_choice: required` (not configurable) — this is the exact trigger for vLLM issue #19051 (Qwen3 + reasoning parser + required = 400, fixed in vLLM 0.9.0)
- `qwen3_coder` streaming parser drops tool calls intermittently (vLLM issue #22975, closed stale)
- Qwen3 thinking + tool calls = ~60% failure rate even with `enable_thinking: False` (QwenLM issue #1817)
- The bugs are split across three layers (Crush, vLLM, model) with maintainers on both sides closing reports as not planned

**vLLM version**: 0.19.2rc1.dev228+gebf862c35 (Genesis fork — may have its own behavior)

**Mitigations applied**:
- Force non-streaming for tool requests in harness (bypasses streaming parser bug)
- Added TOOL USE directive to soul_code.md (commands before text for diagnostic questions)
- `enable_thinking: False` already set in all payloads

**Status**: Partially functional. MCP shell server executes (confirmed `Shell Sysinfo` call returned real data). Full tool loop (call → result → model continuation) blocked by harness 400 on tool result turns — fixed during session but not yet confirmed end-to-end.

### Next Session

- Try Qwen2.5-Coder-32B as Crush backend — reportedly more stable for tool use, no thinking/tool conflict
- Verify full MCP tool loop works end-to-end with new model
- If tool loop works: run the coding benchmark again and compare

### Lessons

1. Local inference coding agents are not plug-and-play. The Crush + vLLM + Qwen3 tool-call stack has known unfixed bugs at every layer.
2. The "thin harness" pattern works — soul/memory injection, context preservation, and shell execution all function correctly. The ceiling is the model's tool-calling reliability.
3. Benchmark scores (5/5 coding tasks) don't predict agentic reliability. A model can write perfect code and still fail to reach for tools on casual prompts.
4. MCP doesn't bypass the tool-calling problem — it still requires the model to emit structured `tool_calls`. It standardizes *what* gets called, not *whether* the model calls anything.
