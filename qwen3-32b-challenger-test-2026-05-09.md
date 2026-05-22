# Genesis Challenger Test: Qwen3-32B AutoRound INT4 — 2026-05-09

**Challenger:** `kaitchup/Qwen3-32B-autoround-4bit-gptq`  
**Incumbent:** Genesis — Qwen3.6-27B AutoRound INT4, MTP-3, port 8022  
**Config:** TP=2, gpu_mem_util=0.88, max_model_len=26000 (reduced from 32768 — KV cache insufficient)  
**Benchmark:** 500-token fixed output, tool call validity, instruction adherence

---

## Results

| Test | Genesis 27B | 32B Challenger |
|---|---|---|
| Throughput | **80.3 t/s** | 17.9 t/s |
| Tool call | PASS | FAIL |
| Constraint adherence | PASS | PASS |

**Verdict: Genesis wins decisively. 32B not adopted.**

---

## Root Cause: No MTP Heads in kaitchup AutoRound

The 32B AutoRound quant (`kaitchup/Qwen3-32B-autoround-4bit-gptq`) does not include the MTP (Multi-Token Prediction) speculative decoding heads. These heads are what give Genesis its ~2x throughput multiplier — same model predicts multiple tokens per forward pass.

Without MTP:
- 32B dense model, no speculative decoding
- Each forward pass produces 1 token instead of ~2
- Larger model = slower per-pass even without the speculative deficit

Result: 17.9 t/s vs 80.3 t/s. The 32B is not slower because of quantization quality; it's slower because it's doing half the work per cycle with twice the parameter count.

## Tool Call Failure

32B returned tool call in `<tool_call>` XML format inside the `content` field rather than the structured `tool_calls` object. The vLLM `qwen3_xml` parser handled it differently than the 27B model produces — suggests the 32B uses a slightly different prompt template or output format than the version the parser expects. Genesis (27B) produces clean structured `tool_calls` correctly.

## max_model_len Reduction Required

32B at 0.88 gpu_mem_util needed 4.0 GiB KV cache for max_seq_len=32768 but only had 3.22 GiB available. Reduced to 26000 to start. This means the 32B would cap at 26k context vs Genesis's 65k — a significant capability regression.

---

## What Would Make 32B Worth Testing Again

1. A 32B AutoRound quant **that includes MTP heads** — if one appears on HuggingFace, pull and test
2. Alternatively: a quality benchmark showing dramatically better reasoning/coding output that justifies the 4.5x speed penalty for specific use cases

## Current Standing

Genesis (Qwen3.6-27B MTP-3) remains the production model. No challengers have beaten it. The MTP self-speculative decoding is the key differentiator — any challenger needs to match or beat it on that dimension.

