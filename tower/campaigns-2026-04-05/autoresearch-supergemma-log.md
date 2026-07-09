

======================================================================
# Autoresearch supergemma4-26b single-GPU — 2026-04-19 16:52
======================================================================
[16:52:13] 
────────────────────────────────────────────────────────────
[16:52:13]   AUTORESEARCH — supergemma4-26b single GPU  (2026-04-19 16:52)
[16:52:13] ────────────────────────────────────────────────────────────
[16:52:13] Baseline: gen=61.7 tok/s  prompt=281.9 tok/s
[16:52:13] Gate: 5/6  |  Max iterations: 12

[16:52:13] 
────────────────────────────────────────────────────────────
[16:52:13]   ITERATION 1/12
[16:52:13] ────────────────────────────────────────────────────────────
[16:52:13]   Generating seed (attempt 1)...
[16:52:21]   Seed: "Aggressive CPU Offload + Context Reduction for Q8 KV"
[16:52:21]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[16:52:21]   Hypothesis: Offloading layers 20-29 to CPU will free enough VRAM to allow a 16k context size with a high-precision q8_0 KV cache, potentially improving gen speed via better cache-to-compute throughput.
[16:52:21]   Accepted (6/6)
[16:52:21] 
  Running: Aggressive CPU Offload + Context Reduction for Q8 KV
[16:52:21]   Hypothesis: Offloading layers 20-29 to CPU will free enough VRAM to allow a 16k context size with a high-precision q8_0 KV cache, potentially improving gen speed via better cache-to-compute throughput.
[16:52:21]   flags_changed: {'ctx_size': 16384, 'ctk': 'q8_0', 'ctv': 'q8_0'}  extra: ['--override-tensor "blk\\.(2[0-9])\\..*exps.*=CPU"']
[16:52:21]   Stopping prod server...
[16:52:26]   cmd: -ctk q8_0 -ctv q8_0 --ctx-size 16384 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --alias gemma4 --mlock --override-tensor "blk\.(2[0-9])\..*exps.*=CPU"
[16:54:28]   Server failed to start — restarting prod...
[16:54:31] 
  FAILED (server failed to start)
[16:54:31] 
────────────────────────────────────────────────────────────
[16:54:31]   ITERATION 2/12
[16:54:31] ────────────────────────────────────────────────────────────
[16:54:31]   Generating seed (attempt 1)...
[16:54:38]   Seed: "Aggressive CPU Offload with Context Reduction for Q4 KV"
[16:54:38]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[16:54:38]   Hypothesis: By offloading 10 layers to CPU and reducing context to 16k, we free enough VRAM to utilize q4_0 KV cache while maintaining high throughput.
[16:54:38]   Accepted (6/6)
[16:54:38] 
  Running: Aggressive CPU Offload with Context Reduction for Q4 KV
[16:54:38]   Hypothesis: By offloading 10 layers to CPU and reducing context to 16k, we free enough VRAM to utilize q4_0 KV cache while maintaining high throughput.
[16:54:38]   flags_changed: {'ctk': 'q4_0', 'ctx_size': 16384}  extra: ['--override-tensor "blk\\.(2[0-9])\\..*exps.*=CPU"', '--ubatch_size 512']
[16:54:38]   Stopping prod server...
[16:54:44]   cmd: -ctk q4_0 -ctv q4_0 --ctx-size 16384 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --alias gemma4 --mlock --override-tensor "blk\.(2[0-9])\..*exps.*=CPU" --ubatch_size 512
[16:56:46]   Server failed to start — restarting prod...
[16:56:49] 
  FAILED (server failed to start)
[16:56:49] 
────────────────────────────────────────────────────────────
[16:56:49]   ITERATION 3/12
[16:56:49] ────────────────────────────────────────────────────────────
[16:56:49]   Generating seed (attempt 1)...
[16:56:56]   Seed: "Context Reduction for High-Precision KV"
[16:56:56]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[16:56:56]   Hypothesis: Reducing ctx_size to 16384 will free significant VRAM to allow q8_0 KV cache without OOMing, potentially improving generation quality/speed balance.
[16:56:56]   Accepted (6/6)
[16:56:56] 
  Running: Context Reduction for High-Precision KV
[16:56:56]   Hypothesis: Reducing ctx_size to 16384 will free significant VRAM to allow q8_0 KV cache without OOMing, potentially improving generation quality/speed balance.
[16:56:56]   flags_changed: {'ctx_size': '16384', 'ctk': 'q8_0', 'ctv': 'q8_0'}  extra: ['--override-tensor "blk\\.(2[4-9])\\..*exps.*=CPU"']
[16:56:56]   Stopping prod server...
[16:57:01]   cmd: -ctk q8_0 -ctv q8_0 --ctx-size 16384 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --alias gemma4 --mlock --override-tensor "blk\.(2[4-9])\..*exps.*=CPU"
[16:59:03]   Server failed to start — restarting prod...
[16:59:06] 
  FAILED (server failed to start)
[16:59:06] 
────────────────────────────────────────────────────────────
[16:59:06]   ITERATION 4/12
[16:59:06] ────────────────────────────────────────────────────────────
[16:59:06]   Generating seed (attempt 1)...
[16:59:14]   Seed: "Aggressive CPU Offload + Context Reduction for Q8 KV"
[16:59:14]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[16:59:14]   Hypothesis: By offloading layers 20-29 to CPU and dropping ctx to 16384, we free enough VRAM to utilize q8_0 KV cache to improve precision-weighted throughput.
[16:59:14]   Accepted (6/6)
[16:59:14] 
  Running: Aggressive CPU Offload + Context Reduction for Q8 KV
[16:59:14]   Hypothesis: By offloading layers 20-29 to CPU and dropping ctx to 16384, we free enough VRAM to utilize q8_0 KV cache to improve precision-weighted throughput.
[16:59:14]   flags_changed: {'ctk': 'q8_0', 'ctv': 'q8_0', 'ctx_size': 16384}  extra: ['--override-tensor "blk\\.(2[0-9])\\..*exps.*=CPU"']
[16:59:14]   Stopping prod server...
[16:59:19]   cmd: -ctk q8_0 -ctv q8_0 --ctx-size 16384 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --alias gemma4 --mlock --override-tensor "blk\.(2[0-9])\..*exps.*=CPU"
[17:01:21]   Server failed to start — restarting prod...
[17:01:24] 
  FAILED (server failed to start)
[17:01:24] 
────────────────────────────────────────────────────────────
[17:01:24]   ITERATION 5/12
[17:01:24] ────────────────────────────────────────────────────────────
[17:01:24]   Generating seed (attempt 1)...
[17:01:32]   Seed: "Deep CPU Offload with Reduced Context for High-Precision KV"
[17:01:32]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[17:01:32]   Hypothesis: Offloading layers 20-29 to CPU will free sufficient VRAM to allow a 16k context with q8_0 KV cache without OOMing.
[17:01:32]   Accepted (6/6)
[17:01:32] 
  Running: Deep CPU Offload with Reduced Context for High-Precision KV
[17:01:32]   Hypothesis: Offloading layers 20-29 to CPU will free sufficient VRAM to allow a 16k context with q8_0 KV cache without OOMing.
[17:01:32]   flags_changed: {'ctx_size': '16384', 'ctk': 'q8_0', 'ctv': 'q8_0'}  extra: ['--override-tensor "blk\\.(2[0-9])\\..*exps.*=CPU"']
[17:01:32]   Stopping prod server...
[17:01:37]   cmd: -ctk q8_0 -ctv q8_0 --ctx-size 16384 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --alias gemma4 --mlock --override-tensor "blk\.(2[0-9])\..*exps.*=CPU"
[17:03:39]   Server failed to start — restarting prod...
[17:03:42] 
  FAILED (server failed to start)
[17:03:42] 
────────────────────────────────────────────────────────────
[17:03:42]   ITERATION 6/12
[17:03:42] ────────────────────────────────────────────────────────────
[17:03:42]   Generating seed (attempt 1)...
[17:03:51]   Seed: "Aggressive CPU Offload (12 layers) + Context Reduction for Q4 KV"
[17:03:51]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[17:03:51]   Hypothesis: By offloading 12 layers to CPU, we free enough VRAM to run a reduced context (16384) with high-precision q8_0 KV cache to test if the memory bandwidth savings on the GPU outweigh the CPU transfer overhead.
[17:03:51]   Accepted (6/6)
[17:03:51] 
  Running: Aggressive CPU Offload (12 layers) + Context Reduction for Q4 KV
[17:03:51]   Hypothesis: By offloading 12 layers to CPU, we free enough VRAM to run a reduced context (16384) with high-precision q8_0 KV cache to test if the memory bandwidth savings on the GPU outweigh the CPU transfer overhead.
[17:03:51]   flags_changed: {'ctx_size': 16384, 'ctk': 'q8_0', 'ctv': 'q8_0'}  extra: ['--override-tensor "blk\\.(1[89]|2[0-9])\\..*exps.*=CPU"', '--defrag-thold 0.1']
[17:03:51]   Stopping prod server...
[17:03:56]   cmd: -ctk q8_0 -ctv q8_0 --ctx-size 16384 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --alias gemma4 --mlock --override-tensor "blk\.(1[89]|2[0-9])\..*exps.*=CPU" --defrag-thold 0.1
[17:05:59]   Server failed to start — restarting prod...
[17:06:02] 
  FAILED (server failed to start)
[17:06:02] 
────────────────────────────────────────────────────────────
[17:06:02]   ITERATION 7/12
[17:06:02] ────────────────────────────────────────────────────────────
[17:06:02]   Generating seed (attempt 1)...
[17:06:10]   Seed: "Deep CPU Offload + Context Compression + Q4_NL KV"
[17:06:10]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[17:06:10]   Hypothesis: Increasing CPU offload to 10 layers and reducing context to 16384 will provide enough VRAM headroom to use iq4_nl KV cache, potentially increasing gen speed via better cache packing.
[17:06:10]   Accepted (6/6)
[17:06:10] 
  Running: Deep CPU Offload + Context Compression + Q4_NL KV
[17:06:10]   Hypothesis: Increasing CPU offload to 10 layers and reducing context to 16384 will provide enough VRAM headroom to use iq4_nl KV cache, potentially increasing gen speed via better cache packing.
[17:06:10]   flags_changed: {'ctk': 'iq4_nl', 'ctv': 'iq4_nl', 'ctx_size': 16384}  extra: ['--override-tensor "blk\\.(2[0-9])\\..*exps.*=CPU"', '--defrag-thold 0.5']
[17:06:10]   Stopping prod server...
[17:06:15]   cmd: -ctk iq4_nl -ctv iq4_nl --ctx-size 16384 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --alias gemma4 --mlock --override-tensor "blk\.(2[0-9])\..*exps.*=CPU" --defrag-thold 0.5
[17:08:17]   Server failed to start — restarting prod...
[17:08:20] 
  FAILED (server failed to start)
[17:08:20] 
────────────────────────────────────────────────────────────
[17:08:20]   ITERATION 8/12
[17:08:20] ────────────────────────────────────────────────────────────
[17:08:20]   Generating seed (attempt 1)...
[17:08:29]   Seed: "Moderate CPU Offload + Q5_0 KV with 16k Context"
[17:08:29]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[17:08:29]   Hypothesis: By offloading 10 layers to CPU (blk.20-29) and reducing context to 16384, we free enough VRAM to use q5_0 KV cache to balance precision and speed.
[17:08:29]   Accepted (6/6)
[17:08:29] 
  Running: Moderate CPU Offload + Q5_0 KV with 16k Context
[17:08:29]   Hypothesis: By offloading 10 layers to CPU (blk.20-29) and reducing context to 16384, we free enough VRAM to use q5_0 KV cache to balance precision and speed.
[17:08:29]   flags_changed: {'ctk': 'q5_0', 'ctv': 'q5_0', 'ctx_size': '16384'}  extra: ['--override-tensor "blk\\.(2[0-9])\\..*exps.*=CPU"', '--defrag-thold 0.1']
[17:08:29]   Stopping prod server...
[17:08:34]   cmd: -ctk q5_0 -ctv q5_0 --ctx-size 16384 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --alias gemma4 --mlock --override-tensor "blk\.(2[0-9])\..*exps.*=CPU" --defrag-thold 0.1
[17:10:36]   Server failed to start — restarting prod...
[17:10:39] 
  FAILED (server failed to start)
[17:10:39] 
────────────────────────────────────────────────────────────
[17:10:39]   ITERATION 9/12
[17:10:39] ────────────────────────────────────────────────────────────
[17:10:39]   Generating seed (attempt 1)...
[17:10:47]   Seed: "Deep CPU Offload + 16k Context + Q8 KV"
[17:10:47]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[17:10:47]   Hypothesis: Offloading 10 layers to CPU and reducing ctx_size to 16384 will free enough VRAM to support q8_0 KV cache without OOMing.
[17:10:47]   Accepted (6/6)
[17:10:47] 
  Running: Deep CPU Offload + 16k Context + Q8 KV
[17:10:47]   Hypothesis: Offloading 10 layers to CPU and reducing ctx_size to 16384 will free enough VRAM to support q8_0 KV cache without OOMing.
[17:10:47]   flags_changed: {'ctk': 'q8_0', 'ctv': 'q8_0', 'ctx_size': 16384}  extra: ['--override-tensor "blk\\.(2[0-9])\\..*exps.*=CPU"']
[17:10:47]   Stopping prod server...
[17:10:52]   cmd: -ctk q8_0 -ctv q8_0 --ctx-size 16384 --ubatch-size 1024 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --alias gemma4 --mlock --override-tensor "blk\.(2[0-9])\..*exps.*=CPU"


======================================================================
# Autoresearch supergemma4-26b single-GPU — 2026-04-19 17:14
======================================================================
[17:14:05] 
────────────────────────────────────────────────────────────
[17:14:05]   AUTORESEARCH — supergemma4-26b single GPU  (2026-04-19 17:14)
[17:14:05] ────────────────────────────────────────────────────────────
[17:14:05] Baseline: gen=61.7 tok/s  prompt=281.9 tok/s
[17:14:05] Gate: 5/6  |  Max iterations: 12

[17:14:05] 
────────────────────────────────────────────────────────────
[17:14:05]   ITERATION 1/12
[17:14:05] ────────────────────────────────────────────────────────────
[17:14:05]   Generating seed (attempt 1)...
[17:14:12]   Seed: "E-core Threading Optimization for CPU Experts"
[17:14:12]   Score: 6/6  |  {'novelty': 1, 'feasibility': 1, 'impact': 1, 'safety': 1, 'measurable': 1, 'orthogonality': 1}
[17:14:12]   Hypothesis: Utilizing the 12 E-cores via threads=12 with cpu_range 0-19 will maximize throughput for the CPU-offloaded expert layers without increasing VRAM usage.
[17:14:12]   Accepted (6/6)
[17:14:12] 
  Running: E-core Threading Optimization for CPU Experts
[17:14:12]   Hypothesis: Utilizing the 12 E-cores via threads=12 with cpu_range 0-19 will maximize throughput for the CPU-offloaded expert layers without increasing VRAM usage.
[17:14:12]   flags_changed: {'threads': 12, 'cpu_range': '0-19'}  extra: ['--override-tensor', 'blk\\.(2[4-9])\\..*exps.*=CPU']
[17:14:12]   Stopping prod server...
[17:14:17]   cmd: -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 1024 --threads 12 --threads-batch 8 --cpu-range 0-19 --cpu-range-batch 0-19 --cpu-strict 1 --alias gemma4 --mlock --override-tensor blk.(2[4-9])..*exps.*=CPU
[17:14:20]   Server up — benchmarking...


======================================================================
# Autoresearch supergemma4-26b single-GPU — 2026-04-19 17:17
======================================================================
[17:17:55] 
────────────────────────────────────────────────────────────
  AUTORESEARCH supergemma4-26b single-GPU  2026-04-19 17:17
────────────────────────────────────────────────────────────
[17:17:55] Baseline: gen=61.7 tok/s  prompt=281.9 tok/s
[17:17:55] Iterations: 20  |  One variable per experiment

[17:17:55] 
────────────────────────────────────────────────────────────
  ITERATION 1/20  (best so far: 61.7 tok/s)
────────────────────────────────────────────────────────────
[17:17:57]   LLM picked [1]: ubatch 2048
[17:17:57]   Reasoning: Increasing ubatch_size to 2048 will better saturate GPU compute during the prompt phase and potentially improve generation throughput by increasing the batch size of the kernel launches.
[17:17:57]   Changing: ubatch_size → 2048  (extra: [])
[17:17:57]   Stopping prod...
[17:18:02]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 2048 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[4-9])\..*exps.*=CPU
[17:18:05]   fast-fail: OOM detected
[17:18:07]   Server failed — restarting prod, marking FAILED
[17:18:10] 
────────────────────────────────────────────────────────────
  ITERATION 2/20  (best so far: 61.7 tok/s)
────────────────────────────────────────────────────────────
[17:18:12]   LLM picked [0]: ubatch 512
[17:18:12]   Reasoning: Since ubatch 2048 failed to improve performance, reducing it to 512 will lower memory pressure and potentially improve cache hits for the prompt processing phase.
[17:18:12]   Changing: ubatch_size → 512  (extra: [])
[17:18:12]   Stopping prod...
[17:18:17]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[4-9])\..*exps.*=CPU
[17:18:26]   run 1: gen=63.3  prompt=228.3
[17:18:33]   run 2: gen=62.0  prompt=290.5
[17:18:39]   run 3: gen=65.3  prompt=283.0
[17:18:44]   Restarting prod...
[17:18:47]   gen: 63.6 tok/s  (Δ+1.9)  prompt: 267.3
[17:18:47]   ✓ NEW BEST: 63.6 tok/s
[17:18:47] 
────────────────────────────────────────────────────────────
  ITERATION 3/20  (best so far: 63.6 tok/s)
────────────────────────────────────────────────────────────
[17:18:48]   LLM picked [5]: cpu layers 4 (26-29)
[17:18:48]   Reasoning: Reducing CPU layers to 4 shifts more computation to the GPU, which is likely to improve generation speed given the current VRAM headroom.
[17:18:48]   Changing: override_layers → 2[6-9]  (extra: [])
[17:18:48]   Stopping prod...
[17:18:53]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 8 --threads-batch 8 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU
[17:19:02]   run 1: gen=67.6  prompt=279.4
[17:19:08]   run 2: gen=67.9  prompt=334.0
[17:19:14]   run 3: gen=70.3  prompt=331.8
[17:19:18]   Restarting prod...
[17:19:21]   gen: 68.6 tok/s  (Δ+5.0)  prompt: 315.1
[17:19:21]   ✓ NEW BEST: 68.6 tok/s
[17:19:21] 
────────────────────────────────────────────────────────────
  ITERATION 4/20  (best so far: 68.6 tok/s)
────────────────────────────────────────────────────────────
[17:19:25]   LLM picked [1]: threads 4
[17:19:25]   Reasoning: Reducing threads to 4 minimizes context switching and scheduling overhead for the CPU-offloaded layers, which showed a significant performance gain in previous attempts.
[17:19:25]   Changing: threads → 4  (extra: [])
[17:19:25]   Stopping prod...
[17:20:01]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 4 --threads-batch 4 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU
[17:20:10]   run 1: gen=70.5  prompt=240.5
[17:20:16]   run 2: gen=70.0  prompt=308.8
[17:20:21]   run 3: gen=71.4  prompt=304.8
[17:20:26]   Restarting prod...
[17:20:29]   gen: 70.6 tok/s  (Δ+2.0)  prompt: 284.7
[17:20:29]   ✓ NEW BEST: 70.6 tok/s
[17:20:29] 
────────────────────────────────────────────────────────────
  ITERATION 5/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:20:31]   LLM picked [1]: threads 6
[17:20:31]   Reasoning: Increasing threads from 4 to 6 is the logical next step to optimize the CPU-offloaded expert computation based on the successful trend of previous thread adjustments.
[17:20:31]   Changing: threads → 6  (extra: [])
[17:20:31]   Stopping prod...
[17:20:36]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 6 --threads-batch 6 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU
[17:20:45]   run 1: gen=69.2  prompt=247.4
[17:20:51]   run 2: gen=66.6  prompt=308.7
[17:20:57]   run 3: gen=67.1  prompt=315.7
[17:21:01]   Restarting prod...
[17:21:04]   gen: 67.6 tok/s  (Δ-3.0)  prompt: 290.6
[17:21:04]   ✗ No improvement — reverting to best
[17:21:04] 
────────────────────────────────────────────────────────────
  ITERATION 6/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:21:06]   LLM picked [3]: cpu layers 8 (22-29)
[17:21:06]   Reasoning: Increasing CPU layers to 8 (22-29) tests the scaling of the current trend where increasing CPU offload improved performance by 5.0 tok/s.
[17:21:06]   Changing: override_layers → 2[2-9]  (extra: [])
[17:21:06]   Stopping prod...
[17:21:11]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 4 --threads-batch 4 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[2-9])\..*exps.*=CPU
[17:21:20]   run 1: gen=62.5  prompt=179.0
[17:21:27]   run 2: gen=60.0  prompt=192.7
[17:21:34]   run 3: gen=61.7  prompt=189.4
[17:21:38]   Restarting prod...
[17:21:41]   gen: 61.4 tok/s  (Δ-9.2)  prompt: 187.0
[17:21:41]   ✗ No improvement — reverting to best
[17:21:41] 
────────────────────────────────────────────────────────────
  ITERATION 7/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:21:42]   LLM picked [4]: defrag 0.1
[17:21:42]   Reasoning: Since VRAM headroom is limited, a lightweight KV cache defragmentation strategy is a low-risk, VRAM-neutral way to optimize memory throughput and reduce fragmentation overhead.
[17:21:42]   Changing: extra → ['--defrag-thold', '0.1']  (extra: ['--defrag-thold', '0.1'])
[17:21:42]   Stopping prod...
[17:21:48]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 4 --threads-batch 4 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU --defrag-thold 0.1
[17:21:56]   run 1: gen=71.9  prompt=235.2
[17:22:02]   run 2: zero result — aborting bench
[17:22:06]   Restarting prod...
[17:22:09]   Bench failed
[17:22:09] 
────────────────────────────────────────────────────────────
  ITERATION 8/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:22:10]   LLM picked [1]: threads 12 all-core
[17:22:10]   Reasoning: Increasing threads to 12 leverages more physical cores for the CPU-offloaded expert layers which previously showed improvement when increasing layers.
[17:22:10]   Changing: threads → 12  (extra: [])
[17:22:10]   Stopping prod...
[17:22:16]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 12 --threads-batch 12 --cpu-range 0-19 --cpu-range-batch 0-19 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU
[17:22:25]   run 1: gen=60.1  prompt=272.8
[17:22:32]   run 2: gen=60.5  prompt=341.5
[17:22:38]   run 3: gen=60.6  prompt=336.8
[17:22:43]   Restarting prod...
[17:22:46]   gen: 60.4 tok/s  (Δ-10.2)  prompt: 317.0
[17:22:46]   ✗ No improvement — reverting to best
[17:22:46] 
────────────────────────────────────────────────────────────
  ITERATION 9/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:22:47]   LLM picked [4]: no-mmap
[17:22:47]   Reasoning: Disabling mmap can improve memory access patterns and cache locality by forcing the model into physical RAM, which is a zero-VRAM-cost optimization.
[17:22:47]   Changing: extra → ['--no-mmap']  (extra: ['--no-mmap'])
[17:22:47]   Stopping prod...
[17:22:52]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 4 --threads-batch 4 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU --no-mmap
[17:23:01]   run 1: gen=71.3  prompt=241.9
[17:23:07]   run 2: gen=69.7  prompt=305.7
[17:23:13]   run 3: gen=70.7  prompt=306.9
[17:23:18]   Restarting prod...
[17:23:21]   gen: 70.6 tok/s  (Δ-0.0)  prompt: 284.8
[17:23:21]   ✗ No improvement — reverting to best
[17:23:21] 
────────────────────────────────────────────────────────────
  ITERATION 10/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:23:22]   LLM picked [2]: cpu layers 10 (20-29)
[17:23:22]   Reasoning: Increasing CPU layers to 10 provides a better balance between GPU compute saturation and CPU overhead, building on the successful 4-layer experiment.
[17:23:22]   Changing: override_layers → 2[0-9]  (extra: [])
[17:23:22]   Stopping prod...
[17:23:27]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 4 --threads-batch 4 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[0-9])\..*exps.*=CPU
[17:23:37]   run 1: gen=58.0  prompt=146.8
[17:23:44]   run 2: gen=57.1  prompt=157.3
[17:23:51]   run 3: gen=55.9  prompt=169.2
[17:23:56]   Restarting prod...
[17:23:59]   gen: 57.0 tok/s  (Δ-13.6)  prompt: 157.8
[17:23:59]   ✗ No improvement — reverting to best
[17:23:59] 
────────────────────────────────────────────────────────────
  ITERATION 11/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:24:00]   LLM picked [1]: threads 16 all-core
[17:24:00]   Reasoning: Increasing threads to 16 targets the CPU-bound expert computation to maximize throughput on the available 20-core architecture.
[17:24:00]   Changing: threads → 16  (extra: [])
[17:24:00]   Stopping prod...
[17:24:05]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 16 --threads-batch 16 --cpu-range 0-19 --cpu-range-batch 0-19 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU
[17:24:15]   run 1: gen=58.6  prompt=271.5
[17:24:22]   run 2: gen=58.5  prompt=335.2
[17:24:29]   run 3: gen=59.1  prompt=338.4
[17:24:33]   Restarting prod...
[17:24:36]   gen: 58.7 tok/s  (Δ-11.9)  prompt: 315.1
[17:24:36]   ✗ No improvement — reverting to best
[17:24:36] 
────────────────────────────────────────────────────────────
  ITERATION 12/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:24:37]   LLM picked [1]: defrag 0.5
[17:24:37]   Reasoning: Since defrag 0.1 showed no change, a more aggressive 0.5 threshold might better optimize KV cache fragmentation to reclaim bandwidth for generation.
[17:24:37]   Changing: extra → ['--defrag-thold', '0.5']  (extra: ['--defrag-thold', '0.5'])
[17:24:37]   Stopping prod...
[17:24:42]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 4 --threads-batch 4 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU --defrag-thold 0.5
[17:24:51]   run 1: gen=71.1  prompt=243.0
[17:24:56]   run 2: gen=70.8  prompt=300.8
[17:25:02]   run 3: gen=70.9  prompt=295.6
[17:25:07]   Restarting prod...
[17:25:10]   gen: 70.9 tok/s  (Δ+0.3)  prompt: 279.8
[17:25:10]   ✗ No improvement — reverting to best
[17:25:10] 
────────────────────────────────────────────────────────────
  ITERATION 13/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:25:11]   LLM picked [2]: cpu-strict off
[17:25:11]   Reasoning: Since CPU-offloaded layers showed performance gains when specific layers were targeted, allowing the OS scheduler more flexibility for CPU experts is the most likely way to optimize the current bottleneck without increasing VRAM usage.
[17:25:11]   Changing: extra → ['--cpu-strict', '0']  (extra: ['--cpu-strict', '0'])
[17:25:11]   Stopping prod...
[17:25:16]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 4 --threads-batch 4 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU --cpu-strict 0
[17:25:25]   run 1: gen=70.8  prompt=249.5
[17:25:30]   run 2: gen=71.4  prompt=293.4
[17:25:36]   run 3: gen=70.2  prompt=297.3
[17:25:40]   Restarting prod...
[17:25:43]   gen: 70.8 tok/s  (Δ+0.2)  prompt: 280.1
[17:25:43]   ✗ No improvement — reverting to best
[17:25:43] 
────────────────────────────────────────────────────────────
  ITERATION 14/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:25:45]   LLM picked [0]: ubatch 4096
[17:25:45]   Reasoning: Increasing ubatch to 4096 is a VRAM-neutral way to maximize GPU compute saturation, whereas parallel 2 might exceed the available 900 MiB headroom.
[17:25:45]   Changing: ubatch_size → 4096  (extra: [])
[17:25:45]   Stopping prod...
[17:25:50]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 4096 --threads 4 --threads-batch 4 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU
[17:25:53]   fast-fail: OOM detected
[17:25:55]   Server failed — restarting prod, marking FAILED
[17:25:58] 
────────────────────────────────────────────────────────────
  ITERATION 15/20  (best so far: 70.6 tok/s)
────────────────────────────────────────────────────────────
[17:26:00]   LLM picked [0]: parallel 2
[17:26:00]   Reasoning: Testing parallel slots is a logical next step to increase throughput by saturating the GPU with multiple concurrent requests, though it will increase VRAM usage.
[17:26:00]   Changing: extra → ['--parallel', '2']  (extra: ['--parallel', '2'])
[17:26:00]   Stopping prod...
[17:26:05]   $ --port 8090 --n-gpu-layers 999 --flash-attn on -ctk q4_0 -ctv q4_0 --ctx-size 32768 --ubatch-size 512 --threads 4 --threads-batch 4 --cpu-range 0-7 --cpu-range-batch 0-7 --cpu-strict 1 --mlock --alias gemma4 --override-tensor blk\.(2[6-9])\..*exps.*=CPU --parallel 2
[17:26:13]   run 1: gen=70.5  prompt=242.6
[17:26:19]   run 2: gen=70.8  prompt=307.5
[17:26:25]   run 3: gen=72.0  prompt=289.9
[17:26:29]   Restarting prod...
[17:26:32]   gen: 71.1 tok/s  (Δ+0.5)  prompt: 280.0
[17:26:32]   ✓ NEW BEST: 71.1 tok/s
[17:26:32] 
────────────────────────────────────────────────────────────
  ITERATION 16/20  (best so far: 71.1 tok/s)
────────────────────────────────────────────────────────────
[17:26:32]   All candidates exhausted — done
[17:26:32] 
────────────────────────────────────────────────────────────
  FINAL SUMMARY
────────────────────────────────────────────────────────────
[17:26:32] Baseline:   61.7 tok/s gen
[17:26:32] Final best: 71.1 tok/s gen  (Δ+9.4)
[17:26:32] Best extra flags: ['--parallel', '2']
[17:26:32] Written to /home/dino/inference-research/current-best-flags-supergemma-1gpu.sh
