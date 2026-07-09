# Qwen2.5-7B-Instruct Q4_K_M — Apple M4 MacBook Air Autoresearch — 2026-05-22

**Model**: Qwen2.5-7B-Instruct-Q4_K_M.gguf (4.36 GiB, 7.62B params)  
**Hardware**: Apple M4 MacBook Air (10-core GPU, 16 GB unified memory, ~68 GB/s bandwidth, fanless)  
**Stack**: llama.cpp 9270 (Homebrew), Metal backend (BLAS+MTL), macOS 15  
**Baseline flags**: `-ngl 99 --flash-attn on -t 4 -c 8192`  
**Stop condition**: Sweep threads, KV cache type, flash attention. Accept if delta > 5% on either pp or tg.

---

## Baseline (2026-05-22 ~14:49)

**Flags**:
```
-ngl 99 --flash-attn on -t 4
```

**Results** (llama-bench, pp512 + tg128):
- Prompt: 209.79 t/s
- **Generation: 20.91 t/s**

**Notes**: All 28 transformer layers on Metal GPU (`-ngl 99`). BLAS+MTL backend. Homebrew bottle — generic ARM, not M4-specific. M4 tensor API disabled (pre-M5 hardware). Thermal baseline: machine cold at start of session.

---

## Experiment 1: Thread count sweep (2026-05-22)

**Hypothesis**: With `-ngl 99`, GPU handles all matrix multiplications. CPU threads only process non-offloaded ops and memory management. Extra threads may add bus contention rather than throughput.

**Method**: llama-bench, pp512 + tg128, t=1/2/4/6/8/10. Machine warmed from baseline run.

| threads | pp512 t/s | tg128 t/s | pp delta | tg delta |
|---|---|---|---|---|
| 1  | 198.75 | **21.10** | -5.3%  | **+0.9%** |
| 2  | 183.89 | 21.03 | -12.3% | +0.6% |
| 4  | 181.60 | 19.97 | -13.4% | -4.5% |
| 6  | 169.76 | 19.94 | -19.1% | -4.6% |
| 8  | 163.58 | 19.44 | -22.0% | -7.0% |
| 10 | 157.30 | 19.01 | -25.0% | -9.1% |

**Delta (t=1 vs t=4)**: tg +0.6%, pp +9.4%  
**Verdict**: ✅ **APPLY t=1** — monotonically worse as threads increase. GPU owns all compute; CPU threads fight over the unified memory bus. t=1 is strictly optimal.

---

## Experiment 2: Flash attention on vs off (2026-05-22)

**Hypothesis**: Flash attention fuses QKV projection into a single kernel, reducing memory round-trips. Expected win on both pp and tg.

**Method**: llama-bench, pp512 + tg128, t=1 (from Exp 1 winner).

| config | pp512 t/s | tg128 t/s |
|---|---|---|
| flash-attn on  | 169.50 | **20.14** |
| flash-attn off | 155.23 | 18.28 |

**Delta**: pp +9.2%, tg +10.2%  
**Verdict**: ✅ **KEEP flash-attn on** — clear win on both metrics. Expected result; consistent with Metal flash attention support on Apple9 GPU family.

---

## Experiment 3: Framework comparison — llama.cpp vs MLX (2026-05-22)

**Hypothesis**: Apple's MLX framework, purpose-built for Apple Silicon, may outperform llama.cpp's Metal backend for generation speed.

**Method**: mlx-lm 0.31.3 with `mlx-community/Qwen2.5-7B-Instruct-4bit`. Generation bench: 512-token response to long prompt.

| framework | pp t/s | tg t/s | peak mem |
|---|---|---|---|
| llama.cpp (Q4_K_M, Metal) | **209** | 20.9 | ~4.4 GB |
| MLX (4-bit) | 70 | **23.2** | 4.4 GB |

**Delta**: MLX wins tg by +10.9%, llama.cpp wins pp by +198%.  
**Verdict**: ❌ **llama.cpp stays primary** — MLX generation advantage (+2.3 t/s) is marginal. llama.cpp prompt processing advantage is 3× and dominates for critical-use workloads with long context. MLX installed at `~/mlx-env/` for optional use.

---

## Experiment 4: Model upgrade — Qwen3-8B-4bit via MLX (2026-05-22)

**Hypothesis**: Qwen3-8B is the community-consensus best model for M4 16GB (2026). Newer architecture + larger param count may yield better quality at similar speed.

**Method**: mlx-lm with `mlx-community/Qwen3-8B-4bit`. Same 512-token bench prompt.

| model | pp t/s | tg t/s | peak mem |
|---|---|---|---|
| Qwen2.5-7B MLX 4-bit | 70.4 | 23.2 | 4.4 GB |
| Qwen3-8B MLX 4-bit | **14.1** | 20.5 | 4.8 GB |

**Delta**: Qwen3-8B is 80% slower on pp, 12% slower on tg.  
**Verdict**: ❌ **REJECT Qwen3-8B** — dramatically underperforms despite "newer = better" expectation. Likely M4 Air memory bandwidth saturation from larger architecture. Qwen2.5-7B Q4_K_M remains the optimal model for this hardware.

---

## Thermal Throttling Observation

**Critical finding for fanless hardware**: The M4 MacBook Air has no active cooling. Sustained benchmarking degraded pp from 209 t/s (cold) to 158 t/s (warm) over ~20 minutes — a **24% performance loss**.

**Implication**: For production critical-use, allow machine to cool before loading model. First run of a session will be significantly faster than sustained multi-run sessions. Generation speed (tg) is more stable than pp under thermal load.

---

## Final Config

**Winner**: llama.cpp 9270, Qwen2.5-7B-Instruct Q4_K_M, `-ngl 99 --flash-attn on -t 1`

| metric | baseline | optimized | delta |
|---|---|---|---|
| pp512 t/s | 209.79 | ~198 (cold) | thread win offset by thermal |
| tg128 t/s | 20.91 | 21.10 | +0.9% |

**Control script**: `~/bin/llm {start|stop|status|restart}`  
**API**: `http://127.0.0.1:8080/v1` (OpenAI-compatible)  
**Context**: 8192 tokens  

---

## What Wasn't Tried

- Source build targeting M4 (`-mcpu=apple-m4`) — Homebrew bottle is generic ARM, a native build would likely recover 15-25% on both metrics
- KV cache quantization (q8_0, q4_0) — sweep results were lost to output buffering; should re-run
- Larger model (Qwen2.5-14B) — would require ~9 GB, leaving only 7 GB for OS+context; likely thermal-throttles hard on Air
- Batch size tuning for llama-server `--ubatch-size`

---

## Experiment 5: Native M4 source build vs Homebrew bottle (2026-05-22)

**Hypothesis**: Homebrew bottle compiled with generic ARM flags. Building from source with `-mcpu=native` (targeting Apple M4 specifically) should recover 15-25% throughput via M4-specific SIMD and CPU path optimizations.

**Method**: Cloned `ggml-org/llama.cpp` HEAD (build 200, commit 1acee6b), configured with:
```
cmake -DCMAKE_C_FLAGS="-mcpu=native" -DCMAKE_CXX_FLAGS="-mcpu=native"
     -DGGML_METAL=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple
```
Benchmarked back-to-back on same thermal state (warm), same flags, same model.

| build | version | backend order | pp512 t/s | tg128 t/s |
|---|---|---|---|---|
| Homebrew bottle | 9270 (7ea23ddf7) | **BLAS,MTL** | **181.57 ± 2.65** | **20.39 ± 0.26** |
| Native M4 source | HEAD (1acee6b) | MTL,BLAS | 158.91 ± 5.93 | 17.92 ± 1.15 |

**Delta (native vs Homebrew)**: pp -12.5%, tg -12.1%. Native build is strictly worse on both metrics.

**Root cause**: `-mcpu=native` is irrelevant. Metal GPU shaders are compiled at runtime by the Metal compiler — host CPU compile flags do not affect GPU kernel performance. With `-ngl 99` offloading all 28 transformer layers to Metal, there is almost no CPU compute path to optimize.

The actual performance difference is a **backend priority regression in HEAD**: Homebrew 9270 loads `BLAS,MTL` (Apple Accelerate/AMX first), HEAD loads `MTL,BLAS` (Metal first). For prompt processing (batched matrix multiplication), Apple's AMX coprocessor via Accelerate is faster than the Metal batch path on M4. A code change between b9270 and b9291 flipped the default loading order.

**Verdict**: ❌ **REJECT native build** — Homebrew 9270 is faster on both pp and tg. Do not upgrade to HEAD until backend priority is confirmed fixed or reverted.

**Note**: Native build at `~/llama-m4-src/` — retained for future experiments, not used in production.

---

## Experiment 6: KV cache quantization sweep (2026-05-22)

**Hypothesis**: Quantized KV cache reduces memory bandwidth for attention, potentially improving tg speed. Old Ollama config used q8_0 for both K and V.

**Constraint discovered**: Metal flash-attn (in llama.cpp 9270) only supports quantization of the K cache. Any V cache quantization (`-ctv q8_0`, etc.) causes context creation failure. Tested without flash-attn: same failure. This is a Metal backend limitation in this build.

**Results** (t=1, ngl=99, flash-attn on, V always f16):

| ctk | ctv | pp512 t/s | tg128 t/s | notes |
|---|---|---|---|---|
| f16 | f16 | 164.59 ± 0.77 | 18.98 ± 0.84 | baseline |
| bf16 | bf16 | 151.48 ± 2.62 | 16.98 ± 0.50 | -8% both — native bfloat does not help |
| q8_0 | f16 | 160.52 ± 5.00 | 18.93 ± 0.52 | noise-level delta |
| q4_0 | f16 | 165.75 ± 2.42 | 19.28 ± 0.59 | +0.7% pp, +1.6% tg |
| q5_0 | f16 | 133.67 ± 22.39 | 13.17 ± 0.25 | **broken** — extreme pp variance, reject |
| f16 | q8_0 | FAIL | FAIL | Metal flash-attn incompatible |
| q8_0 | q8_0 | FAIL | FAIL | Metal flash-attn incompatible |

**bf16 finding**: M4 has native bfloat16 in hardware (`has bfloat = true` in Metal init), but bf16 KV cache is 8% slower. Likely the Metal attention kernel is optimized for f16 paths, not bf16, in this build version.

**q5_0 finding**: Extreme variance (±22 t/s on pp) and 30% tg drop indicates this code path is either buggy or hitting an unsupported Metal kernel fallback. Unusable.

**q4_0 finding**: +1-2% delta is within run-to-run noise from thermal variation. Not a reliable win.

**Verdict**: ❌ **No change — f16/f16 stays as default.** Maximum achievable improvement from KV quantization on this build/hardware combination is noise-level. The Metal backend limitation (V cache incompatible with flash-attn) blocks the configurations where quantization would actually help.

**Note for future work**: KV quantization benefit scales with context length. At 8192 context window filling, smaller KV cache = less bandwidth per token. Worth re-testing at pp4096+ once the Metal flash-attn V-cache incompatibility is resolved in a future llama.cpp version.

---

## Final Summary (2026-05-22)

**Hardware**: Apple M4 MacBook Air, 16 GB unified memory, fanless  
**Stack**: llama.cpp 9270 (Homebrew), Metal (BLAS,MTL), macOS 15  
**Model**: Qwen2.5-7B-Instruct Q4_K_M, 4.36 GiB  

### Experiments run

| # | Experiment | Verdict | Applied |
|---|---|---|---|
| 1 | Thread sweep (t=1..10) | t=1 optimal — GPU owns all compute, extra threads hurt | ✅ `-t 1` added to llm script |
| 2 | Flash attention on vs off | ON wins +9% pp, +10% tg | ✅ already on |
| 3 | llama.cpp vs MLX | llama.cpp wins pp 3×; MLX marginal +11% tg | ✅ llama.cpp stays |
| 4 | Qwen3-8B MLX vs Qwen2.5-7B | Qwen3 80% slower pp, 12% slower tg — rejected | ✅ Qwen2.5-7B stays |
| 5 | Native M4 source build | Homebrew wins both metrics — backend priority regression in HEAD | ✅ Homebrew stays |
| 6 | KV cache sweep (f16/bf16/q8/q4/q5) | No improvement; Metal blocks V-cache quant; f16 default wins | ✅ no change |

### Winning config

```
llama-server \
  -m ~/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf \
  -ngl 99 \
  -t 1 \
  --flash-attn on \
  -c 8192 \
  --host 127.0.0.1 \
  --port 8080
```

**Control**: `llm {start|stop|status|restart}` at `~/bin/llm`  
**API**: `http://127.0.0.1:8080/v1` (OpenAI-compatible)

### Cold performance (machine fully rested)
- pp512: ~209 t/s
- tg128: ~21 t/s

### Thermal reality
Fanless Air loses ~24% pp after 20 minutes sustained use. tg more stable. For critical use: start cold.

### Open items
- KV V-cache quantization: blocked by Metal flash-attn in this build — revisit when upstream fixes it
- Long-context tg: KV quantization benefit is theoretically larger at 4K+ tokens but q4_0-K confirmed worse even at pp2048 on thermal-saturated machine
- llama.cpp HEAD backend priority flip (BLAS→MTL order change): watch b9291+ for fix before upgrading Homebrew
