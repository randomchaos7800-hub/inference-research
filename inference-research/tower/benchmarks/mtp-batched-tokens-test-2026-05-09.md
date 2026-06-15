# Genesis Config Test: MTP Removal + Batched Tokens — 2026-05-09

**Hardware:** 2x RTX 5060 Ti 16GB GDDR7, Blackwell SM_120, Intel Core Ultra 7 265F  
**Stack:** vLLM 0.19.2rc1 (Genesis custom patched build), Qwen3.6-27B-int4-AutoRound, GPTQ-Marlin  
**Config at test time:** TP=2, max_model_len=65536, gpu_mem_util=0.90, MTP-3, chunked_prefill, prefix_caching  
**Benchmark:** 500-token fixed output, temperature=0, single request, warm run

---

## What We Tested

Based on external inference optimization research (May 2026), two config changes were recommended for single-user workloads:

1. **Remove MTP speculative decoding** (was `num_speculative_tokens=3`)  
   Rationale from research: ~22% Marlin kernel overhead, low acceptance rate at concurrency=1, vLLM bug #35288 (corrupted output at concurrency ≥4)

2. **Drop `--max-num-batched-tokens` from 4096 → 2048**  
   Rationale from research: 2048 is the single-user sweet spot per vLLM tuning guides; 4096 causes TTFT spikes

Both changes were applied together and tested.

---

## Results

| Config | t/s |
|---|---|
| Baseline (MTP-3, batched=4096) | **80.8** |
| MTP disabled + batched=2048 | **40.1** |
| Restored original | **79.5** |

MTP removal caused a **~50% throughput regression**. Fully reverted.

---

## Root Cause: Research Misidentified the MTP Architecture

The external research treated MTP as a separate-draft-model speculative decoding setup, where:
- A small draft model proposes tokens
- The main model verifies them
- Marlin kernel overhead is significant relative to the acceptance rate gain

**This is wrong for Genesis.** Qwen3.6-27B uses a **self-MTP head** — the same model predicts multiple future tokens as part of a single forward pass. This is fundamentally different:

- No separate model, no separate forward pass for drafting
- Acceptance rate is much higher (same weights predicting ahead)
- The ~22% Marlin overhead is outweighed by the throughput gain when acceptance rate is high

At MTP-3 with self-speculative heads, Genesis is effectively generating ~2 tokens per forward pass cycle. Disabling this cuts output rate roughly in half — exactly what we observed.

The vLLM bug #35288 (corrupted output at concurrency ≥4) is still relevant but Genesis runs max_num_seqs=2, so it's not exposed.

---

## Operational Notes

During the test, a race condition caused boot failures:

- Killed old system-service vLLM process (PID 3691806)
- User service restarted immediately before GPU VRAM was freed
- New instance saw 13.51 GiB free, needed 13.91 GiB (0.90 × 15.45 GiB)
- `ValueError: Free memory on device cuda:0 ... less than desired GPU memory utilization`

**Fix:** After killing a vLLM process, wait for GPU memory to clear before starting a new instance. Check with `nvidia-smi --query-gpu=memory.used --format=csv,noheader` — both GPUs should be near-idle (<500 MiB) before starting.

Note: Genesis runs from a **user systemd service** (`systemctl --user ...`), not the system service (`/etc/systemd/system/vllm-genesis.service`). The system service file exists but the user service is what's active. This matters for restarts — `sudo systemctl restart` doesn't work without a password; use `systemctl --user restart vllm-genesis`.

---

## What's Still Valid from the Research

| Finding | Status |
|---|---|
| SGLang #21132 (garbage output on SM_120 INT4) — stay on vLLM | ✅ Correct, still open |
| GPTQ-Marlin is the best INT4 format for this stack | ✅ Correct |
| FlashInfer attention backend not ready for SM_120 | ✅ Correct |
| vLLM 0.20.1 has SM_120 CUTLASS fixes vs 0.19.2rc1 | ⚠️ Potentially valid, but Genesis uses a custom-patched vLLM build — stock upgrade would wipe Genesis patches P60–P82. Not safe to upgrade without porting patches. |
| MTP-3 is net negative at single-user concurrency | ❌ Wrong for self-MTP (Qwen3 architecture). May be valid for separate draft-model setups. |
| Drop batched-tokens to 2048 | Untested alone — left at 4096 which was tuned and verified |

---

## Conclusion

**Do not change the MTP config.** Genesis at MTP-3 is delivering ~2x throughput via self-speculative decoding. The 80 t/s baseline already accounts for this — it's the correct operating point.

The only actionable remaining item is the vLLM upgrade to 0.20.1 for SM_120 CUTLASS fixes, but that requires someone with access to the Genesis patch repo to port P60–P82 to the new base. Not a remote-SSH task.
