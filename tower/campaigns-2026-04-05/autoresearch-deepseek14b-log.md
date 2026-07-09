# DeepSeek-R1-Distill-14B AWQ Autoresearch — 2026-05-17 06:27

**Baseline:** 67.57 t/s  (TP=2, GMU=0.85, ctx=65536, auto KV, seqs=2)
**Genesis reference:** 65.40 t/s (eval-v4, same config)
**Threshold:** ±1.0 t/s for win/loss

## Throughput Sweep

| ID | Label | Median t/s | Delta | Outcome |
|---|---|---|---|---|
| baseline | Baseline (TP=2, GMU=0.85, ctx=65536, auto KV, seqs=2, batch=4096) | 67.57 | +0.00 | NEUTRAL |
| gmu_090 | GMU=0.90 — more KV blocks for the same context | 67.59 | +0.02 | NEUTRAL |
| gmu_092 | GMU=0.92 — max safe VRAM allocation | 67.56 | -0.01 | NEUTRAL |
| single_gpu | TP=1 single GPU — eliminate TP communication overhead (14B AWQ fits in 16GB) | FAIL | — | TIMEOUT |
| fp8_kv | FP8 KV cache — halves KV footprint vs auto/bf16 | 68.16 | +0.59 | NEUTRAL |
| nvfp4_kv | NVFP4 KV cache — native Blackwell FP4, quarter KV footprint | FAIL | — | TIMEOUT |
| seqs4 | seqs=4, batch=8192, GMU=0.90 — higher concurrency headroom | 67.47 | -0.10 | NEUTRAL |

## Cache Size Sweep

| ID | Label | Median t/s | Delta | Outcome |
|---|---|---|---|---|
| ctx_32k | ctx=32768 — shorter window, more KV block slots per VRAM | 67.63 | +0.06 | NEUTRAL |
| ctx_128k | ctx=131072 — full DeepSeek-R1 context (GMU=0.90 for headroom) | FAIL | — | TIMEOUT |
| ctx_128k_fp8 | ctx=131072 + FP8 KV — full context, halved KV footprint | 67.17 | -0.40 | NEUTRAL |
| ctx_128k_nvfp4 | ctx=131072 + NVFP4 KV — full context, native Blackwell quarter-precision KV | FAIL | — | TIMEOUT |

## Recommendation

Baseline config is optimal. No improvement found.

## Log

```
[05:20:33] DeepSeek-R1-Distill-14B AWQ autoresearch  2026-05-17 05:20:33
[05:20:33] Model: /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ
[05:20:33] Experiments: 11  |  Timeout: 600s/exp
[05:20:33] 
============================================================
[05:20:33] EXPERIMENT: baseline
[05:20:33]   Baseline (TP=2, GMU=0.85, ctx=65536, auto KV, seqs=2, batch=4096)
[05:21:39]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:21:39]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[05:21:39]   pid=281722 pgid=281722
[05:22:24]   healthy at 05:22:24
[05:22:24]   VRAM free: [2073, 2795] MiB
[05:22:24]   warmup ×2...
[05:22:32]     warmup 1: 63.69 t/s
[05:22:33]     warmup 2: 65.03 t/s
[05:22:33]   bench ×5...
[05:22:40]     run 1: 67.55 t/s
[05:22:48]     run 2: 67.60 t/s
[05:22:55]     run 3: 67.57 t/s
[05:23:03]     run 4: 67.57 t/s
[05:23:11]     run 5: 67.55 t/s
[05:24:19]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:24:19]   RESULT: 67.57 t/s  (+0.00 vs baseline)  [NEUTRAL]
[05:24:19] 
============================================================
[05:24:19] EXPERIMENT: gmu_090
[05:24:19]   GMU=0.90 — more KV blocks for the same context
[05:25:25]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:25:25]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[05:25:25]   pid=284829 pgid=284829
[05:25:55]   healthy at 05:25:55
[05:25:56]   VRAM free: [713, 1435] MiB
[05:25:56]   warmup ×2...
[05:26:03]     warmup 1: 67.02 t/s
[05:26:04]     warmup 2: 65.15 t/s
[05:26:04]   bench ×5...
[05:26:11]     run 1: 67.58 t/s
[05:26:19]     run 2: 67.61 t/s
[05:26:26]     run 3: 67.59 t/s
[05:26:34]     run 4: 67.59 t/s
[05:26:42]     run 5: 67.61 t/s
[05:27:51]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:27:51]   RESULT: 67.59 t/s  (+0.02 vs baseline)  [NEUTRAL]
[05:27:51] 
============================================================
[05:27:51] EXPERIMENT: gmu_092
[05:27:51]   GMU=0.92 — max safe VRAM allocation
[05:28:57]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:28:57]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[05:28:57]   pid=287583 pgid=287583
[05:29:27]   healthy at 05:29:27
[05:29:27]   VRAM free: [393, 1115] MiB
[05:29:27]   warmup ×2...
[05:29:34]     warmup 1: 67.01 t/s
[05:29:35]     warmup 2: 64.82 t/s
[05:29:35]   bench ×5...
[05:29:43]     run 1: 67.54 t/s
[05:29:50]     run 2: 67.57 t/s
[05:29:58]     run 3: 67.56 t/s
[05:30:05]     run 4: 67.46 t/s
[05:30:13]     run 5: 67.59 t/s
[05:31:22]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:31:22]   RESULT: 67.56 t/s  (-0.01 vs baseline)  [NEUTRAL]
[05:31:22] 
============================================================
[05:31:22] EXPERIMENT: single_gpu
[05:31:22]   TP=1 single GPU — eliminate TP communication overhead (14B AWQ fits in 16GB)
[05:32:28]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:32:28]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 1 --gpu-memory-utilization ...
[05:32:28]   pid=290368 pgid=290368
[05:40:30]   FAIL: never became healthy (timeout or hard-kill)
[05:41:39]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:41:39] 
============================================================
[05:41:39] EXPERIMENT: fp8_kv
[05:41:39]   FP8 KV cache — halves KV footprint vs auto/bf16
[05:42:45]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:42:45]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[05:42:45]   pid=297779 pgid=297779
[05:43:25]   healthy at 05:43:25
[05:43:25]   VRAM free: [2071, 2793] MiB
[05:43:25]   warmup ×2...
[05:43:33]     warmup 1: 65.16 t/s
[05:43:33]     warmup 2: 65.52 t/s
[05:43:33]   bench ×5...
[05:43:41]     run 1: 68.16 t/s
[05:43:48]     run 2: 68.21 t/s
[05:43:56]     run 3: 68.20 t/s
[05:44:05]     run 4: 57.46 t/s
[05:44:12]     run 5: 66.01 t/s
[05:45:21]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:45:21]   RESULT: 68.16 t/s  (+0.59 vs baseline)  [NEUTRAL]
[05:45:21] 
============================================================
[05:45:21] EXPERIMENT: nvfp4_kv
[05:45:21]   NVFP4 KV cache — native Blackwell FP4, quarter KV footprint
[05:46:27]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:46:27]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[05:46:27]   pid=300706 pgid=300706
[05:54:29]   FAIL: never became healthy (timeout or hard-kill)
[05:55:38]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:55:38] 
============================================================
[05:55:38] EXPERIMENT: seqs4
[05:55:38]   seqs=4, batch=8192, GMU=0.90 — higher concurrency headroom
[05:56:44]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:56:44]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[05:56:44]   pid=308181 pgid=308181
[05:57:25]   healthy at 05:57:25
[05:57:25]   VRAM free: [1235, 1957] MiB
[05:57:25]   warmup ×2...
[05:57:33]     warmup 1: 64.24 t/s
[05:57:33]     warmup 2: 64.71 t/s
[05:57:33]   bench ×5...
[05:57:41]     run 1: 67.46 t/s
[05:57:48]     run 2: 67.51 t/s
[05:57:56]     run 3: 67.48 t/s
[05:58:03]     run 4: 67.46 t/s
[05:58:11]     run 5: 67.47 t/s
[05:59:20]   WARNING: GPU not clean after 60s: [15722, 15834]
[05:59:20]   RESULT: 67.47 t/s  (-0.10 vs baseline)  [NEUTRAL]
[05:59:20] 
============================================================
[05:59:20] EXPERIMENT: ctx_32k
[05:59:20]   ctx=32768 — shorter window, more KV block slots per VRAM
[06:00:26]   WARNING: GPU not clean after 60s: [15722, 15834]
[06:00:26]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[06:00:26]   pid=311137 pgid=311137
[06:01:06]   healthy at 06:01:06
[06:01:06]   VRAM free: [2073, 2795] MiB
[06:01:06]   warmup ×2...
[06:01:14]     warmup 1: 64.44 t/s
[06:01:15]     warmup 2: 64.87 t/s
[06:01:15]   bench ×5...
[06:01:22]     run 1: 67.59 t/s
[06:01:30]     run 2: 67.63 t/s
[06:01:38]     run 3: 67.64 t/s
[06:01:45]     run 4: 67.63 t/s
[06:01:53]     run 5: 67.63 t/s
[06:03:02]   WARNING: GPU not clean after 60s: [15722, 15834]
[06:03:02]   RESULT: 67.63 t/s  (+0.06 vs baseline)  [NEUTRAL]
[06:03:02] 
============================================================
[06:03:02] EXPERIMENT: ctx_128k
[06:03:02]   ctx=131072 — full DeepSeek-R1 context (GMU=0.90 for headroom)
[06:04:07]   WARNING: GPU not clean after 60s: [15722, 15834]
[06:04:07]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[06:04:07]   pid=313991 pgid=313991
[06:12:09]   FAIL: never became healthy (timeout or hard-kill)
[06:13:18]   WARNING: GPU not clean after 60s: [15722, 15834]
[06:13:18] 
============================================================
[06:13:18] EXPERIMENT: ctx_128k_fp8
[06:13:18]   ctx=131072 + FP8 KV — full context, halved KV footprint
[06:14:24]   WARNING: GPU not clean after 60s: [15722, 15834]
[06:14:24]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[06:14:24]   pid=321662 pgid=321662
[06:15:04]   healthy at 06:15:04
[06:15:04]   VRAM free: [2071, 2793] MiB
[06:15:04]   warmup ×2...
[06:15:12]     warmup 1: 65.20 t/s
[06:15:13]     warmup 2: 65.48 t/s
[06:15:13]   bench ×5...
[06:15:20]     run 1: 68.15 t/s
[06:15:28]     run 2: 68.20 t/s
[06:15:36]     run 3: 65.78 t/s
[06:15:43]     run 4: 67.17 t/s
[06:15:51]     run 5: 64.88 t/s
[06:17:00]   WARNING: GPU not clean after 60s: [15722, 15834]
[06:17:00]   RESULT: 67.17 t/s  (-0.40 vs baseline)  [NEUTRAL]
[06:17:00] 
============================================================
[06:17:00] EXPERIMENT: ctx_128k_nvfp4
[06:17:00]   ctx=131072 + NVFP4 KV — full context, native Blackwell quarter-precision KV
[06:18:06]   WARNING: GPU not clean after 60s: [15722, 15834]
[06:18:06]   cmd: /opt/ai/vllm-env/bin/vllm serve /home/dino/models/DeepSeek-R1-Distill-Qwen-14B-AWQ --tensor-parallel-size 2 --gpu-memory-utilization ...
[06:18:06]   pid=324550 pgid=324550
[06:26:08]   FAIL: never became healthy (timeout or hard-kill)
[06:27:17]   WARNING: GPU not clean after 60s: [15722, 15834]
```
