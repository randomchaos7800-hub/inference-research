
## autoresearch-vllm-27b pass2 — Karpathy loop

[11:09:53] Pass-1 canonical baseline: {'gpu_memory_utilization': 0.82, 'max_model_len': 32768, 'max_num_seqs': 2, 'max_num_batched_tokens': 4096, 'kv_cache_dtype': 'auto', 'mtp_n': 3, 'NCCL_P2P_DISABLE': '1', 'VLLM_USE_FLASHINFER_SAMPLER': '1', 'OMP_NUM_THREADS': '1', 'CUDA_DEVICE_MAX_CONNECTIONS': '8', 'GENESIS_BUFFER_MODE': 'shared', 'GENESIS_PREALLOC_TOKEN_BUDGET': '4096', 'VLLM_MARLIN_USE_ATOMIC_ADD': '0', 'VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE': '413138944', 'NCCL_BUFFSIZE': '4194304', 'PYTORCH_MAX_SPLIT_MB': '512'}
[11:09:53] Experiments: 12
[11:09:53] Bench: 4 warmup + 5 timed reps × 512 tokens
[11:09:53] Improve threshold: 1.5 t/s

## BASELINE — pass-1 canonical config

[11:10:00]   restarted vllm-genesis
[11:10:30]   still starting... (30s)
[11:10:55]   warming up (4 requests, Marlin kernel JIT)...
[11:10:57]     warmup 1/4: 64.5 t/s
[11:10:59]     warmup 2/4: 70.5 t/s
[11:11:01]     warmup 3/4: 70.4 t/s
[11:11:03]     warmup 4/4: 70.5 t/s
[11:11:03]   measuring (5 requests × 512 tokens)...
[11:11:09]     rep 1/5: 74.1 t/s
[11:11:16]     rep 2/5: 74.4 t/s
[11:11:23]     rep 3/5: 74.4 t/s
[11:11:30]     rep 4/5: 74.3 t/s
[11:11:37]     rep 5/5: 74.3 t/s
[11:11:37] Baseline: 74.35 t/s median, 74.38 t/s p90

## [1/12] Marlin atomic-add

[11:11:37]   atomic-add reduce in gptq_marlin kernel for small-n decode layers (TP=2 eligible)
[11:11:37]   Change: VLLM_MARLIN_USE_ATOMIC_ADD = '1'
[11:13:08]   restarted vllm-genesis
[11:13:38]   still starting... (30s)
[11:14:08]   still starting... (60s)
[11:14:38]   still starting... (90s)
[11:15:08]   still starting... (120s)
[11:15:18]   warming up (4 requests, Marlin kernel JIT)...
[11:15:21]     warmup 1/4: 38.8 t/s
[11:15:23]     warmup 2/4: 69.1 t/s
[11:15:25]     warmup 3/4: 69.0 t/s
[11:15:27]     warmup 4/4: 69.0 t/s
[11:15:27]   measuring (5 requests × 512 tokens)...
[11:15:33]     rep 1/5: 80.6 t/s
[11:15:39]     rep 2/5: 80.6 t/s
[11:15:46]     rep 3/5: 80.6 t/s
[11:15:52]     rep 4/5: 80.6 t/s
[11:15:58]     rep 5/5: 80.6 t/s
[11:15:58]   Result: 80.59 t/s median (Δ+6.25 vs best 74.35)
[11:15:58]   ✓ NEW BEST: 80.59 t/s — updating best config

## [2/12] FlashInfer workspace 1GB

[11:15:58]   FlashInfer workspace 1 GB (default 394 MB) — prevents mid-request realloc
[11:15:58]   Change: VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE = '1073741824'
[11:16:04]   restarted vllm-genesis
[11:16:34]   still starting... (30s)
[11:17:04]   still starting... (60s)
[11:17:34]   still starting... (90s)
[11:18:04]   still starting... (120s)
[11:18:14]   warming up (4 requests, Marlin kernel JIT)...
[11:18:18]     warmup 1/4: 38.6 t/s
[11:18:19]     warmup 2/4: 70.5 t/s
[11:18:21]     warmup 3/4: 70.5 t/s
[11:18:23]     warmup 4/4: 70.6 t/s
[11:18:23]   measuring (5 requests × 512 tokens)...
[11:18:30]     rep 1/5: 73.3 t/s
[11:18:37]     rep 2/5: 73.6 t/s
[11:18:44]     rep 3/5: 73.6 t/s
[11:18:51]     rep 4/5: 73.6 t/s
[11:18:58]     rep 5/5: 73.5 t/s
[11:18:58]   Result: 73.57 t/s median (Δ-7.02 vs best 80.59)
[11:18:58]   ✗ no improvement (-7.02 t/s) — reverting
[11:19:04]   restarted vllm-genesis
[11:19:34]   still starting... (30s)

## [3/12] FlashInfer workspace 768MB

[11:19:59]   FlashInfer workspace 768 MB — bisect between default and 1 GB
[11:19:59]   Change: VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE = '805306368'
[11:20:04]   restarted vllm-genesis
[11:20:34]   still starting... (30s)
[11:21:04]   still starting... (60s)
[11:21:34]   still starting... (90s)
[11:22:04]   still starting... (120s)
[11:22:14]   warming up (4 requests, Marlin kernel JIT)...
[11:22:17]     warmup 1/4: 39.1 t/s
[11:22:19]     warmup 2/4: 70.6 t/s
[11:22:21]     warmup 3/4: 70.5 t/s
[11:22:23]     warmup 4/4: 70.6 t/s
[11:22:23]   measuring (5 requests × 512 tokens)...
[11:22:30]     rep 1/5: 74.6 t/s
[11:22:37]     rep 2/5: 74.9 t/s
[11:22:43]     rep 3/5: 74.9 t/s
[11:22:50]     rep 4/5: 74.9 t/s
[11:22:57]     rep 5/5: 74.9 t/s
[11:22:57]   Result: 74.92 t/s median (Δ-5.67 vs best 80.59)
[11:22:57]   ✗ no improvement (-5.67 t/s) — reverting
[11:24:28]   restarted vllm-genesis
[11:24:58]   still starting... (30s)

## [4/12] OMP threads 2

[11:25:23]   OMP=2 threads — bisect between pass-1 baseline (1) and marginal (4)
[11:25:23]   Change: OMP_NUM_THREADS = '2'
[11:25:28]   restarted vllm-genesis
[11:25:58]   still starting... (30s)
[11:26:23]   warming up (4 requests, Marlin kernel JIT)...
[11:26:25]     warmup 1/4: 63.3 t/s
[11:26:27]     warmup 2/4: 69.1 t/s
[11:26:29]     warmup 3/4: 69.1 t/s
[11:26:31]     warmup 4/4: 69.1 t/s
[11:26:31]   measuring (5 requests × 512 tokens)...
[11:26:37]     rep 1/5: 80.2 t/s
[11:26:44]     rep 2/5: 80.1 t/s
[11:26:50]     rep 3/5: 80.1 t/s
[11:26:56]     rep 4/5: 80.1 t/s
[11:27:03]     rep 5/5: 80.1 t/s
[11:27:03]   Result: 80.14 t/s median (Δ-0.46 vs best 80.59)
[11:27:03]   ✗ no improvement (-0.46 t/s) — reverting
[11:27:08]   restarted vllm-genesis
[11:27:38]   still starting... (30s)

## [5/12] NCCL buffer 8MB

[11:28:03]   NCCL allreduce buffer 8 MB (default 4 MB) — reduces fragmentation on TP=2 PCIe
[11:28:03]   Change: NCCL_BUFFSIZE = '8388608'
[11:28:09]   restarted vllm-genesis
[11:28:39]   still starting... (30s)
[11:29:04]   warming up (4 requests, Marlin kernel JIT)...
[11:29:06]     warmup 1/4: 63.3 t/s
[11:29:08]     warmup 2/4: 69.1 t/s
[11:29:10]     warmup 3/4: 69.1 t/s
[11:29:12]     warmup 4/4: 69.1 t/s
[11:29:12]   measuring (5 requests × 512 tokens)...
[11:29:18]     rep 1/5: 80.7 t/s
[11:29:25]     rep 2/5: 81.0 t/s
[11:29:31]     rep 3/5: 81.0 t/s
[11:29:37]     rep 4/5: 81.0 t/s
[11:29:44]     rep 5/5: 81.0 t/s
[11:29:44]   Result: 80.99 t/s median (Δ+0.40 vs best 80.59)
[11:29:44]   ~ marginal (+0.40 t/s < threshold 1.5)

## [6/12] NCCL buffer 16MB

[11:29:44]   NCCL allreduce buffer 16 MB — test if larger buffer helps further
[11:29:44]   Change: NCCL_BUFFSIZE = '16777216'
[11:31:14]   restarted vllm-genesis
[11:31:44]   still starting... (30s)
[11:32:09]   warming up (4 requests, Marlin kernel JIT)...
[11:32:11]     warmup 1/4: 63.4 t/s
[11:32:13]     warmup 2/4: 69.0 t/s
[11:32:15]     warmup 3/4: 69.0 t/s
[11:32:17]     warmup 4/4: 68.9 t/s
[11:32:17]   measuring (5 requests × 512 tokens)...
[11:32:23]     rep 1/5: 81.7 t/s
[11:32:29]     rep 2/5: 81.7 t/s
[11:32:36]     rep 3/5: 81.7 t/s
[11:32:42]     rep 4/5: 81.6 t/s
[11:32:48]     rep 5/5: 81.6 t/s
[11:32:48]   Result: 81.65 t/s median (Δ+1.06 vs best 80.59)
[11:32:48]   ~ marginal (+1.06 t/s < threshold 1.5)

## [7/12] max_split_mb 64

[11:32:48]   PYTORCH_CUDA_ALLOC_CONF max_split_size_mb=64 — tighter allocator pools
[11:32:48]   Change: PYTORCH_MAX_SPLIT_MB = '64'
[11:32:54]   restarted vllm-genesis
[11:33:24]   still starting... (30s)
[11:33:49]   warming up (4 requests, Marlin kernel JIT)...
[11:33:51]     warmup 1/4: 63.5 t/s
[11:33:53]     warmup 2/4: 69.1 t/s
[11:33:54]     warmup 3/4: 69.1 t/s
[11:33:56]     warmup 4/4: 69.1 t/s
[11:33:56]   measuring (5 requests × 512 tokens)...
[11:34:03]     rep 1/5: 81.2 t/s
[11:34:09]     rep 2/5: 81.2 t/s
[11:34:15]     rep 3/5: 81.2 t/s
[11:34:22]     rep 4/5: 81.2 t/s
[11:34:28]     rep 5/5: 81.2 t/s
[11:34:28]   Result: 81.18 t/s median (Δ+0.58 vs best 80.59)
[11:34:28]   ~ marginal (+0.58 t/s < threshold 1.5)

## [8/12] max_split_mb 128

[11:34:28]   PYTORCH_CUDA_ALLOC_CONF max_split_size_mb=128 — moderate pool tightening
[11:34:28]   Change: PYTORCH_MAX_SPLIT_MB = '128'
[11:34:33]   restarted vllm-genesis
[11:35:03]   still starting... (30s)
[11:35:28]   warming up (4 requests, Marlin kernel JIT)...
[11:35:30]     warmup 1/4: 64.7 t/s
[11:35:32]     warmup 2/4: 70.6 t/s
[11:35:34]     warmup 3/4: 70.6 t/s
[11:35:36]     warmup 4/4: 70.6 t/s
[11:35:36]   measuring (5 requests × 512 tokens)...
[11:35:43]     rep 1/5: 74.1 t/s
[11:35:50]     rep 2/5: 74.4 t/s
[11:35:56]     rep 3/5: 74.6 t/s
[11:36:03]     rep 4/5: 74.5 t/s
[11:36:10]     rep 5/5: 74.4 t/s
[11:36:10]   Result: 74.44 t/s median (Δ-6.15 vs best 80.59)
[11:36:10]   ✗ no improvement (-6.15 t/s) — reverting
[11:37:41]   restarted vllm-genesis
[11:38:11]   still starting... (30s)

## [9/12] OMP4 + exclusive buffer

[11:38:36]   stack pass-1 marginals: OMP=4 (+0.94) + exclusive buffer (+1.05)
[11:38:36]   Change: OMP_NUM_THREADS = '4' also {'GENESIS_BUFFER_MODE': 'exclusive'}
[11:38:42]   restarted vllm-genesis
[11:39:12]   still starting... (30s)
[11:39:37]   warming up (4 requests, Marlin kernel JIT)...
[11:39:39]     warmup 1/4: 63.6 t/s
[11:39:40]     warmup 2/4: 69.1 t/s
[11:39:42]     warmup 3/4: 69.1 t/s
[11:39:44]     warmup 4/4: 69.1 t/s
[11:39:44]   measuring (5 requests × 512 tokens)...
[11:39:50]     rep 1/5: 80.7 t/s
[11:39:57]     rep 2/5: 80.6 t/s
[11:40:03]     rep 3/5: 80.5 t/s
[11:40:10]     rep 4/5: 80.5 t/s
[11:40:16]     rep 5/5: 80.5 t/s
[11:40:16]   Result: 80.54 t/s median (Δ-0.06 vs best 80.59)
[11:40:16]   ✗ no improvement (-0.06 t/s) — reverting
[11:40:21]   restarted vllm-genesis
[11:40:51]   still starting... (30s)

## [10/12] OMP4 + exclusive + GMU 0.88

[11:41:16]   triple marginal stack: OMP=4 + exclusive + GMU 0.88 (+0.94+1.05+0.45)
[11:41:16]   Change: OMP_NUM_THREADS = '4' also {'GENESIS_BUFFER_MODE': 'exclusive', 'gpu_memory_utilization': 0.88}
[11:42:47]   restarted vllm-genesis
[11:43:17]   still starting... (30s)
[11:43:42]   warming up (4 requests, Marlin kernel JIT)...
[11:43:44]     warmup 1/4: 63.6 t/s
[11:43:46]     warmup 2/4: 69.1 t/s
[11:43:48]     warmup 3/4: 69.1 t/s
[11:43:50]     warmup 4/4: 69.2 t/s
[11:43:50]   measuring (5 requests × 512 tokens)...
[11:43:56]     rep 1/5: 79.2 t/s
[11:44:03]     rep 2/5: 79.2 t/s
[11:44:09]     rep 3/5: 79.1 t/s
[11:44:16]     rep 4/5: 79.1 t/s
[11:44:22]     rep 5/5: 79.1 t/s
[11:44:22]   Result: 79.15 t/s median (Δ-1.45 vs best 80.59)
[11:44:22]   ✗ no improvement (-1.45 t/s) — reverting
[11:44:28]   restarted vllm-genesis
[11:44:58]   still starting... (30s)

## [11/12] ctx 16K + GMU 0.88

[11:45:23]   stack ctx 16K (+0.40) + GMU 0.88 (+0.45) — smaller graphs + more KV blocks
[11:45:23]   Change: max_model_len = 16384 also {'gpu_memory_utilization': 0.88}
[11:46:54]   restarted vllm-genesis
[11:47:24]   still starting... (30s)
[11:47:54]   still starting... (60s)
[11:48:24]   still starting... (90s)
[11:48:54]   still starting... (120s)
[11:49:04]   warming up (4 requests, Marlin kernel JIT)...
[11:49:07]     warmup 1/4: 38.9 t/s
[11:49:09]     warmup 2/4: 69.1 t/s
[11:49:11]     warmup 3/4: 69.1 t/s
[11:49:12]     warmup 4/4: 69.1 t/s
[11:49:12]   measuring (5 requests × 512 tokens)...
[11:49:19]     rep 1/5: 79.1 t/s
[11:49:25]     rep 2/5: 79.1 t/s
[11:49:32]     rep 3/5: 79.1 t/s
[11:49:38]     rep 4/5: 79.1 t/s
[11:49:45]     rep 5/5: 79.1 t/s
[11:49:45]   Result: 79.11 t/s median (Δ-1.48 vs best 80.59)
[11:49:45]   ✗ no improvement (-1.48 t/s) — reverting
[11:49:50]   restarted vllm-genesis
[11:50:20]   still starting... (30s)

## [12/12] Marlin atomic + OMP4 + exclusive

[11:50:45]   Marlin atomic-add + OMP=4 + exclusive buffer — three-way stack
[11:50:45]   Change: VLLM_MARLIN_USE_ATOMIC_ADD = '1' also {'OMP_NUM_THREADS': '4', 'GENESIS_BUFFER_MODE': 'exclusive'}
[11:50:51]   restarted vllm-genesis
[11:51:21]   still starting... (30s)
[11:51:46]   warming up (4 requests, Marlin kernel JIT)...
[11:51:48]     warmup 1/4: 63.6 t/s
[11:51:50]     warmup 2/4: 69.2 t/s
[11:51:52]     warmup 3/4: 69.1 t/s
[11:51:53]     warmup 4/4: 69.1 t/s
[11:51:53]   measuring (5 requests × 512 tokens)...
[11:52:00]     rep 1/5: 80.2 t/s
[11:52:06]     rep 2/5: 80.0 t/s
[11:52:13]     rep 3/5: 79.8 t/s
[11:52:19]     rep 4/5: 80.0 t/s
[11:52:25]     rep 5/5: 80.0 t/s
[11:52:25]   Result: 80.02 t/s median (Δ-0.58 vs best 80.59)
[11:52:25]   ✗ no improvement (-0.58 t/s) — reverting
[11:52:31]   restarted vllm-genesis
[11:53:01]   still starting... (30s)

## CANONICAL — pass 2 complete

[11:53:26] Pass-1 baseline: 74.35 t/s
[11:53:26] Best:            80.59 t/s  (Δ+6.25)
[11:53:26] Best config: {'gpu_memory_utilization': 0.82, 'max_model_len': 32768, 'max_num_seqs': 2, 'max_num_batched_tokens': 4096, 'kv_cache_dtype': 'auto', 'mtp_n': 3, 'NCCL_P2P_DISABLE': '1', 'VLLM_USE_FLASHINFER_SAMPLER': '1', 'OMP_NUM_THREADS': '1', 'CUDA_DEVICE_MAX_CONNECTIONS': '8', 'GENESIS_BUFFER_MODE': 'shared', 'GENESIS_PREALLOC_TOKEN_BUDGET': '4096', 'VLLM_MARLIN_USE_ATOMIC_ADD': '1', 'VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE': '413138944', 'NCCL_BUFFSIZE': '4194304', 'PYTORCH_MAX_SPLIT_MB': '512'}
[11:53:26] Improvements found: 1
[11:53:26]   + Marlin atomic-add: VLLM_MARLIN_USE_ATOMIC_ADD=1 → +6.25 t/s
[11:54:57]   restarted vllm-genesis
[11:55:27]   still starting... (30s)
[11:55:52]   warming up (4 requests, Marlin kernel JIT)...
[11:55:54]     warmup 1/4: 62.0 t/s
[11:55:56]     warmup 2/4: 67.6 t/s
[11:55:58]     warmup 3/4: 67.5 t/s
[11:56:00]     warmup 4/4: 67.6 t/s
[11:56:00]   measuring (5 requests × 512 tokens)...
[11:56:06]     rep 1/5: 80.5 t/s
[11:56:12]     rep 2/5: 80.6 t/s
[11:56:19]     rep 3/5: 80.5 t/s
[11:56:25]     rep 4/5: 80.5 t/s
[11:56:31]     rep 5/5: 80.4 t/s
[11:56:31] Final verification: 80.48 t/s median, 80.55 t/s p90
[11:56:31] CANONICAL ✓
starting... (30s)
[11:55:52]   warming up (4 requests, Marlin kernel JIT)...
[11:55:54]     warmup 1/4: 62.0 t/s
[11:55:56]     warmup 2/4: 67.6 t/s
[11:55:58]     warmup 3/4: 67.5 t/s
[11:56:00]     warmup 4/4: 67.6 t/s
[11:56:00]   measuring (5 requests × 512 tokens)...
[11:56:06]     rep 1/5: 80.5 t/s
[11:56:12]     rep 2/5: 80.6 t/s
[11:56:19]     rep 3/5: 80.5 t/s
[11:56:25]     rep 4/5: 80.5 t/s
[11:56:31]     rep 5/5: 80.4 t/s
[11:56:31] Final verification: 80.48 t/s median, 80.55 t/s p90
[11:56:31] CANONICAL ✓
