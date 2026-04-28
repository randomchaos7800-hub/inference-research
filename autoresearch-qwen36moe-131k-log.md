

======================================================================
# Autoresearch Qwen3.6-35B-A3B 131K pass 2 — 2026-04-22 11:55
======================================================================

## AUTORESEARCH Qwen3.6-35B-A3B 131K pass 2  2026-04-22 11:55

[11:55:59] Baseline: tg512=97.34 tok/s (q4_0 KV, ctx=131072)  pp512=2426 tok/s
[11:55:59] Iterations: 20  |  Improve threshold: 0.8 tok/s

[11:55:59] Checking prod server health...
[11:55:59] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 97.34 tok/s)

[11:56:01]   LLM picked [1]: no-kv-offload
[11:56:01]   Reasoning: Disabling KV offload (nkvo=0) is the current baseline, but the candidate list implies testing nkvo=1 (KV on CPU) to free VRAM; however, given the explicit constraint 'q4_0 KV locked' and 'f16 would OOM', moving KV to CPU (nkvo=1) is the only remaining structural change that significantly alters memory bandwidth dynamics for the O(n) attention layers without hitting VRAM limits, potentially improving throughput if PCIe bandwidth is sufficient compared to current GPU-bound constraints.
[11:56:01]   Changing: nkvo → 1  depth=0  extra=[]
[11:56:01]   Stopping prod server for bench...
[11:56:05]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 1 -mg 0 -d 0 -p 512 -n 512 -r 3 -o md
[11:57:54]   Restarting prod server...
[11:58:00]   tg512: 14.68 tok/s  (Δ-82.66 vs best)  pp512: 1533
[11:58:00]   No improvement (-82.66) — reverting
[11:58:00] 

## ITERATION 2/20  (best so far: 97.34 tok/s)

[11:58:02]   LLM picked [0]: flash-attn off
[11:58:02]   Reasoning: Disabling flash attention is the highest-impact remaining variable to test, as the O(n^2) CPU fallback may bypass GPU memory bandwidth bottlenecks or kernel launch overheads that currently limit throughput at this specific context length and quantization.
[11:58:02]   Changing: flash_attn → 0  depth=0  extra=[]
[11:58:02]   Stopping prod server for bench...
[11:58:05]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 0 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 0 -p 512 -n 512 -r 3 -o md
[11:58:08]   bench failed (exit 1)
[11:58:08]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to create context with model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:58:08]   Restarting prod server...
[11:58:15]   Bench failed — marking FAILED

## ITERATION 3/20  (best so far: 97.34 tok/s)

[11:58:16]   LLM picked [6]: depth 4096
[11:58:16]   Reasoning: Since the architecture has O(1) attention layers for the majority of the context, testing the shortest depth (4096) establishes the theoretical maximum throughput ceiling for the MoE routing and compute, allowing us to quantify the exact performance penalty introduced by the O(n) layers at longer contexts.
[11:58:16]   Changing: n_depth → 4096  depth=4096  extra=[]
[11:58:16]   Stopping prod server for bench...
[11:58:19]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 4096 -p 512 -n 512 -r 3 -o md
[11:58:42]   Restarting prod server...
[11:58:48]   tg512: 93.52 tok/s  (Δ-3.82 vs baseline)  pp512: 2311
[11:58:48]   Depth info: 93.52 tok/s at d=4096
[11:58:48] 

## ITERATION 4/20  (best so far: 97.34 tok/s)

[11:58:49]   LLM picked [10]: depth 131000
[11:58:49]   Reasoning: Since the architecture has 48 O(1) layers and 16 O(n) layers, the throughput degradation at depth is primarily driven by the O(n) attention layers; characterizing the curve up to the full 131K context is critical to determine if the O(1) layers allow for a flatter degradation profile than expected, which informs whether the current depth is a bottleneck or if the model scales efficiently.
[11:58:49]   Changing: n_depth → 131000  depth=131000  extra=[]
[11:58:49]   Stopping prod server for bench...
[11:58:53]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 131000 -p 512 -n 512 -r 3 -o md
[12:00:26]   Restarting prod server...
[12:00:32]   tg512: 39.72 tok/s  (Δ-57.62 vs baseline)  pp512: 1093
[12:00:32]   Depth info: 39.72 tok/s at d=131000
[12:00:32] 

## ITERATION 5/20  (best so far: 97.34 tok/s)

[12:00:34]   LLM picked [1]: ubatch 2048
[12:00:34]   Reasoning: Since ubatch=4096 was previously ruled out but the KV cache quantization changed to q4_0 (reducing memory bandwidth pressure compared to f16), re-testing ubatch=2048 is critical to determine if the smaller memory footprint allows for better GPU occupancy and throughput without the overhead of larger batches.
[12:00:34]   Changing: ubatch_size → 2048  depth=0  extra=[]
[12:00:34]   Stopping prod server for bench...
[12:00:37]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 2048 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 0 -p 512 -n 512 -r 3 -o md
[12:00:57]   Restarting prod server...
[12:01:03]   tg512: 97.51 tok/s  (Δ+0.17 vs best)  pp512: 2416
[12:01:03]   No improvement (+0.17) — reverting
[12:01:03] 

## ITERATION 6/20  (best so far: 97.34 tok/s)

[12:01:05]   LLM picked [9]: batch 4096
[12:01:05]   Reasoning: Increasing the batch size to 4096 maximizes GPU occupancy for the prefill phase (pp512), which is critical for hiding latency and maintaining high throughput in MoE architectures, whereas thread and depth changes primarily affect generation speed or are already suboptimal.
[12:01:05]   Changing: batch_size → 4096  depth=0  extra=[]
[12:01:05]   Stopping prod server for bench...
[12:01:08]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 4096 --split-mode layer -nkvo 0 -mg 0 -d 0 -p 512 -n 512 -r 3 -o md
[12:01:28]   Restarting prod server...
[12:01:35]   tg512: 96.68 tok/s  (Δ-0.66 vs best)  pp512: 2414
[12:01:35]   No improvement (-0.66) — reverting
[12:01:35] 

## ITERATION 7/20  (best so far: 97.34 tok/s)

[12:01:36]   LLM picked [2]: threads 16 d32k
[12:01:36]   Reasoning: With 16 full-attention layers dominating the compute and 8 threads currently used, increasing to 16 threads at a moderate 32K depth is the most likely to unlock parallelization gains in the O(n) attention mechanism without the severe scaling penalties observed at 131K context.
[12:01:36]   Changing: threads → 16  depth=32768  extra=[]
[12:01:36]   Stopping prod server for bench...
[12:01:39]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 16 --cpu-mask 0xFFFFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 32768 -p 512 -n 512 -r 3 -o md
[12:02:14]   Restarting prod server...
[12:02:20]   tg512: 71.75 tok/s  (Δ-25.59 vs best)  pp512: 1847
[12:02:20]   No improvement (-25.59) — reverting
[12:02:20] 

## ITERATION 8/20  (best so far: 97.34 tok/s)

[12:02:22]   LLM picked [0]: main-gpu 1
[12:02:22]   Reasoning: With q4_0 KV cache locking the model to a single GPU and tensor-split bias ruled out, testing the secondary GPU as main is the highest-leverage remaining architectural variable to optimize PCIe bandwidth utilization or layer distribution for this specific MoE topology.
[12:02:22]   Changing: main_gpu → 1  depth=0  extra=[]
[12:02:22]   Stopping prod server for bench...
[12:02:25]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 1 -d 0 -p 512 -n 512 -r 3 -o md
[12:02:45]   Restarting prod server...
[12:02:51]   tg512: 97.57 tok/s  (Δ+0.23 vs best)  pp512: 2418
[12:02:51]   No improvement (+0.23) — reverting
[12:02:51] 

## ITERATION 9/20  (best so far: 97.34 tok/s)

[12:02:52]   LLM picked [2]: threads 20 d32k
[12:02:52]   Reasoning: Increasing threads to 20 is the most logical next step to maximize parallelism for the 48 GDN layers which are O(1) in context and likely under-utilized on 8 threads, whereas depth tests only characterize scaling rather than improving baseline speed.
[12:02:52]   Changing: threads → 20  depth=32768  extra=[]
[12:02:52]   Stopping prod server for bench...
[12:02:56]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 20 --cpu-mask 0xFFFFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 32768 -p 512 -n 512 -r 3 -o md
[12:03:31]   Restarting prod server...
[12:03:37]   tg512: 71.54 tok/s  (Δ-25.80 vs best)  pp512: 1847
[12:03:37]   No improvement (-25.80) — reverting
[12:03:37] 

## ITERATION 10/20  (best so far: 97.34 tok/s)

[12:03:38]   LLM picked [7]: no-mmap
[12:03:38]   Reasoning: Since ubatch and thread count variations have shown negligible gains and flash attention is already enabled, disabling mmap is the most plausible remaining low-level optimization to reduce memory access latency for the KV cache in a q4_0 configuration.
[12:03:38]   Changing: extra → ['-mmp', '0']  depth=0  extra=['-mmp', '0']
[12:03:38]   Stopping prod server for bench...
[12:03:41]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 0 -p 512 -n 512 -r 3 -o md -mmp 0
[12:04:02]   Restarting prod server...
[12:04:08]   tg512: 97.30 tok/s  (Δ-0.04 vs best)  pp512: 2417
[12:04:08]   No improvement (-0.04) — reverting
[12:04:08] 

## ITERATION 11/20  (best so far: 97.34 tok/s)

[12:04:09]   LLM picked [2]: depth 16384
[12:04:09]   Reasoning: Given the steep O(n) degradation in the 16 full-attn layers, measuring tg speed at 16K depth provides a critical intermediate data point to characterize the performance cliff between 4K and 32K, helping to identify if the bottleneck is purely memory bandwidth or attention compute scaling.
[12:04:09]   Changing: n_depth → 16384  depth=16384  extra=[]
[12:04:09]   Stopping prod server for bench...
[12:04:13]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 16384 -p 512 -n 512 -r 3 -o md
[12:04:40]   Restarting prod server...
[12:04:46]   tg512: 82.44 tok/s  (Δ-14.90 vs baseline)  pp512: 2076
[12:04:46]   Depth info: 82.44 tok/s at d=16384
[12:04:46] 

## ITERATION 12/20  (best so far: 97.34 tok/s)

[12:04:47]   LLM picked [2]: depth 32768
[12:04:47]   Reasoning: Since depth scaling is the dominant bottleneck and 32K is the previous baseline, testing this specific depth provides the critical anchor point to model the performance decay curve between the current 131K and the 4K baseline.
[12:04:47]   Changing: n_depth → 32768  depth=32768  extra=[]
[12:04:47]   Stopping prod server for bench...
[12:04:51]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 32768 -p 512 -n 512 -r 3 -o md
[12:05:26]   Restarting prod server...
[12:05:32]   tg512: 71.62 tok/s  (Δ-25.72 vs baseline)  pp512: 1846
[12:05:32]   Depth info: 71.62 tok/s at d=32768
[12:05:32] 

## ITERATION 13/20  (best so far: 97.34 tok/s)

[12:05:33]   LLM picked [2]: depth 65536
[12:05:33]   Reasoning: Given the steep performance degradation at depth (halving at 2x depth), characterizing the 65K depth point is critical to understanding the O(n) attention bottleneck and determining if the current context window usage is near a performance cliff, which informs whether optimization efforts should focus on context management rather than micro-tuning.
[12:05:33]   Changing: n_depth → 65536  depth=65536  extra=[]
[12:05:33]   Stopping prod server for bench...
[12:05:36]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 65536 -p 512 -n 512 -r 3 -o md
[12:06:29]   Restarting prod server...
[12:06:35]   tg512: 56.50 tok/s  (Δ-40.84 vs baseline)  pp512: 1501
[12:06:35]   Depth info: 56.50 tok/s at d=65536
[12:06:35] 

## ITERATION 14/20  (best so far: 97.34 tok/s)

[12:06:36]   LLM picked [2]: depth 98304
[12:06:36]   Reasoning: Since all standard parameter tuning attempts have yielded negligible gains and the architecture is dominated by O(n) attention layers, characterizing the performance curve at 98K depth provides the most critical data to understand the scaling limits and potential bottlenecks before concluding optimization is exhausted.
[12:06:36]   Changing: n_depth → 98304  depth=98304  extra=[]
[12:06:36]   Stopping prod server for bench...
[12:06:39]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 98304 -p 512 -n 512 -r 3 -o md
[12:07:51]   Restarting prod server...
[12:07:57]   tg512: 46.95 tok/s  (Δ-50.39 vs baseline)  pp512: 1270
[12:07:57]   Depth info: 46.95 tok/s at d=98304
[12:07:57] 

## ITERATION 15/20  (best so far: 97.34 tok/s)

[12:07:58]   LLM picked [0]: ubatch 1024
[12:07:58]   Reasoning: Since the current ubatch of 4096 is significantly larger than the batch size of 2048 and previous tests showed negligible gains from ubatch changes, testing 1024 is the most logical remaining hyperparameter to check for optimal parallelism overlap or memory bandwidth saturation before concluding that the bottleneck is purely compute-bound by the attention layers.
[12:07:58]   Changing: ubatch_size → 1024  depth=0  extra=[]
[12:07:58]   Stopping prod server for bench...
[12:08:02]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 0 -p 512 -n 512 -r 3 -o md
[12:08:22]   Restarting prod server...
[12:08:28]   tg512: 97.61 tok/s  (Δ+0.27 vs best)  pp512: 2413
[12:08:28]   No improvement (+0.27) — reverting
[12:08:28] 

## ITERATION 16/20  (best so far: 97.34 tok/s)

[12:08:29]   LLM picked [1]: no mlock
[12:08:29]   Reasoning: Since thread count scaling has already been exhausted with negative results and mlock is a low-risk system-level optimization that can reduce page fault overhead on large context windows, it is the most viable remaining candidate to potentially recover the slight performance delta.
[12:08:29]   Changing: mlock → False  depth=0  extra=[]
[12:08:29]   Stopping prod server for bench...
[12:08:32]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 0 -p 512 -n 512 -r 3 -o md
[12:08:53]   Restarting prod server...
[12:08:59]   tg512: 96.74 tok/s  (Δ-0.60 vs best)  pp512: 2415
[12:08:59]   No improvement (-0.60) — reverting
[12:08:59] 

## ITERATION 17/20  (best so far: 97.34 tok/s)

[12:09:00]   LLM picked [0]: threads 12 d32k
[12:09:00]   Reasoning: Since thread counts of 16 and 20 degraded performance significantly at 32K depth, testing 12 threads at 32K depth is the most logical next step to identify the optimal parallelism sweet spot for the attention layers without incurring the overhead observed at higher thread counts.
[12:09:00]   Changing: threads → 12  depth=32768  extra=[]
[12:09:00]   Stopping prod server for bench...
[12:09:03]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 12 --cpu-mask 0xFFFFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -nkvo 0 -mg 0 -d 32768 -p 512 -n 512 -r 3 -o md
[12:09:38]   Restarting prod server...
[12:09:45]   tg512: 71.70 tok/s  (Δ-25.64 vs best)  pp512: 1842
[12:09:45]   No improvement (-25.64) — reverting
[12:09:45] 

## ITERATION 18/20  (best so far: 97.34 tok/s)

[12:09:45] All candidates exhausted — done

## FINAL SUMMARY

[12:09:45] Baseline:   tg512=97.34 tok/s
[12:09:45] Final best: tg512=97.34 tok/s  (Δ+0.00)
[12:09:45] Speed improvements: 0/17 experiments
[12:09:45] Depth characterization:
[12:09:45]   depth 4096: 93.52 tok/s
[12:09:45]   depth 131000: 39.72 tok/s
[12:09:45]   depth 16384: 82.44 tok/s
[12:09:45]   depth 32768: 71.62 tok/s
[12:09:45]   depth 65536: 56.50 tok/s
[12:09:45]   depth 98304: 46.95 tok/s
[12:09:45]   Best flags written to /home/dino/inference-research/current-best-flags-qwen36moe-131k.sh
