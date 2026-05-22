

======================================================================
# Autoresearch GLM-4.7-Flash Loop — 2026-04-18 21:07
======================================================================
[21:07:32] 
────────────────────────────────────────────────────────────
[21:07:32]   AUTORESEARCH LOOP — GLM-4.7-Flash dual GPU  (2026-04-18 21:07)
[21:07:32] ────────────────────────────────────────────────────────────
[21:07:32] Baseline: gen=95.9 tok/s  prompt=149.7 tok/s
[21:07:32] Gate: 5/6  |  Max iterations: 10

[21:07:32] 
────────────────────────────────────────────────────────────
[21:07:32]   ITERATION 1/10
[21:07:32] ────────────────────────────────────────────────────────────
[21:07:32]   Generating seed (attempt 1)...
[21:07:41]   LLM returned nothing, retrying...
[21:07:46]   Generating seed (attempt 2)...
[21:07:55]   LLM returned nothing, retrying...
[21:08:00]   Generating seed (attempt 3)...
[21:08:08]   LLM returned nothing, retrying...
[21:08:13]   Generating seed (attempt 4)...
[21:08:22]   LLM returned nothing, retrying...
[21:08:27]   Generating seed (attempt 5)...
[21:08:36]   LLM returned nothing, retrying...


======================================================================
# Autoresearch GLM-4.7-Flash Loop — 2026-04-18 21:08
======================================================================
[21:08:38] 
────────────────────────────────────────────────────────────
[21:08:38]   AUTORESEARCH LOOP — GLM-4.7-Flash dual GPU  (2026-04-18 21:08)
[21:08:38] ────────────────────────────────────────────────────────────
[21:08:38] Baseline: gen=95.9 tok/s  prompt=149.7 tok/s
[21:08:38] Gate: 5/6  |  Max iterations: 10

[21:08:38] 
────────────────────────────────────────────────────────────
[21:08:38]   ITERATION 1/10
[21:08:38] ────────────────────────────────────────────────────────────
[21:08:38]   Generating seed (attempt 1)...
[21:08:41]   Generating seed (attempt 6)...
[21:08:42]   Seed: "KV Cache Hybrid F16+Q4 (Cache-type-k v4)"
[21:08:42]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[21:08:42]   Hypothesis: Since the model is MoE with heavy routing overhead, storing Q4_0 for the Key cache reduces memory bandwidth pressure and VRAM footprint, while keeping the Value cache in F16 preserves the activation gradient precision needed for the top-k expert gating to prevent quality degradation and potential slowdowns from speculative re-computation.
[21:08:42]   ✅ Seed accepted (6/6)
[21:08:42] 
  Running: KV Cache Hybrid F16+Q4 (Cache-type-k v4)
[21:08:42]   Hypothesis: Since the model is MoE with heavy routing overhead, storing Q4_0 for the Key cache reduces memory bandwidth pressure and VRAM footprint, while keeping the Value cache in F16 preserves the activation gradient precision needed for the top-k expert gating to prevent quality degradation and potential slowdowns from speculative re-computation.
[21:08:42] 
  Flags delta: {'cache-type-k': 'q4_0', 'cache-type-v': 'f16'}  extras: ['--ctx-size 65536', '--n-gpu-layers 999', '--tensor-split 1,1']
[21:08:42]   Stopping prod server...
[21:09:12] LLM call failed: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
[21:09:12]   LLM returned nothing, retrying...
[21:09:17]   Generating seed (attempt 7)...
[21:09:17] LLM call failed: HTTPConnectionPool(host='127.0.0.1', port=8081): Max retries exceeded with url: /v1/chat/completions (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7aa5d2354b90>: Failed to establish a new connection: [Errno 111] Connection refused'))
[21:09:17]   LLM returned nothing, retrying...
[21:09:18] Starting test server: --n-gpu-layers 999 --tensor-split 1,1 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1 --ctx-size 65536 --n-gpu-layers 999 --tensor-split 1,1
[21:09:22]   Generating seed (attempt 8)...
[21:09:22] LLM call failed: 'choices'
[21:09:22]   LLM returned nothing, retrying...
[21:09:27]   Generating seed (attempt 9)...
[21:09:34]   Seed: "Asymmetric Tensor Split for MoE Expert Routing"
[21:09:34]   Score: 2/6  |  {'novelty': 0.8, 'feasibility': 0.9, 'impact': 0.7, 'safety': 0.9, 'measurable': 1.0, 'orthogonality': 1.0}
[21:09:34]   Hypothesis: By shifting a portion of the workload to the primary GPU via a non-equal tensor-split, we can optimize the communication overhead of the MoE routing layers which are currently split exactly 50/50.
[21:09:34]   ❌ Seed rejected (2/6 < 5/6) — regenerating
[21:09:34]   Generating seed (attempt 10)...
[21:09:42]   Seed: "KV Cache Quantization Precision Scaling (F16/Q8_0/IQ4_NL)"
[21:09:42]   Score: 3/6  |  {'novelty': 0.7, 'feasibility': 1.0, 'impact': 0.6, 'safety': 1.0, 'measurable': 1.0, 'orthogonality': 0.9}
[21:09:42]   Hypothesis: Replacing Q4_0 KV cache with F16 or Q8_0 will improve generation throughput by reducing the overhead of dequantization-on-the-fly during the attention mechanism's backward pass within the MoE routing logic.
[21:09:42]   ❌ Seed rejected (3/6 < 5/6) — regenerating
[21:09:42]   Generating seed (attempt 11)...
[21:09:49]   Seed: "Parallel Batch-Interleaved KV Cache Optimization"
[21:09:49]   Score: 1/6  |  {'novelty': 0.85, 'feasational': 0.95, 'impact': 0.8, 'safety': 0.9, 'measurable': 1.0, 'orthogonality': 0.9}
[21:09:49]   Hypothesis: By leveraging the 8GB VRAM headroom to increase --parallel slots while simultaneously decreasing --ubatch-size, we can maximize the throughput of the 3B active MoE parameters by overlapping the compute-heavy routing phase with KV cache management.
[21:09:49]   ❌ Seed rejected (1/6 < 5/6) — regenerating
[21:09:49]   Generating seed (attempt 12)...
[21:09:55]   Seed: "KV-Cache Precision Decoupling (F16-K / Q4_0-V)"
[21:09:55]   Score: 56/6  |  {'novelty': 8, 'feasibility': 10, 'impact': 9, 'safety': 10, 'measurable': 10, 'orthogonality': 9}
[21:09:55]   Hypothesis: Using F16 for Key tensors and Q4_0 for Value tensors will maximize routing precision for the MoE heads while drastically reducing the memory bandwidth pressure of the KV cache during the generation phase.
[21:09:55]   ✅ Seed accepted (56/6)
[21:09:55] 
  Running: KV-Cache Precision Decoupling (F16-K / Q4_0-V)
[21:09:55]   Hypothesis: Using F16 for Key tensors and Q4_0 for Value tensors will maximize routing precision for the MoE heads while drastically reducing the memory bandwidth pressure of the KV cache during the generation phase.
[21:09:55] 
  Flags delta: {'--ctk': 'f16', '--ctv': 'q4_0'}  extras: ['--no-mmap', '--numa', '--ubatch-size 512']
[21:09:55]   Stopping prod server...
[21:09:59]   Freed leaked VRAM from pid 30409
[21:09:59]   Freed leaked VRAM from pid 30409
[21:10:01] Starting test server: --n-gpu-layers 999 --tensor-split 1,1 --flash-attn on -ctk f16 -ctv q4_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1 --no-mmap --numa --ubatch-size 512
[21:10:48]   ❌ Server failed to start (OOM or crash)
[21:10:48] 
  ❌ FAILED (server failed to start)
[21:10:48] 
────────────────────────────────────────────────────────────
[21:10:48]   ITERATION 2/10
[21:10:48] ────────────────────────────────────────────────────────────
[21:10:48]   Generating seed (attempt 1)...
[21:10:53]   Seed: "Asymmetric KV-Cache Precision Tuning"
[21:10:53]   Score: 3/6  |  {'novelty': 0.8, 'feasibility': 1.0, 'impact': 0.7, 'safety': 1.0, 'measurable': 1.0, 'orthogonality': 0.9}
[21:10:53]   Hypothesis: Since the model is MoE with low active params, using high-precision F16 for Keys and low-precision Q4_0 for Values will maximize throughput by reducing VRAM bandwidth pressure while maintaining routing stability.
[21:10:53]   ❌ Seed rejected (3/6 < 5/6) — regenerating
[21:10:53]   Generating seed (attempt 2)...
[21:11:00]   Seed: "KV-Cache Precision Maximization (Q8_0 K/V)"
[21:11:00]   Score: 3/6  |  {'novelty': 0.8, 'feasibility': 1.0, 'impact': 0.7, 'safety': 1.0, 'measurable': 1.0, 'orthogonality': 0.9}
[21:11:00]   Hypothesis: By upgrading the KV cache from q4_0 to q8_0, we will reduce the quantization error/routing noise for the MoE experts while maintaining enough VRAM headroom to prevent swapping, potentially increasing generation stability and throughput.
[21:11:00]   ❌ Seed rejected (3/6 < 5/6) — regenerating
[21:11:00]   Generating seed (attempt 3)...
[21:11:06]   Seed: "Asymmetric KV-Cache Precision with F16-K and Q8_0-V"
[21:11:06]   Score: 1/6  |  {'novelty': 0.8, 'feasibility': 0.9, 'impact': 0.7, 'safety': 0.9, 'measurable': 1.0, 'orthogonality': 0.9}
[21:11:06]   Hypothesis: Using F16 for keys to maintain high precision for routing/positional accuracy while using Q8_0 for values to maximize memory bandwidth efficiency will yield better gen-speed than the baseline Q4_0/Q4_0 combo.
[21:11:06]   ❌ Seed rejected (1/6 < 5/6) — regenerating
[21:11:06]   Generating seed (attempt 4)...
[21:11:14]   Seed: "KV-Cache Compression: iq4_nl with split-tensor-split"
[21:11:14]   Score: 52/6  |  {'novelty': 8, 'feasibility': 9, 'impact': 7, 'safety': 9, 'measurable': 10, 'orthogonality': 9}
[21:11:14]   Hypothesis: By using a more aggressive --ctk iq4_nl (importance-quantized) while shifting the tensor split to favor the primary GPU, we can maximize VRAM headroom to potentially increase context overhead or cache efficiency without sacrificing routing speed.
[21:11:14]   ✅ Seed accepted (52/6)
[21:11:14] 
  Running: KV-Cache Compression: iq4_nl with split-tensor-split
[21:11:14]   Hypothesis: By using a more aggressive --ctk iq4_nl (importance-quantized) while shifting the tensor split to favor the primary GPU, we can maximize VRAM headroom to potentially increase context overhead or cache efficiency without sacrificing routing speed.
[21:11:14] 
  Flags delta: {'--ctk': 'iq4_nl', '--ctv': 'iq4_nl', '--tensor-split': '1.2,0.8'}  extras: ['--no-mmap', '--defrag-thold 0.05']
[21:11:14]   Stopping prod server...
[21:11:18]   Freed leaked VRAM from pid 30896
[21:11:18]   Freed leaked VRAM from pid 30896
[21:11:20] Starting test server: --n-gpu-layers 999 --tensor-split 1.2,0.8 --flash-attn on -ctk iq4_nl -ctv iq4_nl --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1 --no-mmap --defrag-thold 0.05
[21:11:33]   ❌ Server failed to start (OOM or crash)
[21:11:33] 
  ❌ FAILED (server failed to start)
[21:11:33] 
────────────────────────────────────────────────────────────
[21:11:33]   ITERATION 2/10
[21:11:33] ────────────────────────────────────────────────────────────
[21:11:33]   Generating seed (attempt 1)...
[21:11:33] LLM call failed: 'choices'
[21:11:33]   LLM returned nothing, retrying...
[21:11:38]   Generating seed (attempt 2)...
[21:11:38] LLM call failed: 'choices'
[21:11:38]   LLM returned nothing, retrying...
[21:11:43]   Generating seed (attempt 3)...


======================================================================
# Autoresearch GLM-4.7-Flash v2 — 2026-04-18 21:16
======================================================================
[21:16:29] 
────────────────────────────────────────────────────────────
[21:16:29]   AUTORESEARCH LOOP v2 — GLM-4.7-Flash  (2026-04-18 21:16)
[21:16:29] ────────────────────────────────────────────────────────────
[21:16:29] Baseline: gen=95.9 tok/s  prompt=149.7 tok/s
[21:16:29] Gate: 5/6  |  Max iterations: 10

[21:16:29] 
────────────────────────────────────────────────────────────
[21:16:29]   ITERATION 1/10
[21:16:29] ────────────────────────────────────────────────────────────
[21:16:29]   Generating seed (attempt 1)...
[21:16:48]   JSON parse error: Expecting property name enclosed in double quotes: line 18 column 4 (char 457)
  Raw: ```json
{
  "name": "KV-Cache-Q8-K-Compression",
  "hypothesis": "Switching KV cache from q4_0 to q8_0 will increase precision for routing while staying within the 8GB VRAM headroom to see if it stabilizes throughput.",
  "flags_changed": {
    "kv_cache_type": "q8_0"
  },
  "extra_flags": [
    "--
[21:16:48]   LLM returned nothing, retrying...
[21:16:53]   Generating seed (attempt 2)...


======================================================================
# Autoresearch GLM-4.7-Flash v2 — 2026-04-18 21:17
======================================================================
[21:17:04] 
────────────────────────────────────────────────────────────
[21:17:04]   AUTORESEARCH LOOP v2 — GLM-4.7-Flash  (2026-04-18 21:17)
[21:17:04] ────────────────────────────────────────────────────────────
[21:17:04] Baseline: gen=95.9 tok/s  prompt=149.7 tok/s
[21:17:04] Gate: 5/6  |  Max iterations: 10

[21:17:04] 
────────────────────────────────────────────────────────────
[21:17:04]   ITERATION 1/10
[21:17:04] ────────────────────────────────────────────────────────────
[21:17:04]   Generating seed (attempt 1)...
[21:17:10]   Seed: "KV-Cache-Quant-Q8"
[21:17:10]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[21:17:10]   Hypothesis: Switching KV cache from q4_0 to q8_0 will increase precision and potentially improve routing stability in MoE without exceeding the 8GB VRAM headroom.
[21:17:10]   Seed accepted (6/6)
[21:17:10] 
  Running: KV-Cache-Quant-Q8
[21:17:10]   Hypothesis: Switching KV cache from q4_0 to q8_0 will increase precision and potentially improve routing stability in MoE without exceeding the 8GB VRAM headroom.
[21:17:10] 
  Flags delta: {'kv_cache_type': 'q8_0'}  extras: ['--type q8_0']
[21:17:10]   Stopping prod server...
[21:17:13]   Freed leaked VRAM from pid 31714
[21:17:13]   Freed leaked VRAM from pid 31714
[21:17:15] Starting test server: --n-gpu-layers 999 --tensor-split 1,1 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1 --type q8_0
[21:18:45]   Server failed to start — restarting prod...
[21:18:45] 
  FAILED (server failed to start)
[21:18:45] 
────────────────────────────────────────────────────────────
[21:18:45]   ITERATION 2/10
[21:18:45] ────────────────────────────────────────────────────────────
[21:18:45]   Generating seed (attempt 1)...
[21:18:52]   Seed: "KV-Cache-Q4-NL-Split"
[21:18:52]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[21:18:52]   Hypothesis: Applying iq4_nl quantization to the KV cache will drastically reduce VRAM footprint and memory bandwidth pressure, potentially boosting generation speed on MoE architectures.
[21:18:52]   Seed accepted (6/6)
[21:18:52] 
  Running: KV-Cache-Q4-NL-Split
[21:18:52]   Hypothesis: Applying iq4_nl quantization to the KV cache will drastically reduce VRAM footprint and memory bandwidth pressure, potentially boosting generation speed on MoE architectures.
[21:18:52] 
  Flags delta: {'kv-cache-type': 'iq4_nl'}  extras: ['--kv-cache-type iq4_nl']
[21:18:52]   Stopping prod server...
[21:18:55]   Freed leaked VRAM from pid 35341
[21:18:55]   Freed leaked VRAM from pid 35341
[21:18:57] Starting test server: --n-gpu-layers 999 --tensor-split 1,1 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1 --kv-cache-type iq4_nl
[21:20:27]   Server failed to start — restarting prod...
[21:20:27] 
  FAILED (server failed to start)
[21:20:27] 
────────────────────────────────────────────────────────────
[21:20:27]   ITERATION 3/10
[21:20:27] ────────────────────────────────────────────────────────────
[21:20:27]   Generating seed (attempt 1)...
[21:20:34]   Seed: "KV-Cache-Q8-K-V-Split"
[21:20:34]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[21:20:34]   Hypothesis: Using q8_0 for KV cache will provide higher precision than q4 while maintaining a smaller VRAM footprint than f16, potentially optimizing bandwidth on Blackwell.
[21:20:34]   Seed accepted (6/6)
[21:20:34] 
  Running: KV-Cache-Q8-K-V-Split
[21:20:34]   Hypothesis: Using q8_0 for KV cache will provide higher precision than q4 while maintaining a smaller VRAM footprint than f16, potentially optimizing bandwidth on Blackwell.
[21:20:34] 
  Flags delta: {'kv_cache_type': 'q8_0'}  extras: ['--cache-type-k q8_0', '--cache-type-v q8_0']
[21:20:34]   Stopping prod server...
[21:20:37]   Freed leaked VRAM from pid 36404
[21:20:37]   Freed leaked VRAM from pid 36404
[21:20:39] Starting test server: --n-gpu-layers 999 --tensor-split 1,1 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1 --cache-type-k q8_0 --cache-type-v q8_0
[21:21:03]   Server up — running benchmark...
[21:21:09]   run 1: gen=83.6 tok/s  prompt=32.4 tok/s
[21:21:14]   run 2: gen=95.5 tok/s  prompt=70.3 tok/s
[21:21:18]   run 3: gen=95.8 tok/s  prompt=72.8 tok/s


======================================================================
# Autoresearch GLM-4.7-Flash v2 — 2026-04-18 21:34
======================================================================
[21:34:56] 
────────────────────────────────────────────────────────────
[21:34:56]   AUTORESEARCH LOOP v2 — GLM-4.7-Flash  (2026-04-18 21:34)
[21:34:56] ────────────────────────────────────────────────────────────
[21:34:56] Baseline: gen=95.9 tok/s  prompt=149.7 tok/s
[21:34:56] Gate: 5/6  |  Max iterations: 10

[21:34:56] 
────────────────────────────────────────────────────────────
[21:34:56]   ITERATION 1/10
[21:34:56] ────────────────────────────────────────────────────────────
[21:34:56]   Generating seed (attempt 1)...
[21:34:59]   Seed: "KV Cache Quantization (q8_0)"
[21:34:59]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[21:34:59]   Hypothesis: Increasing KV cache precision from q4_0 to q8_0 reduces memory bandwidth bottlenecks for the MoE expert activations, potentially improving token generation speed despite the higher memory footprint.
[21:34:59]   Seed accepted (6/6)
[21:34:59] 
  Running: KV Cache Quantization (q8_0)
[21:34:59]   Hypothesis: Increasing KV cache precision from q4_0 to q8_0 reduces memory bandwidth bottlenecks for the MoE expert activations, potentially improving token generation speed despite the higher memory footprint.
[21:34:59] 
  Flags delta: {'kv-cache': 'q8_0'}  extras: ['ctx-size 65536']
[21:34:59]   Stopping prod server...
[21:35:04] Starting test server: --n-gpu-layers 999 --tensor-split 1,1 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1 ctx-size 65536
[21:36:34]   Server failed to start — restarting prod...
[21:36:34] 
  FAILED (server failed to start)
[21:36:34] 
────────────────────────────────────────────────────────────
[21:36:34]   ITERATION 2/10
[21:36:34] ────────────────────────────────────────────────────────────
[21:36:34]   Generating seed (attempt 1)...
[21:36:41]   Seed: "KV Cache Precision: f16"
[21:36:41]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[21:36:41]   Hypothesis: Switching from q4_0 to f16 for KV cache will increase prompt speed through better precision alignment with Blackwell-specific hardware, despite higher VRAM usage.
[21:36:41]   Seed accepted (6/6)
[21:36:41] 
  Running: KV Cache Precision: f16
[21:36:41]   Hypothesis: Switching from q4_0 to f16 for KV cache will increase prompt speed through better precision alignment with Blackwell-specific hardware, despite higher VRAM usage.
[21:36:41] 
  Flags delta: {'kv_cache': 'f16'}  extras: ['--type f16']
[21:36:41]   Stopping prod server...
[21:36:44]   Freed leaked VRAM from pid 6020
[21:36:44]   Freed leaked VRAM from pid 6020
[21:36:46] Starting test server: --n-gpu-layers 999 --tensor-split 1,1 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1 --type f16
[21:38:16]   Server failed to start — restarting prod...
[21:38:16] 
  FAILED (server failed to start)
[21:38:16] 
────────────────────────────────────────────────────────────
[21:38:16]   ITERATION 3/10
[21:38:16] ────────────────────────────────────────────────────────────
[21:38:16]   Generating seed (attempt 1)...
[21:38:39]   JSON parse error: Expecting property name enclosed in double quotes: line 19 column 3 (char 528)
  Raw: ```json
{
  "name": "KV Cache Quantization: iq4_nl",
  "hypothesis": "Using iq4_nl for the KV cache will significantly reduce VRAM footprint and memory bandwidth requirements compared to q4_0, potentially increasing gen speed via higher effective bandwidth.",
  "flags_changed": {
    "kv-cache-type"
[21:38:39]   LLM returned nothing, retrying...
[21:38:44]   Generating seed (attempt 2)...
[21:38:50]   Seed: "ubatch-size-tuning-2048"
[21:38:50]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[21:38:50]   Hypothesis: Increasing --ubatch-size to 2048 will maximize throughput by better saturating the Blackwell SMs during the prompt processing phase without exceeding VRAM limits.
[21:38:50]   Seed accepted (6/6)
[21:38:50] 
  Running: ubatch-size-tuning-2048
[21:38:50]   Hypothesis: Increasing --ubatch-size to 2048 will maximize throughput by better saturating the Blackwell SMs during the prompt processing phase without exceeding VRAM limits.
[21:38:50] 
  Flags delta: {}  extras: ['--ubatch-size 2048']
[21:38:50]   Stopping prod server...
[21:38:53]   Freed leaked VRAM from pid 7045
[21:38:53]   Freed leaked VRAM from pid 7045
[21:38:55] Starting test server: --n-gpu-layers 999 --tensor-split 1,1 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1 --ubatch-size 2048
[21:39:22]   Server up — running benchmark...
[21:39:28]   run 1: gen=94.5 tok/s  prompt=29.6 tok/s
[21:39:32]   run 2: gen=95.7 tok/s  prompt=60.7 tok/s
[21:39:36]   run 3: gen=95.6 tok/s  prompt=72.5 tok/s


======================================================================
# Autoresearch GLM-4.7-Flash v2 — 2026-04-19 11:37
======================================================================
[11:37:30] 
────────────────────────────────────────────────────────────
[11:37:30]   AUTORESEARCH LOOP v2 — GLM-4.7-Flash  (2026-04-19 11:37)
[11:37:30] ────────────────────────────────────────────────────────────
[11:37:30] Baseline: gen=95.9 tok/s  prompt=149.7 tok/s
[11:37:30] Gate: 5/6  |  Max iterations: 10

[11:37:30] 
────────────────────────────────────────────────────────────
[11:37:30]   ITERATION 1/10
[11:37:30] ────────────────────────────────────────────────────────────
[11:37:30]   Generating seed (attempt 1)...
[11:37:34]   Seed: "KV cache q5_0 value type"
[11:37:34]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[11:37:34]   Hypothesis: Quantizing only the K and V cache to q5_0 should increase memory bandwidth utilization without exceeding the 8GB VRAM headroom, as q5_0 is slightly larger than q4_0 but significantly smaller than f16, which should reduce cache eviction and improve MoE expert throughput.
[11:37:34]   Seed accepted (6/6)
[11:37:34] 
  Running: KV cache q5_0 value type
[11:37:34]   Hypothesis: Quantizing only the K and V cache to q5_0 should increase memory bandwidth utilization without exceeding the 8GB VRAM headroom, as q5_0 is slightly larger than q4_0 but significantly smaller than f16, which should reduce cache eviction and improve MoE expert throughput.
[11:37:34] 
  Flags delta: {'ctk': 'q4_0', 'ctv': 'q5_0'}  extras: []
[11:37:34]   Stopping prod server...
[11:37:39] Starting test server: --n-gpu-layers 999 --tensor-split 1,1 --flash-attn on -ctk q4_0 -ctv q5_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1
[11:37:48]   Server up — running benchmark...
[11:37:52]   run 1: gen=97.1 tok/s  prompt=158.2 tok/s
[11:37:57]   run 2: gen=96.9 tok/s  prompt=73.0 tok/s
[11:38:01]   run 3: gen=97.3 tok/s  prompt=62.1 tok/s
[11:38:03]   Restarting prod server...
[11:38:12] 
  IMPROVEMENT
[11:38:12]   gen: 97.1 tok/s  (Delta +1.2)
[11:38:12]   prompt: 97.8 tok/s  (Delta -51.9)
[11:38:12]   New best: 97.1 tok/s gen
[11:38:12] 
────────────────────────────────────────────────────────────
[11:38:12]   ITERATION 2/10
[11:38:12] ────────────────────────────────────────────────────────────
[11:38:12]   Generating seed (attempt 1)...
[11:38:15]   Seed: "KV Cache Imbalance Split"
[11:38:15]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[11:38:15]   Hypothesis: Allocating more VRAM to the GPU with the active MoE expert routing (tensor-split 0.8, 1.2) should reduce expert transfer latency and increase generation speed.
[11:38:15]   Seed accepted (6/6)
[11:38:15] 
  Running: KV Cache Imbalance Split
[11:38:15]   Hypothesis: Allocating more VRAM to the GPU with the active MoE expert routing (tensor-split 0.8, 1.2) should reduce expert transfer latency and increase generation speed.
[11:38:15] 
  Flags delta: {'tensor_split': '0.8,1.2'}  extras: []
[11:38:15]   Stopping prod server...
[11:38:21] Starting test server: --n-gpu-layers 999 --tensor-split 0.8,1.2 --flash-attn on -ctk q4_0 -ctv q5_0 --ctx-size 65536 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --alias glm47flash --mlock --cpu-strict 1
[11:38:33]   Server up — running benchmark...
[11:38:37]   run 1: gen=97.1 tok/s  prompt=168.8 tok/s
[11:38:41]   run 2: gen=97.1 tok/s  prompt=72.6 tok/s
[11:38:45]   run 3: gen=0.0 tok/s  prompt=0.0 tok/s
