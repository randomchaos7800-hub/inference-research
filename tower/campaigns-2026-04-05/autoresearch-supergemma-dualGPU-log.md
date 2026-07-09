

======================================================================
# Autoresearch supergemma4-26b dual-GPU — 2026-04-20 21:48
======================================================================

## AUTORESEARCH supergemma4-26b dual-GPU  2026-04-20 21:48

[21:48:32] Baseline: tg512=99.2 tok/s  pp2048=4502 tok/s
[21:48:32] Iterations: 20  |  One variable per experiment  |  Improve threshold: 0.8 tok/s
[21:48:32] Hardware: 2x RTX 5060 Ti (32 GB total), ~12 GB VRAM headroom

[21:48:32] Checking prod server health...
[21:48:32] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 99.20 tok/s)

[21:48:33]   LLM picked [2]: ctk/ctv iq4_nl
[21:48:33]   Reasoning: iq4_nl provides a more efficient KV cache quantization than q4_0, potentially increasing throughput by reducing memory bandwidth pressure without sacrificing significant quality.
[21:48:33]   Changing: ctk_ctv → iq4_nl  extra: []
[21:48:33]   Stopping prod server for bench...
[21:48:38]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk iq4_nl -ctv iq4_nl --threads 8 --threads-batch 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 512,2048,8192 -n 128,512 -r 3 -o md --mlock
[21:48:39]   bench failed (exit 1)
[21:48:39]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
error: invalid parameter for argument: --threads-batch

[21:48:39]   Restarting prod server...
[21:48:45]   Bench failed — marking FAILED

## ITERATION 2/20  (best so far: 99.20 tok/s)

[21:48:46]   LLM picked [12]: split-mode row
[21:48:46]   Reasoning: Switching from layer-wise split to row-wise split can significantly improve throughput in dual-GPU setups by better balancing the compute load across the PCIe bus during the generation phase.
[21:48:46]   Changing: split_mode → row  extra: []
[21:48:46]   Stopping prod server for bench...
[21:48:51]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --threads-batch 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode row -p 512,2048,8192 -n 128,512 -r 3 -o md --mlock
[21:48:51]   bench failed (exit 1)
[21:48:51]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
error: invalid parameter for argument: --threads-batch

[21:48:51]   Restarting prod server...


======================================================================
# Autoresearch supergemma4-26b dual-GPU — 2026-04-20 21:49
======================================================================

## AUTORESEARCH supergemma4-26b dual-GPU  2026-04-20 21:49

[21:49:10] Baseline: tg512=99.2 tok/s  pp2048=4502 tok/s
[21:49:10] Iterations: 20  |  One variable per experiment  |  Improve threshold: 0.8 tok/s
[21:49:10] Hardware: 2x RTX 5060 Ti (32 GB total), ~12 GB VRAM headroom

[21:49:10] Checking prod server health...
[21:49:10] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 99.20 tok/s)

[21:49:12]   LLM picked [2]: ctk/ctv iq4_nl
[21:49:12]   Reasoning: iq4_nl provides a more efficient KV cache quantization than q4_0, potentially increasing throughput by reducing memory bandwidth pressure without sacrificing significant quality.
[21:49:12]   Changing: ctk_ctv → iq4_nl  extra: []
[21:49:12]   Stopping prod server for bench...
[21:49:16]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk iq4_nl -ctv iq4_nl --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 512,2048,8192 -n 128,512 -r 3 -o md --mlock
[21:49:16]   bench failed (exit 1)
[21:49:16]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
error: invalid parameter for argument: --mlock

[21:49:16]   Restarting prod server...


======================================================================
# Autoresearch supergemma4-26b dual-GPU — 2026-04-20 21:50
======================================================================

## AUTORESEARCH supergemma4-26b dual-GPU  2026-04-20 21:50

[21:50:02] Baseline: tg512=99.2 tok/s  pp2048=4502 tok/s
[21:50:02] Iterations: 20  |  One variable per experiment  |  Improve threshold: 0.8 tok/s
[21:50:02] Hardware: 2x RTX 5060 Ti (32 GB total), ~12 GB VRAM headroom

[21:50:02] Checking prod server health...
[21:50:02] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 99.20 tok/s)

[21:50:03]   LLM picked [2]: ctk/ctv iq4_nl
[21:50:03]   Reasoning: iq4_nl provides a more efficient quantization for the KV cache than q4_0, potentially increasing throughput while maintaining similar memory footprint.
[21:50:03]   Changing: ctk_ctv → iq4_nl  extra: []
[21:50:03]   Stopping prod server for bench...
[21:50:07]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk iq4_nl -ctv iq4_nl --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 512,2048,8192 -n 128,512 -r 3 -o md
[22:00:08]   bench timed out
[22:00:08]   Restarting prod server...
[22:00:14]   Bench failed — marking FAILED

## ITERATION 2/20  (best so far: 99.20 tok/s)

[22:00:16]   LLM picked [19]: tensor-split 2/1
[22:00:16]   Reasoning: Since the current split-mode is layer-wise, adjusting the tensor-split to favor the x8 PCIe slot (GPU 0) will optimize the data transfer bottleneck inherent in asymmetric dual-GPU setups.
[22:00:16]   Changing: extra → ['-ts', '2/1']  extra: ['-ts', '2/1']
[22:00:16]   Stopping prod server for bench...


======================================================================
# Autoresearch supergemma4-26b dual-GPU — 2026-04-20 22:08
======================================================================

## AUTORESEARCH supergemma4-26b dual-GPU  2026-04-20 22:08

[22:08:12] Baseline: tg512=99.2 tok/s  pp2048=4502 tok/s
[22:08:12] Iterations: 20  |  One variable per experiment  |  Improve threshold: 0.8 tok/s
[22:08:12] Hardware: 2x RTX 5060 Ti (32 GB total), ~12 GB VRAM headroom

[22:08:12] Checking prod server health...
[22:08:12] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 99.20 tok/s)

[22:08:13]   LLM picked [13]: split-mode row
[22:08:13]   Reasoning: Switching from layer-wise split to row-wise split can significantly improve throughput by better distributing the workload across the dual-GPU communication fabric.
[22:08:13]   Changing: split_mode → row  extra: []
[22:08:13]   Stopping prod server for bench...
[22:08:18]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode row -p 512,2048,8192 -n 128,512 -r 3 -o md
[22:08:22]   bench failed (exit -6)
[22:08:22]   stderr: ggml_cuda_init: found 2 CUDA devices (Total VRAM: 31673 MiB):
  Device 0: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15825 MiB
  Device 1: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0, VMM: yes, VRAM: 15847 MiB
/home/dino/llama.cpp/ggml/src/ggml-cuda/ggml-cuda.cu:905: GGML_ASSERT(tensor->view_src == nullptr) failed
warning: 30	../sysdeps/unix/sysv/linux/wait4.c: No such file or directory

[22:08:22]   Restarting prod server...
[22:08:28]   Bench failed — marking FAILED

## ITERATION 2/20  (best so far: 99.20 tok/s)

[22:08:30]   LLM picked [13]: split-mode tensor
[22:08:30]   Reasoning: Since 'split-mode row' failed to improve performance, 'tensor' split mode is the logical next step to test if intra-layer parallelism provides better throughput on a dual-GPU setup.
[22:08:30]   Changing: split_mode → tensor  extra: []
[22:08:30]   Stopping prod server for bench...


======================================================================
# Autoresearch supergemma4-26b dual-GPU — 2026-04-20 22:08
======================================================================

## AUTORESEARCH supergemma4-26b dual-GPU  2026-04-20 22:08

[22:08:48] Baseline: tg512=99.2 tok/s  pp2048=4502 tok/s
[22:08:48] Iterations: 20  |  One variable per experiment  |  Improve threshold: 0.8 tok/s
[22:08:48] Hardware: 2x RTX 5060 Ti (32 GB total), ~12 GB VRAM headroom

[22:08:48] Checking prod server health...
[22:08:48] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 99.20 tok/s)

[22:08:49]   LLM picked [1]: ctk/ctv q5_0
[22:08:49]   Reasoning: Increasing KV cache precision to q5_0 provides a better balance of memory bandwidth efficiency and cache hit quality than q4_0 without the heavy overhead of f16.
[22:08:49]   Changing: ctk_ctv → q5_0  extra: []
[22:08:49]   Stopping prod server for bench...
[22:08:53]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q5_0 -ctv q5_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 512,2048,8192 -n 128,512 -r 3 -o md
[22:18:54]   bench timed out
[22:18:54]   Restarting prod server...
[22:19:07]   Bench failed — marking FAILED

## ITERATION 2/20  (best so far: 99.20 tok/s)

[22:19:09]   LLM picked [1]: ctk/ctv iq4_nl
[22:19:09]   Reasoning: iq4_nl provides a more efficient quantization-aware KV cache than q4_0, potentially increasing throughput by reducing memory bandwidth pressure while maintaining similar memory footprint.
[22:19:09]   Changing: ctk_ctv → iq4_nl  extra: []
[22:19:09]   Stopping prod server for bench...
[22:19:13]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk iq4_nl -ctv iq4_nl --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 512,2048,8192 -n 128,512 -r 3 -o md


======================================================================
# Autoresearch supergemma4-26b dual-GPU — 2026-04-20 22:20
======================================================================

## AUTORESEARCH supergemma4-26b dual-GPU  2026-04-20 22:20

[22:20:05] Baseline: tg512=99.2 tok/s  pp2048=4502 tok/s
[22:20:05] Iterations: 20  |  One variable per experiment  |  Improve threshold: 0.8 tok/s
[22:20:05] Hardware: 2x RTX 5060 Ti (32 GB total), ~12 GB VRAM headroom

[22:20:05] Checking prod server health...
[22:20:05] Prod server healthy. Starting research loop.


## ITERATION 1/20  (best so far: 99.20 tok/s)

[22:20:07]   LLM picked [2]: ctk/ctv iq4_nl
[22:20:07]   Reasoning: Switching to iq4_nl provides a higher-quality KV cache than q4_0 without increasing VRAM usage, allowing us to test if the improved precision improves generation throughput via better cache hits.
[22:20:07]   Changing: ctk_ctv → iq4_nl  extra: []
[22:20:07]   Stopping prod server for bench...
[22:20:11]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk iq4_nl -ctv iq4_nl --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:23:13]   Restarting prod server...
[22:23:19]   tg512: 25.62 tok/s  (Δ-73.58)  tg128: 0.00  pp2048: 70
[22:23:19]   No improvement (-73.58) — reverting to best
[22:23:19] 

## ITERATION 2/20  (best so far: 99.20 tok/s)

[22:23:20]   LLM picked [1]: ctk/ctv q5_0
[22:23:20]   Reasoning: Since q4_0 caused a significant performance drop, testing q5_0 will determine if a slightly higher precision KV cache provides a better balance between compute-bound efficiency and memory bandwidth overhead.
[22:23:20]   Changing: ctk_ctv → q5_0  extra: []
[22:23:20]   Stopping prod server for bench...
[22:23:25]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q5_0 -ctv q5_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:25:49]   Restarting prod server...
[22:25:55]   tg512: 26.64 tok/s  (Δ-72.56)  tg128: 0.00  pp2048: 100
[22:25:55]   No improvement (-72.56) — reverting to best
[22:25:55] 

## ITERATION 3/20  (best so far: 99.20 tok/s)

[22:25:56]   LLM picked [2]: ubatch 512
[22:25:56]   Reasoning: Since q4_0 KV cache caused a significant drop in generation speed, reducing ubatch to 512 will decrease the memory bandwidth pressure per step, potentially recovering throughput lost to cache quantization overhead.
[22:25:56]   Changing: ubatch_size → 512  extra: []
[22:25:56]   Stopping prod server for bench...
[22:26:01]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 512 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:26:22]   Restarting prod server...
[22:26:28]   tg512: 97.37 tok/s  (Δ-1.83)  tg128: 0.00  pp2048: 4393
[22:26:28]   No improvement (-1.83) — reverting to best
[22:26:28] 

## ITERATION 4/20  (best so far: 99.20 tok/s)

[22:26:29]   LLM picked [15]: tensor-split 2/1
[22:26:29]   Reasoning: Adjusting the tensor-split ratio to favor the x8 PCIe lane (GPU 0) can optimize the data transfer bottleneck inherent in asymmetric dual-GPU setups.
[22:26:29]   Changing: extra → ['-ts', '2/1']  extra: ['-ts', '2/1']
[22:26:29]   Stopping prod server for bench...
[22:26:33]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q4_0 -ctv q4_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md -ts 2/1
[22:26:54]   Restarting prod server...
[22:27:00]   tg512: 98.31 tok/s  (Δ-0.89)  tg128: 0.00  pp2048: 4072
[22:27:00]   No improvement (-0.89) — reverting to best
[22:27:00] 

## ITERATION 5/20  (best so far: 99.20 tok/s)

[22:27:01]   LLM picked [1]: ctk/ctv f16
[22:27:01]   Reasoning: Since q4_0 KV cache is already performing well, testing f16 will determine if the current quantization overhead is the bottleneck for generation speed given the ample 12GB VRAM headroom.
[22:27:01]   Changing: ctk_ctv → f16  extra: []
[22:27:01]   Stopping prod server for bench...
[22:27:06]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 1024 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:27:25]   Restarting prod server...
[22:27:31]   tg512: 106.37 tok/s  (Δ+7.17)  tg128: 0.00  pp2048: 4594
[22:27:31]   NEW BEST: 106.37 tok/s  (+7.17 from previous best)
[22:27:31]   Best flags written to /home/dino/inference-research/current-best-flags-supergemma-dualGPU.sh
[22:27:31] 

## ITERATION 6/20  (best so far: 106.37 tok/s)

[22:27:32]   LLM picked [1]: ubatch 2048
[22:27:32]   Reasoning: Increasing ubatch to 2048 will better saturate the GPU compute cores during the generation phase, given that the current 1024 is likely under-utilizing the available parallelism.
[22:27:32]   Changing: ubatch_size → 2048  extra: []
[22:27:32]   Stopping prod server for bench...
[22:27:37]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 2048 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:27:57]   Restarting prod server...
[22:28:03]   tg512: 106.76 tok/s  (Δ+0.39)  tg128: 0.00  pp2048: 3737
[22:28:03]   No improvement (+0.39) — reverting to best
[22:28:03] 

## ITERATION 7/20  (best so far: 106.37 tok/s)

[22:28:04]   LLM picked [1]: ubatch 4096
[22:28:04]   Reasoning: Increasing ubatch to 4096 will better saturate the GPU compute during the generation phase by increasing the parallelism of the kernel launches.
[22:28:04]   Changing: ubatch_size → 4096  extra: []
[22:28:04]   Stopping prod server for bench...
[22:28:08]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:28:28]   Restarting prod server...
[22:28:34]   tg512: 107.23 tok/s  (Δ+0.86)  tg128: 0.00  pp2048: 3745
[22:28:34]   NEW BEST: 107.23 tok/s  (+0.86 from previous best)
[22:28:34]   Best flags written to /home/dino/inference-research/current-best-flags-supergemma-dualGPU.sh
[22:28:34] 

## ITERATION 8/20  (best so far: 107.23 tok/s)

[22:28:35]   LLM picked [1]: batch 4096
[22:28:35]   Reasoning: Increasing the batch size to 4096 (matching ubatch) will maximize GPU utilization during the prompt processing phase, as the current 2048 is likely underutilizing the available compute bandwidth.
[22:28:35]   Changing: batch_size → 4096  extra: []
[22:28:35]   Stopping prod server for bench...
[22:28:39]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 4096 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:28:59]   Restarting prod server...
[22:29:05]   tg512: 106.54 tok/s  (Δ-0.69)  tg128: 0.00  pp2048: 3743
[22:29:05]   No improvement (-0.69) — reverting to best
[22:29:05] 

## ITERATION 9/20  (best so far: 107.23 tok/s)

[22:29:06]   LLM picked [9]: numa distribute
[22:29:06]   Reasoning: With dual-GPU setups on modern architectures, NUMA-aware memory distribution can significantly reduce latency in CPU-to-GPU communication and memory-bound generation tasks.
[22:29:06]   Changing: extra → ['--numa', 'distribute']  extra: ['--numa', 'distribute']
[22:29:06]   Stopping prod server for bench...
[22:29:11]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md --numa distribute
[22:29:30]   Restarting prod server...
[22:29:37]   tg512: 107.00 tok/s  (Δ-0.23)  tg128: 0.00  pp2048: 3745
[22:29:37]   No improvement (-0.23) — reverting to best
[22:29:37] 

## ITERATION 10/20  (best so far: 107.23 tok/s)

[22:29:38]   LLM picked [10]: tensor-split 3/2
[22:29:38]   Reasoning: Adjusting the tensor-split ratio to 3/2 can optimize workload distribution across asymmetric PCIe lanes or GPU memory bandwidths to improve generation throughput.
[22:29:38]   Changing: extra → ['-ts', '3/2']  extra: ['-ts', '3/2']
[22:29:38]   Stopping prod server for bench...
[22:29:42]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md -ts 3/2
[22:30:02]   Restarting prod server...
[22:30:08]   tg512: 106.93 tok/s  (Δ-0.30)  tg128: 0.00  pp2048: 3736
[22:30:08]   No improvement (-0.30) — reverting to best
[22:30:08] 

## ITERATION 11/20  (best so far: 107.23 tok/s)

[22:30:09]   LLM picked [2]: threads 4
[22:30:09]   Reasoning: Reducing threads to 4 minimizes context switching and synchronization overhead for the single-stream generation task, which is often more efficient than over-subscribing cores when the GPU is the primary bottleneck.
[22:30:09]   Changing: threads → 4  extra: []
[22:30:09]   Stopping prod server for bench...
[22:30:13]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 4 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:30:33]   Restarting prod server...
[22:30:39]   tg512: 106.62 tok/s  (Δ-0.61)  tg128: 0.00  pp2048: 3751
[22:30:39]   No improvement (-0.61) — reverting to best
[22:30:39] 

## ITERATION 12/20  (best so far: 107.23 tok/s)

[22:30:40]   LLM picked [7]: poll 100
[22:30:40]   Reasoning: Increasing polling frequency can reduce the latency between the GPU finishing a kernel and the CPU scheduling the next task, which is critical for maximizing generation throughput in dual-GPU setups.
[22:30:40]   Changing: extra → ['--poll', '100']  extra: ['--poll', '100']
[22:30:40]   Stopping prod server for bench...
[22:30:44]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md --poll 100
[22:31:04]   Restarting prod server...
[22:31:10]   tg512: 107.04 tok/s  (Δ-0.19)  tg128: 0.00  pp2048: 3743
[22:31:10]   No improvement (-0.19) — reverting to best
[22:31:10] 

## ITERATION 13/20  (best so far: 107.23 tok/s)

[22:31:11]   LLM picked [1]: batch 8192
[22:31:11]   Reasoning: Increasing the batch size to 8192 will maximize the throughput of the prompt processing phase and potentially improve the efficiency of the compute-bound generation phase by saturating the GPU kernels.
[22:31:11]   Changing: batch_size → 8192  extra: []
[22:31:11]   Stopping prod server for bench...
[22:31:16]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 8192 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:31:36]   Restarting prod server...
[22:31:42]   tg512: 106.39 tok/s  (Δ-0.84)  tg128: 0.00  pp2048: 3748
[22:31:42]   No improvement (-0.84) — reverting to best
[22:31:42] 

## ITERATION 14/20  (best so far: 107.23 tok/s)

[22:31:43]   LLM picked [1]: threads 12 all-core
[22:31:43]   Reasoning: Increasing threads to 12 leverages more physical cores to reduce CPU-side overhead in the generation phase without the diminishing returns of hyperthreading seen in higher thread counts.
[22:31:43]   Changing: threads → 12  extra: []
[22:31:43]   Stopping prod server for bench...
[22:31:47]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 12 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:32:07]   Restarting prod server...
[22:32:13]   tg512: 106.32 tok/s  (Δ-0.91)  tg128: 0.00  pp2048: 3665
[22:32:13]   No improvement (-0.91) — reverting to best
[22:32:13] 

## ITERATION 15/20  (best so far: 107.23 tok/s)

[22:32:14]   LLM picked [4]: poll 0
[22:32:14]   Reasoning: Since the current best is 107.23 tok/s, reducing polling overhead via '--poll 0' is the most likely way to reduce latency in the generation phase compared to scaling CPU threads which showed diminishing returns.
[22:32:14]   Changing: extra → ['--poll', '0']  extra: ['--poll', '0']
[22:32:14]   Stopping prod server for bench...
[22:32:19]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md --poll 0
[22:32:38]   Restarting prod server...
[22:32:44]   tg512: 107.23 tok/s  (Δ+0.00)  tg128: 0.00  pp2048: 3746
[22:32:44]   No improvement (+0.00) — reverting to best
[22:32:44] 

## ITERATION 16/20  (best so far: 107.23 tok/s)

[22:32:45]   LLM picked [1]: threads 16 all-core
[22:32:45]   Reasoning: Increasing threads to 16 may optimize CPU-side overhead for the generation phase without the diminishing returns or synchronization overhead seen with 20 threads.
[22:32:45]   Changing: threads → 16  extra: []
[22:32:45]   Stopping prod server for bench...
[22:32:50]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 16 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:33:10]   Restarting prod server...
[22:33:16]   tg512: 105.94 tok/s  (Δ-1.29)  tg128: 0.00  pp2048: 3715
[22:33:16]   No improvement (-1.29) — reverting to best
[22:33:16] 

## ITERATION 17/20  (best so far: 107.23 tok/s)

[22:33:16]   LLM picked [2]: no mlock
[22:33:16]   Reasoning: Disabling mlock allows the OS to manage memory pages more dynamically, which can reduce latency in dual-GPU communication and memory access patterns compared to pinning everything.
[22:33:16]   Changing: mlock → False  extra: []
[22:33:16]   Stopping prod server for bench...
[22:33:21]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:33:41]   Restarting prod server...
[22:33:47]   tg512: 106.82 tok/s  (Δ-0.41)  tg128: 0.00  pp2048: 3716
[22:33:47]   No improvement (-0.41) — reverting to best
[22:33:47] 

## ITERATION 18/20  (best so far: 107.23 tok/s)

[22:33:48]   LLM picked [1]: threads 20 all-core
[22:33:48]   Reasoning: Increasing threads to 20 maximizes CPU-bound compute-heavy tasks, which is the logical next step since lower thread counts showed negligible performance loss.
[22:33:48]   Changing: threads → 20  extra: []
[22:33:48]   Stopping prod server for bench...
[22:33:52]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 20 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:34:12]   Restarting prod server...
[22:34:18]   tg512: 107.12 tok/s  (Δ-0.11)  tg128: 0.00  pp2048: 3741
[22:34:18]   No improvement (-0.11) — reverting to best
[22:34:18] 

## ITERATION 19/20  (best so far: 107.23 tok/s)

[22:34:19]   LLM picked [0]: ctk/ctv q8_0
[22:34:19]   Reasoning: Since f16 was improved and lower-precision KV caches (iq4_nl, q5_0) were significantly slower, q8_0 provides a better balance of precision and cache bandwidth to maximize generation speed.
[22:34:19]   Changing: ctk_ctv → q8_0  extra: []
[22:34:19]   Stopping prod server for bench...
[22:34:23]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk q8_0 -ctv q8_0 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md
[22:34:44]   Restarting prod server...
[22:34:50]   tg512: 97.64 tok/s  (Δ-9.59)  tg128: 0.00  pp2048: 3551
[22:34:50]   No improvement (-9.59) — reverting to best
[22:34:50] 

## ITERATION 20/20  (best so far: 107.23 tok/s)

[22:34:51]   LLM picked [0]: no-mmap
[22:34:51]   Reasoning: Disabling mmap can improve performance by ensuring all model weights are resident in physical memory, reducing page fault overhead during generation.
[22:34:51]   Changing: extra → ['--mmap', '0']  extra: ['--mmap', '0']
[22:34:51]   Stopping prod server for bench...
[22:34:56]   bench cmd: /home/dino/llama.cpp/build/bin/llama-bench --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf --n-gpu-layers 999 --flash-attn 1 -ctk f16 -ctv f16 --threads 8 --cpu-mask 0xFF --cpu-strict 1 --ubatch-size 4096 -b 2048 --split-mode layer -p 2048 -n 512 -r 3 -o md --mmap 0
[22:35:16]   Restarting prod server...
[22:35:22]   tg512: 106.75 tok/s  (Δ-0.48)  tg128: 0.00  pp2048: 3723
[22:35:22]   No improvement (-0.48) — reverting to best
[22:35:22] 

## FINAL SUMMARY

[22:35:22] Baseline:   tg512=99.20 tok/s
[22:35:22] Final best: tg512=107.23 tok/s  (Δ+8.03)
[22:35:22] Best config: ctk/ctv=f16  ubatch=4096  batch=2048  threads=8  split=layer  extra=[]
[22:35:22] 
[22:35:22] Improvements found: 2/20 experiments
[22:35:22]   + ctk/ctv f16: Δ+7.17 tok/s
[22:35:22]   + ubatch 4096: Δ+0.86 tok/s
[22:35:22]   Best flags written to /home/dino/inference-research/current-best-flags-supergemma-dualGPU.sh
