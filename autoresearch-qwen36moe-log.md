

======================================================================
# Autoresearch Qwen3.6-35B-A3B — 2026-04-22 11:02
======================================================================

## AUTORESEARCH Qwen3.6-35B-A3B  2026-04-22 11:02

[11:02:12] Baseline: tg512=100.24 tok/s  pp512=2436 tok/s
[11:02:12] Iterations: 20  |  One variable per experiment  |  Improve threshold: 1.0 tok/s
[11:02:12] Hardware: 2x RTX 5060 Ti (32 GB total), ~3.6 GB VRAM headroom at f16 KV

[11:02:12] Checking prod server health...
[11:02:12] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 100.24 tok/s)

[11:02:14]   LLM picked [17]: poll 100
[11:02:14]   Reasoning: Since the GDN sequential state update is the compute bottleneck rather than memory bandwidth, maximizing CPU polling to 100% minimizes GPU synchronization latency and ensures the CPU is always ready to feed the next step, reducing idle time during the sequential bottleneck.
[11:02:14]   Changing: extra → ['--poll', '100']  extra: ['--poll', '100']
[11:02:14]   Stopping prod server for bench...
[11:02:18]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md --poll 100
[11:02:19]   bench failed (exit 1)
[11:02:19]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to load model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:02:19]   Restarting prod server...
[11:02:19]   Bench failed — marking FAILED

## ITERATION 2/20  (best so far: 100.24 tok/s)

[11:02:20]   LLM picked [16]: poll 0
[11:02:20]   Reasoning: Switching to pure event-driven polling eliminates CPU busy-wait overhead and reduces synchronization latency, which is critical for maximizing throughput in GDN architectures where the bottleneck is sequential state updates rather than memory bandwidth.
[11:02:20]   Changing: extra → ['--poll', '0']  extra: ['--poll', '0']
[11:02:20]   Stopping prod server for bench...
[11:02:24]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md --poll 0
[11:02:25]   bench failed (exit 1)
[11:02:25]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to load model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:02:25]   Restarting prod server...
[11:02:25]   Bench failed — marking FAILED

## ITERATION 3/20  (best so far: 100.24 tok/s)

[11:02:26]   LLM picked [8]: threads 4
[11:02:26]   Reasoning: Since the GDN sequential state update is the CPU-bound bottleneck and current polling attempts failed to improve throughput, reducing thread contention by halving the thread count is the most direct way to minimize scheduling overhead and improve compute efficiency per token.
[11:02:26]   Changing: threads → 4  extra: []
[11:02:26]   Stopping prod server for bench...
[11:02:30]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 4 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:02:31]   bench failed (exit 1)
[11:02:31]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to load model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:02:31]   Restarting prod server...
[11:02:31]   Bench failed — marking FAILED

## ITERATION 4/20  (best so far: 100.24 tok/s)

[11:02:33]   LLM picked [16]: n-cpu-moe 1
[11:02:33]   Reasoning: Offloading one MoE expert layer to the CPU reduces GPU memory bandwidth pressure and VRAM usage, directly addressing the identified GDN sequential state bottleneck while freeing resources for the active layers.
[11:02:33]   Changing: extra → ['--n-cpu-moe', '1']  extra: ['--n-cpu-moe', '1']
[11:02:33]   Stopping prod server for bench...
[11:02:37]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md --n-cpu-moe 1
[11:02:38]   bench failed (exit 1)
[11:02:38]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to load model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:02:38]   Restarting prod server...
[11:02:38]   Bench failed — marking FAILED

## ITERATION 5/20  (best so far: 100.24 tok/s)

[11:02:39]   LLM picked [8]: threads 12 all
[11:02:39]   Reasoning: Since the GDN sequential state update is the CPU-bound bottleneck and previous attempts to reduce CPU threads failed, utilizing the full CPU core count (including E-cores) is the most logical step to maximize parallelism for the CPU-side GDN computations without impacting the GPU-bound MoE routing.
[11:02:39]   Changing: threads → 12  extra: []
[11:02:39]   Stopping prod server for bench...
[11:02:43]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 12 --cpu-mask 0xFFFFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:02:44]   bench failed (exit 1)
[11:02:44]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to load model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:02:44]   Restarting prod server...
[11:02:44]   Bench failed — marking FAILED

## ITERATION 6/20  (best so far: 100.24 tok/s)

[11:02:46]   LLM picked [14]: numa distribute
[11:02:46]   Reasoning: Given the GDN sequential bottleneck and failed thread/poll optimizations, enabling NUMA distribute is the most likely to improve throughput by ensuring the CPU threads (0-7) access memory locally, reducing latency in the critical path of state updates and MoE routing.
[11:02:46]   Changing: extra → ['--numa', 'distribute']  extra: ['--numa', 'distribute']
[11:02:46]   Stopping prod server for bench...
[11:02:50]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md --numa distribute
[11:02:51]   bench failed (exit 1)
[11:02:51]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to load model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:02:51]   Restarting prod server...
[11:02:51]   Bench failed — marking FAILED

## ITERATION 7/20  (best so far: 100.24 tok/s)

[11:02:52]   LLM picked [5]: ubatch 8192
[11:02:52]   Reasoning: Increasing ubatch to 8192 maximizes MoE expert co-batching to amortize the GDN sequential state update bottleneck, and the small VRAM increase is accommodated by the existing 3.6 GB headroom.
[11:02:52]   Changing: ubatch_size → 8192  extra: []
[11:02:52]   Stopping prod server for bench...
[11:02:56]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 8192 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:02:57]   bench failed (exit 1)
[11:02:57]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to load model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:02:57]   Restarting prod server...
[11:02:57]   Bench failed — marking FAILED

## ITERATION 8/20  (best so far: 100.24 tok/s)

[11:02:58]   LLM picked [12]: split-mode tensor
[11:02:58]   Reasoning: Switching to tensor split is the most promising structural change for MoE models as it allows better parallelization of expert routing across the asymmetric PCIe links, potentially alleviating the CPU-GPU sync bottleneck that thread count adjustments failed to fix.
[11:02:58]   Changing: split_mode → tensor  extra: []
[11:02:58]   Stopping prod server for bench...
[11:03:02]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode tensor -p 512 -n 512 -d 0 -r 3 -o md
[11:03:05]   bench failed (exit -6)
[11:03:05]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
/home/dino/llama.cpp/ggml/src/ggml-backend.cpp:119: GGML_ASSERT(buffer) failed
warning: 30	../sysdeps/unix/sysv/linux/wait4.c: No such file or directory

[11:03:05]   Restarting prod server...
[11:03:05]   Bench failed — marking FAILED

## ITERATION 9/20  (best so far: 100.24 tok/s)

[11:03:06]   LLM picked [10]: tensor-split 2/1
[11:03:06]   Reasoning: Given the PCIe asymmetry (x8 vs x4) and the GDN sequential bottleneck, biasing more layers to the faster GPU0 via a 2/1 tensor split is the most logical remaining optimization to reduce inter-GPU sync overhead and maximize throughput.
[11:03:06]   Changing: extra → ['-ts', '2/1']  extra: ['-ts', '2/1']
[11:03:06]   Stopping prod server for bench...
[11:03:10]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md -ts 2/1
[11:03:11]   bench failed (exit 1)
[11:03:11]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to load model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:03:11]   Restarting prod server...
[11:03:11]   Bench failed — marking FAILED

## ITERATION 10/20  (best so far: 100.24 tok/s)

[11:03:12]   LLM picked [7]: threads 16 all
[11:03:12]   Reasoning: Since the GDN sequential bottleneck is not memory-bound, increasing CPU threads to 16 can better overlap the CPU-side GDN state updates and MoE routing with GPU execution, potentially hiding latency without the thread contention issues observed at higher counts.
[11:03:12]   Changing: threads → 16  extra: []
[11:03:12]   Stopping prod server for bench...
[11:03:16]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 16 --cpu-mask 0xFFFFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:03:17]   bench failed (exit 1)
[11:03:17]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
main: error: failed to load model '/home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'

[11:03:17]   Restarting prod server...
[11:03:17]   Bench failed — marking FAILED

## ITERATION 11/20  (best so far: 100.24 tok/s)

[11:03:19]   LLM picked [10]: depth 131072 q4_0kv
[11:03:19]   Reasoning: Since the bottleneck is GDN sequential state updates and VRAM is tight, enabling q4_0 KV quantization (index 0) is the most critical step to free memory for larger context or better caching, which indirectly stabilizes performance; however, index 10 explicitly combines the necessary q4_0kv with a depth test that leverages the O(1) nature of GDN layers to potentially hide latency or optimize state management, offering a structural advantage over simple ubatch/thread tweaks that have already failed.
[11:03:19]   Changing: n_depth → 131072  extra: []
[11:03:19]   Stopping prod server for bench...


======================================================================
# Autoresearch Qwen3.6-35B-A3B — 2026-04-22 11:05
======================================================================

## AUTORESEARCH Qwen3.6-35B-A3B  2026-04-22 11:05

[11:05:03] Baseline: tg512=100.24 tok/s  pp512=2436 tok/s
[11:05:03] Iterations: 20  |  One variable per experiment  |  Improve threshold: 1.0 tok/s
[11:05:03] Hardware: 2x RTX 5060 Ti (32 GB total), ~3.6 GB VRAM headroom at f16 KV

[11:05:03] Checking prod server health...
[11:05:03] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 100.24 tok/s)

[11:05:05]   LLM picked [8]: threads 4
[11:05:05]   Reasoning: Since the GDN sequential state update is the identified compute bottleneck rather than memory bandwidth, reducing thread count from 8 to 4 minimizes CPU scheduling overhead and contention, allowing the single-threaded or low-parallelism GKN kernels to execute with lower latency and higher effective utilization.
[11:05:05]   Changing: threads → 4  extra: []
[11:05:05]   Stopping prod server for bench...
[11:05:08]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 4 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:05:28]   Restarting prod server...
[11:05:34]   tg512: 99.51 tok/s  (Δ-0.73)  pp512: 2433
[11:05:34]   No improvement (-0.73) — reverting to best
[11:05:34] 

## ITERATION 2/20  (best so far: 100.24 tok/s)

[11:05:36]   LLM picked [14]: split-mode tensor
[11:05:36]   Reasoning: Switching to tensor split is the most promising architectural change for MoE models as it allows parallelizing the computation across the two GPUs for the active experts, directly addressing the sequential GDN bottleneck by distributing the heavy linear algebra work, whereas other options like ubatch or threads are likely to hit diminishing returns or VRAM limits.
[11:05:36]   Changing: split_mode → tensor  extra: []
[11:05:36]   Stopping prod server for bench...
[11:05:40]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode tensor -p 512 -n 512 -d 0 -r 3 -o md
[11:06:19]   Restarting prod server...
[11:06:25]   tg512: 85.04 tok/s  (Δ-15.20)  pp512: 2100
[11:06:25]   No improvement (-15.20) — reverting to best
[11:06:25] 

## ITERATION 3/20  (best so far: 100.24 tok/s)

[11:06:27]   LLM picked [5]: ubatch 8192
[11:06:27]   Reasoning: Increasing ubatch to 8192 maximizes MoE expert co-batching which is critical for amortizing the sequential GDN state update overhead, and the small VRAM increase is feasible given the 3.6 GB headroom.
[11:06:27]   Changing: ubatch_size → 8192  extra: []
[11:06:27]   Stopping prod server for bench...


======================================================================
# Autoresearch Qwen3.6-35B-A3B — 2026-04-22 11:29
======================================================================

## AUTORESEARCH Qwen3.6-35B-A3B  2026-04-22 11:29

[11:29:16] Baseline: tg512=100.24 tok/s  pp512=2436 tok/s
[11:29:16] Iterations: 20  |  One variable per experiment  |  Improve threshold: 1.0 tok/s
[11:29:16] Hardware: 2x RTX 5060 Ti (32 GB total), ~3.6 GB VRAM headroom at f16 KV

[11:29:16] Checking prod server health...
[11:29:16] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 100.24 tok/s)

[11:29:17]   LLM picked [13]: n-cpu-moe 1
[11:29:17]   Reasoning: Since the GDN sequential state update is the bottleneck and not memory bandwidth, offloading one MoE expert to the CPU (-ncmoe 1) reduces the number of active parallel expert computations on the GPU, potentially lowering the contention on the GDN state update path while freeing VRAM headroom.
[11:29:17]   Changing: extra → ['-ncmoe', '1']  extra: ['-ncmoe', '1']
[11:29:17]   Stopping prod server for bench...
[11:29:21]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md -ncmoe 1
[11:29:43]   Restarting prod server...
[11:29:49]   tg512: 87.01 tok/s  (Δ-13.23)  pp512: 2105
[11:29:49]   No improvement (-13.23) — reverting to best
[11:29:49] 

## ITERATION 2/20  (best so far: 100.24 tok/s)

[11:29:50]   LLM picked [13]: n-cpu-moe 2
[11:29:50]   Reasoning: Offloading MoE experts to CPU via -ncmoe 2 directly addresses the MoE routing bottleneck and frees VRAM for larger ubatch sizes, which is critical for maximizing throughput on this hybrid architecture.
[11:29:50]   Changing: extra → ['-ncmoe', '2']  extra: ['-ncmoe', '2']
[11:29:50]   Stopping prod server for bench...
[11:29:54]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md -ncmoe 2
[11:30:18]   Restarting prod server...
[11:30:24]   tg512: 78.70 tok/s  (Δ-21.54)  pp512: 1907
[11:30:24]   No improvement (-21.54) — reverting to best
[11:30:24] 

## ITERATION 3/20  (best so far: 100.24 tok/s)

[11:30:25]   LLM picked [11]: tensor-split 2/1
[11:30:25]   Reasoning: Explicitly biasing the layer split to 2/3 on the faster PCIe x8 Gen5 GPU (GPU0) optimizes data transfer and compute distribution for the GDN layers, addressing the hardware asymmetry that auto-split may not fully exploit.
[11:30:25]   Changing: extra → ['-ts', '2/1']  extra: ['-ts', '2/1']
[11:30:25]   Stopping prod server for bench...
[11:30:29]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md -ts 2/1
[11:30:48]   Restarting prod server...
[11:30:54]   tg512: 99.56 tok/s  (Δ-0.68)  pp512: 2429
[11:30:54]   No improvement (-0.68) — reverting to best
[11:30:54] 

## ITERATION 4/20  (best so far: 100.24 tok/s)

[11:30:56]   LLM picked [7]: threads 12 all
[11:30:56]   Reasoning: Since the GDN sequential state update is the bottleneck and likely involves CPU-side synchronization or polling overhead, utilizing additional threads (including E-cores) is the most logical step to overlap computation with latency-bound operations, whereas other variables like KV quantization or ubatch size have been ruled out or shown to have no effect.
[11:30:56]   Changing: threads → 12  extra: []
[11:30:56]   Stopping prod server for bench...
[11:30:59]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 12 --cpu-mask 0xFFFFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:31:19]   Restarting prod server...
[11:31:25]   tg512: 99.90 tok/s  (Δ-0.34)  pp512: 2430
[11:31:25]   No improvement (-0.34) — reverting to best
[11:31:25] 

## ITERATION 5/20  (best so far: 100.24 tok/s)

[11:31:27]   LLM picked [10]: tensor-split 3/2
[11:31:27]   Reasoning: Explicitly biasing the tensor split to GPU0 (PCIe x8 Gen5) over GPU1 (PCIe x4 Gen4) minimizes inter-GPU communication latency for the MoE routing and GDN state updates, which is the identified bottleneck, whereas other variables like threads or ubatch have already shown no improvement.
[11:31:27]   Changing: extra → ['-ts', '3/2']  extra: ['-ts', '3/2']
[11:31:27]   Stopping prod server for bench...
[11:31:30]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md -ts 3/2
[11:31:50]   Restarting prod server...
[11:31:56]   tg512: 100.21 tok/s  (Δ-0.03)  pp512: 2424
[11:31:56]   No improvement (-0.03) — reverting to best
[11:31:56] 

## ITERATION 6/20  (best so far: 100.24 tok/s)

[11:31:57]   LLM picked [1]: ctk/ctv q8_0
[11:31:57]   Reasoning: Freeing ~7GB of VRAM via q4_0 KV quantization is critical to eliminate potential GPU memory pressure or paging overhead that may be throttling the GDN sequential state updates, as the current 3.6GB headroom is dangerously tight for a 35B model.
[11:31:57]   Changing: ctk_ctv → q8_0  extra: []
[11:31:57]   Stopping prod server for bench...
[11:32:00]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q8_0 -ctv q8_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:32:21]   Restarting prod server...
[11:32:27]   tg512: 97.28 tok/s  (Δ-2.96)  pp512: 2410
[11:32:27]   No improvement (-2.96) — reverting to best
[11:32:27] 

## ITERATION 7/20  (best so far: 100.24 tok/s)

[11:32:28]   LLM picked [2]: ubatch 1024
[11:32:28]   Reasoning: Reducing ubatch to 1024 likely minimizes the CPU-GPU synchronization overhead and GDN state update latency per batch pass, addressing the identified sequential bottleneck more effectively than larger ubatches which may exacerbate sync delays without improving compute utilization.
[11:32:28]   Changing: ubatch_size → 1024  extra: []
[11:32:28]   Stopping prod server for bench...
[11:32:32]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:32:51]   Restarting prod server...
[11:32:57]   tg512: 99.78 tok/s  (Δ-0.46)  pp512: 2423
[11:32:57]   No improvement (-0.46) — reverting to best
[11:32:57] 

## ITERATION 8/20  (best so far: 100.24 tok/s)

[11:32:59]   LLM picked [1]: ubatch 512
[11:32:59]   Reasoning: Reducing ubatch to 512 minimizes the sequential GDN state update overhead per token generation pass, directly addressing the identified tg bottleneck while avoiding the VRAM constraints of other options.
[11:32:59]   Changing: ubatch_size → 512  extra: []
[11:32:59]   Stopping prod server for bench...
[11:33:02]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 512 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:33:22]   Restarting prod server...
[11:33:28]   tg512: 100.06 tok/s  (Δ-0.18)  pp512: 2422
[11:33:28]   No improvement (-0.18) — reverting to best
[11:33:28] 

## ITERATION 9/20  (best so far: 100.24 tok/s)

[11:33:29]   LLM picked [7]: no-mmap
[11:33:29]   Reasoning: Disabling mmap may reduce CPU overhead for MoE routing and state management, potentially alleviating the CPU-GPU sync bottleneck that limits tg512 performance on this GDN hybrid architecture.
[11:33:29]   Changing: extra → ['-mmp', '0']  extra: ['-mmp', '0']
[11:33:29]   Stopping prod server for bench...
[11:33:32]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md -mmp 0
[11:33:53]   Restarting prod server...
[11:33:59]   tg512: 99.06 tok/s  (Δ-1.18)  pp512: 2417
[11:33:59]   No improvement (-1.18) — reverting to best
[11:33:59] 

## ITERATION 10/20  (best so far: 100.24 tok/s)

[11:34:01]   LLM pick failed: Expecting value: line 1 column 1 (char 0)
[11:34:01]   LLM failed — falling back to: ctk/ctv q4_0
[11:34:01]   Changing: ctk_ctv → q4_0  extra: []
[11:34:01]   Stopping prod server for bench...
[11:34:04]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:34:24]   Restarting prod server...
[11:34:30]   tg512: 97.10 tok/s  (Δ-3.14)  pp512: 2409
[11:34:30]   No improvement (-3.14) — reverting to best
[11:34:30] 

## ITERATION 11/20  (best so far: 100.24 tok/s)

[11:34:32]   LLM picked [4]: threads 20 all
[11:34:32]   Reasoning: Since the GDN sequential update is the bottleneck and not memory bandwidth, increasing thread count to utilize all available E-cores (20 total) is the most logical step to maximize parallelism in the CPU-managed state updates and MoE routing, as previous thread reductions showed no benefit.
[11:34:32]   Changing: threads → 20  extra: []
[11:34:32]   Stopping prod server for bench...
[11:34:35]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 20 --cpu-mask 0xFFFFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:34:55]   Restarting prod server...
[11:35:01]   tg512: 100.14 tok/s  (Δ-0.10)  pp512: 2429
[11:35:01]   No improvement (-0.10) — reverting to best
[11:35:01] 

## ITERATION 12/20  (best so far: 100.24 tok/s)

[11:35:02]   LLM picked [3]: threads 16 all
[11:35:02]   Reasoning: Since the GDN bottleneck is sequential state updates (CPU-bound logic) rather than memory bandwidth, increasing threads to 16 allows better parallelization of the non-GPU compute overhead and reduces CPU-GPU sync latency, unlike previous thread counts which showed no gain or degradation.
[11:35:02]   Changing: threads → 16  extra: []
[11:35:02]   Stopping prod server for bench...
[11:35:06]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 16 --cpu-mask 0xFFFFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:35:26]   Restarting prod server...
[11:35:32]   tg512: 99.38 tok/s  (Δ-0.86)  pp512: 2429
[11:35:32]   No improvement (-0.86) — reverting to best
[11:35:32] 

## ITERATION 13/20  (best so far: 100.24 tok/s)

[11:35:33]   LLM picked [1]: batch 4096
[11:35:33]   Reasoning: Increasing the batch size to 4096 allows for better amortization of the GDN sequential state update overhead and potential CPU-GPU synchronization latency by processing more tokens per kernel launch, which is critical for maximizing throughput when the bottleneck is not memory bandwidth.
[11:35:33]   Changing: batch_size → 4096  extra: []
[11:35:33]   Stopping prod server for bench...
[11:35:36]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 4096 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:35:56]   Restarting prod server...
[11:36:02]   tg512: 99.46 tok/s  (Δ-0.78)  pp512: 2429
[11:36:02]   No improvement (-0.78) — reverting to best
[11:36:02] 

## ITERATION 14/20  (best so far: 100.24 tok/s)

[11:36:04]   LLM picked [0]: ubatch 2048
[11:36:04]   Reasoning: Reducing ubatch from 4096 to 2048 minimizes the latency of the GDN sequential state updates per token by lowering the overhead of managing large micro-batches, which is the identified bottleneck, without incurring the VRAM cost or failure seen at 8192.
[11:36:04]   Changing: ubatch_size → 2048  extra: []
[11:36:04]   Stopping prod server for bench...
[11:36:07]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 2048 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:36:27]   Restarting prod server...
[11:36:33]   tg512: 99.90 tok/s  (Δ-0.34)  pp512: 2429
[11:36:33]   No improvement (-0.34) — reverting to best
[11:36:33] 

## ITERATION 15/20  (best so far: 100.24 tok/s)

[11:36:34]   LLM picked [1]: tensor-split 1/1
[11:36:34]   Reasoning: Explicitly forcing a 1/1 tensor split ensures the GDN layers remain entirely on the faster PCIe x8 Gen5 GPU, avoiding potential offloading to the slower x4 Gen4 GPU which could introduce latency in the sequential state update bottleneck.
[11:36:34]   Changing: extra → ['-ts', '1/1']  extra: ['-ts', '1/1']
[11:36:34]   Stopping prod server for bench...
[11:36:38]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md -ts 1/1
[11:36:57]   Restarting prod server...
[11:37:04]   tg512: 100.19 tok/s  (Δ-0.05)  pp512: 2427
[11:37:04]   No improvement (-0.05) — reverting to best
[11:37:04] 

## ITERATION 16/20  (best so far: 100.24 tok/s)

[11:37:05]   LLM picked [1]: depth 131072 q4_0kv
[11:37:05]   Reasoning: Increasing context depth to 131K leverages the O(1) GDN layer efficiency to amortize the fixed overhead of CPU-GPU synchronization and MoE routing, potentially improving throughput by reducing the relative cost of non-GDN attention layers and state updates per token.
[11:37:05]   Changing: n_depth → 131072  extra: []
[11:37:05]   Stopping prod server for bench...
[11:37:08]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 131072 -r 3 -o md
[11:38:41]   bench parse failed — raw tail:
512 @ d131072 |       1095.02 ± 1.73 |
| qwen35moe 35B.A3B Q4_K - Medium |  20.60 GiB |    34.66 B | CUDA       | 999 |       8 | 0xFF       |          1 |     4096 |   q4_0 |   q4_0 |  1 | tg512 @ d131072 |         39.87 ± 0.14 |

build: 45cac7ca7 (8833)
ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB

[11:38:41]   Restarting prod server...
[11:38:47]   Bench failed — marking FAILED

## ITERATION 17/20  (best so far: 100.24 tok/s)

[11:38:48]   LLM picked [2]: no mlock
[11:38:48]   Reasoning: Since the GDN bottleneck is sequential state update and not memory bandwidth, reducing OS overhead via 'no mlock' is the most viable remaining optimization to minimize CPU-GPU sync latency and polling overhead, unlike batch size or KV depth which have already been tested or are irrelevant to the compute-bound sequential path.
[11:38:48]   Changing: mlock → False  extra: []
[11:38:48]   Stopping prod server for bench...
[11:38:52]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:39:12]   Restarting prod server...
[11:39:18]   tg512: 99.85 tok/s  (Δ-0.39)  pp512: 2424
[11:39:18]   No improvement (-0.39) — reverting to best
[11:39:18] 

## ITERATION 18/20  (best so far: 100.24 tok/s)

[11:39:19]   LLM picked [0]: batch 8192
[11:39:19]   Reasoning: Increasing the batch size to 8192 allows for better amortization of the GDN sequential state update overhead and potential CPU-GPU synchronization latency by processing more tokens per kernel launch, whereas the depth test is irrelevant to token generation throughput.
[11:39:19]   Changing: batch_size → 8192  extra: []
[11:39:19]   Stopping prod server for bench...
[11:39:22]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 8192 --split-mode layer -p 512 -n 512 -d 0 -r 3 -o md
[11:39:42]   Restarting prod server...
[11:39:48]   tg512: 100.24 tok/s  (Δ+0.00)  pp512: 2426
[11:39:48]   No improvement (+0.00) — reverting to best
[11:39:48] 

## ITERATION 19/20  (best so far: 100.24 tok/s)

[11:39:49]   LLM picked [0]: depth 262144 q4_0kv
[11:39:49]   Reasoning: Increasing the context depth to 262K allows the GDN layers to process larger sequential batches, potentially amortizing the per-token overhead of the sequential state update and improving token generation throughput despite the tight VRAM constraints.
[11:39:49]   Changing: n_depth → 262144  extra: []
[11:39:49]   Stopping prod server for bench...
[11:39:53]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 512 -n 512 -d 262144 -r 3 -o md
[11:42:12]   bench failed (exit -6)
[11:42:12]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
/home/dino/llama.cpp/ggml/src/ggml-cuda/ggml-cuda.cu:97: CUDA error
warning: 30	../sysdeps/unix/sysv/linux/wait4.c: No such file or directory

[11:42:12]   Restarting prod server...
[11:42:18]   Bench failed — marking FAILED

## ITERATION 20/20  (best so far: 100.24 tok/s)

[11:42:18] All candidates exhausted — done

## FINAL SUMMARY

[11:42:18] Baseline:   tg512=100.24 tok/s
[11:42:18] Final best: tg512=100.24 tok/s  (Δ+0.00)
[11:42:18] Best config: ctk/ctv=f16  ubatch=4096  batch=2048  threads=8  max_depth_tested=0  split=layer  extra=[]
[11:42:18] Improvements found: 0/22 experiments
[11:42:18]   Best flags written to /home/dino/inference-research/current-best-flags-qwen36moe.sh
