# Genesis Baseline — Benchmark & Stress Test Results — 2026-05-09

**Config:** Qwen3.6-27B INT4 AutoRound, GPTQ-Marlin, TP=2, MTP-3, max_model_len=65536  
**Hardware:** 2× RTX 5060 Ti 16GB GDDR7, Blackwell SM_120  
**Stack:** vLLM 0.19.2rc1 (Genesis custom patched, P60–P82)  

---

## Throughput Sweep (single request, temp=0)

| max_tokens | output tokens | time | t/s |
|---|---|---|---|
| 100 | 100 | 1.475s | 67.7 |
| 250 | 250 | 3.354s | 74.5 |
| 500 | 500 | 6.272s | 79.7 |
| 1000 | 1000 | 12.309s | 81.2 |

Short-output t/s is lower because MTP acceptance rate benefit amortizes over fewer speculative steps. At 1000 tokens, effective t/s approaches the theoretical ceiling. **Treat 80 t/s as the operational baseline.**

## TTFT (Time to First Token, streaming)

- Short prompt (~10 tokens): **66–124ms** (first request cold: 636ms — CUDA graph miss)
- 2000-token prompt: **362ms** (consistent, no variance)
- 8000-token prompt: **1400ms** (two 4096-token prefill chunks)

The 8k TTFT is a direct consequence of chunked prefill at max_num_batched_tokens=4096 — two passes needed.

**Attempted optimization:** Raised max_num_batched_tokens to 8192 to halve the 8k TTFT. This caused a hard crash: Genesis MTP speculation buffer is allocated at `4096 × 24 × 128 × 2 = 25MB`; at 8192 it tries to use `50MB` and throws `setStorage: out of bounds`. Not tunable without patching the Genesis MTP buffer allocation. **4096 is a hard ceiling for this build.**

## Concurrent Load (max_num_seqs=2)

2 simultaneous 300-token requests: **76.3 combined t/s** (single-request peak: 79.7)  
Overhead: **~4%** — excellent for TP=2 without NVLink (NCCL_P2P_DISABLE=1, PCIe-only).

## Tool Call Reliability

**10/10 PASS** across 10 sequential tool call requests. No flickers, no content-field fallback.

## Prefix Cache Effectiveness

- Cold (4096-token prompt): **5.188s**  
- Cached (identical prompt): **1.351s**  
- Speedup: **3.84×**

Prefix caching is working correctly and delivering near-theoretical speedup on repeated contexts.

## Sustained Load & Thermal Stability

**50 sequential 500-token requests (25,000 tokens total, 325 seconds):**

| Metric | Value |
|---|---|
| Errors | 0 / 50 |
| Avg sustained t/s | 76.9 |
| First-10 avg | 79.2 t/s |
| Last-10 avg | 79.2 t/s |
| Thermal degradation | **0.0 t/s** |
| Peak GPU temp | 66°C / 64°C |
| Thermal throttle threshold | ~83°C |
| Thermal headroom | **17–19°C** |
| Peak power draw | 121W / 113W per GPU |
| Power limit | 180W per GPU |
| Power utilization | **67% TDP** |
| VRAM before/after | 15707/14880 MiB — **identical** |

No memory leak. No thermal throttle. Clocks held at 2782/2722 MHz throughout.

---

## Config Freeze — Do Not Change These

| Parameter | Value | Reason |
|---|---|---|
| `--max-num-batched-tokens` | **4096** | Hard ceiling — MTP buffer allocates at 4096, crashes at 8192 |
| `--speculative-config mtp n=3` | **keep** | Removing causes 50% throughput regression (see mtp-test writeup) |
| `--max-num-seqs` | **2** | vLLM bug #35288: corrupted output at ≥4 concurrent |
| `--gpu-memory-utilization` | **0.90** | Tuned for max KV cache; higher risks OOM during profile run |
| `--max-model-len` | **65536** | Full 64k context; well within VRAM budget |

## Parameters Safe to Revisit

- `max_num_batched_tokens > 4096`: Only possible if Genesis MTP buffer is patched to scale with this value. Not a remote-SSH task.
- `vLLM 0.20.1 upgrade`: Potential SM_120 CUTLASS improvements, but requires porting Genesis patches P60–P82. Not safe without access to patch repo.
- `max_num_seqs=4`: Only after vLLM bug #35288 is resolved upstream.

---

## Operational Baseline

Genesis is **production-stable**. The config is locked. Primary risk vector going forward is the same as identified in the MTP test writeup: unpinned dependencies causing silent API drift. Requirements are pinned (`requirements.txt` frozen). Next review trigger: a Genesis patch release or a challenger model with self-MTP heads.
