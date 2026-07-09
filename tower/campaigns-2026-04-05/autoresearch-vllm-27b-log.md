
## autoresearch-vllm-27b — Karpathy loop

[09:32:24] Baseline config: {'gpu_memory_utilization': 0.82, 'max_model_len': 32768, 'max_num_seqs': 2, 'max_num_batched_tokens': 4096, 'kv_cache_dtype': 'fp8', 'mtp_n': 3, 'NCCL_P2P_DISABLE': '1', 'VLLM_USE_FLASHINFER_SAMPLER': '1', 'OMP_NUM_THREADS': '1', 'CUDA_DEVICE_MAX_CONNECTIONS': '8', 'GENESIS_BUFFER_MODE': 'shared', 'GENESIS_PREALLOC_TOKEN_BUDGET': '4096'}
[09:32:24] Experiments: 21
[09:32:24] Bench: 4 warmup + 5 timed reps × 512 tokens
[09:32:24] Improve threshold: 1.5 t/s

## BASELINE — measuring current config

[09:32:24]   restarted vllm-genesis
[09:32:54]   still starting... (30s)
[09:33:20]   warming up (4 requests, Marlin kernel JIT)...
[09:33:22]     warmup 1/4: 59.9 t/s
[09:33:24]     warmup 2/4: 66.3 t/s
[09:33:26]     warmup 3/4: 66.2 t/s
[09:33:27]     warmup 4/4: 66.2 t/s
[09:33:27]   measuring (5 requests × 512 tokens)...
[09:33:34]     rep 1/5: 75.6 t/s
[09:33:41]     rep 2/5: 75.7 t/s
[09:33:48]     rep 3/5: 75.7 t/s
[09:33:55]     rep 4/5: 75.6 t/s
[09:34:01]     rep 5/5: 75.6 t/s
[09:34:01] Baseline: 75.63 t/s median, 75.67 t/s p90

## [1/21] batched-tokens 8192

[09:34:01]   fix scheduler warning: scheduled = 8192/4 = 2048 tokens (was 1024)
[09:34:01]   Change: max_num_batched_tokens = 8192
[09:34:07]   restarted vllm-genesis
[09:34:37]   still starting... (30s)
[09:35:07]   warming up (4 requests, Marlin kernel JIT)...
[09:35:10]     warmup 1/4: 36.0 t/s
[09:35:12]     warmup 2/4: 67.6 t/s
[09:35:14]     warmup 3/4: 67.6 t/s
[09:35:16]     warmup 4/4: 67.6 t/s
[09:35:16]   measuring (5 requests × 512 tokens)...
[09:35:23]     rep 1/5: 74.2 t/s
[09:35:30]     rep 2/5: 74.2 t/s
[09:35:37]     rep 3/5: 74.2 t/s
[09:35:44]     rep 4/5: 74.2 t/s
[09:35:51]     rep 5/5: 74.1 t/s
[09:35:51]   Result: 74.16 t/s median (Δ-1.47 vs best 75.63)
[09:35:51]   ✗ no improvement (-1.47 t/s) — reverting
[09:35:56]   restarted vllm-genesis
[09:36:26]   still starting... (30s)

## [2/21] batched-tokens 16384

[09:36:51]   aggressive: scheduled = 4096 tokens per step
[09:36:51]   Change: max_num_batched_tokens = 16384
[09:36:57]   restarted vllm-genesis
[09:37:27]   still starting... (30s)
[09:37:57]   still starting... (60s)
[09:38:27]   still starting... (90s)
[09:38:57]   still starting... (120s)
[09:39:27]   still starting... (150s)
[09:39:57]   still starting... (180s)
[09:40:27]   still starting... (210s)
[09:40:57]   still starting... (240s)
[09:41:27]   still starting... (270s)
[09:41:57]   still starting... (300s)
[09:42:27]   still starting... (330s)
[09:42:57]   still starting... (360s)
[09:43:27]   still starting... (390s)
[09:43:57]   still starting... (420s)
[09:44:27]   still starting... (450s)
[09:44:57]   TIMEOUT — vLLM did not start within 480s
[09:44:57]   Reverting to best config...
[09:46:28]   restarted vllm-genesis
[09:46:58]   still starting... (30s)

## [3/21] NCCL P2P enable

[09:47:23]   allow direct GPU-GPU P2P over PCIe (currently disabled via CPU)
[09:47:23]   Change: NCCL_P2P_DISABLE = '0'
[09:47:29]   restarted vllm-genesis
[09:47:59]   still starting... (30s)
[09:48:24]   warming up (4 requests, Marlin kernel JIT)...
[09:48:26]     warmup 1/4: 61.1 t/s
[09:48:28]     warmup 2/4: 67.9 t/s
[09:48:30]     warmup 3/4: 67.8 t/s
[09:48:31]     warmup 4/4: 67.9 t/s
[09:48:31]   measuring (5 requests × 512 tokens)...
[09:48:39]     rep 1/5: 71.5 t/s
[09:48:46]     rep 2/5: 71.9 t/s
[09:48:53]     rep 3/5: 71.9 t/s
[09:49:00]     rep 4/5: 71.9 t/s
[09:49:07]     rep 5/5: 71.8 t/s
[09:49:07]   Result: 71.86 t/s median (Δ-3.77 vs best 75.63)
[09:49:07]   ✗ no improvement (-3.77 t/s) — reverting
[09:50:38]   restarted vllm-genesis
[09:51:08]   still starting... (30s)

## [4/21] MTP n=4

[09:51:33]   4 speculative tokens — higher draft overhead vs more tokens accepted
[09:51:33]   Change: mtp_n = 4
[09:51:39]   restarted vllm-genesis
[09:52:09]   still starting... (30s)
[09:52:39]   still starting... (60s)
[09:53:09]   still starting... (90s)
[09:53:39]   still starting... (120s)
[09:53:44]   warming up (4 requests, Marlin kernel JIT)...
[09:53:48]     warmup 1/4: 29.8 t/s
[09:53:50]     warmup 2/4: 63.7 t/s
[09:53:52]     warmup 3/4: 63.6 t/s
[09:53:54]     warmup 4/4: 63.6 t/s
[09:53:54]   measuring (5 requests × 512 tokens)...
[09:54:01]     rep 1/5: 69.2 t/s
[09:54:09]     rep 2/5: 69.6 t/s
[09:54:16]     rep 3/5: 69.6 t/s
[09:54:23]     rep 4/5: 69.6 t/s
[09:54:31]     rep 5/5: 69.6 t/s
[09:54:31]   Result: 69.56 t/s median (Δ-6.07 vs best 75.63)
[09:54:31]   ✗ no improvement (-6.07 t/s) — reverting
[09:54:36]   restarted vllm-genesis
[09:55:06]   still starting... (30s)

## [5/21] MTP n=5

[09:55:31]   5 speculative tokens — max speculation, most overhead
[09:55:31]   Change: mtp_n = 5
[09:57:02]   restarted vllm-genesis
[09:57:32]   still starting... (30s)
[09:58:02]   still starting... (60s)
[09:58:32]   still starting... (90s)
[09:59:02]   still starting... (120s)
[09:59:07]   warming up (4 requests, Marlin kernel JIT)...
[09:59:11]     warmup 1/4: 29.6 t/s
[09:59:13]     warmup 2/4: 61.6 t/s
[09:59:16]     warmup 3/4: 61.6 t/s
[09:59:18]     warmup 4/4: 61.5 t/s
[09:59:18]   measuring (5 requests × 512 tokens)...
[09:59:25]     rep 1/5: 66.3 t/s
[09:59:33]     rep 2/5: 66.0 t/s
[09:59:41]     rep 3/5: 66.3 t/s
[09:59:49]     rep 4/5: 66.3 t/s
[09:59:56]     rep 5/5: 66.2 t/s
[09:59:56]   Result: 66.27 t/s median (Δ-9.36 vs best 75.63)
[09:59:56]   ✗ no improvement (-9.36 t/s) — reverting
[10:00:02]   restarted vllm-genesis
[10:00:32]   still starting... (30s)

## [6/21] MTP n=2

[10:00:57]   2 speculative tokens — less overhead, tests if n=3 over-speculates
[10:00:57]   Change: mtp_n = 2
[10:01:03]   restarted vllm-genesis
[10:01:33]   still starting... (30s)
[10:02:03]   still starting... (60s)
[10:02:33]   still starting... (90s)
[10:03:03]   still starting... (120s)
[10:03:08]   warming up (4 requests, Marlin kernel JIT)...
[10:03:12]     warmup 1/4: 30.1 t/s
[10:03:14]     warmup 2/4: 65.1 t/s
[10:03:16]     warmup 3/4: 65.0 t/s
[10:03:18]     warmup 4/4: 65.0 t/s
[10:03:18]   measuring (5 requests × 512 tokens)...
[10:03:25]     rep 1/5: 71.4 t/s
[10:03:32]     rep 2/5: 71.4 t/s
[10:03:39]     rep 3/5: 71.3 t/s
[10:03:47]     rep 4/5: 71.2 t/s
[10:03:54]     rep 5/5: 71.3 t/s
[10:03:54]   Result: 71.35 t/s median (Δ-4.29 vs best 75.63)
[10:03:54]   ✗ no improvement (-4.29 t/s) — reverting
[10:03:59]   restarted vllm-genesis
[10:04:29]   still starting... (30s)

## [7/21] MTP n=1

[10:04:54]   1 speculative token — near-baseline, isolates MTP overhead cost
[10:04:54]   Change: mtp_n = 1
[10:06:25]   restarted vllm-genesis
[10:06:55]   still starting... (30s)
[10:07:20]   warming up (4 requests, Marlin kernel JIT)...
[10:07:23]     warmup 1/4: 43.7 t/s
[10:07:25]     warmup 2/4: 56.6 t/s
[10:07:27]     warmup 3/4: 56.6 t/s
[10:07:30]     warmup 4/4: 56.5 t/s
[10:07:30]   measuring (5 requests × 512 tokens)...
[10:07:38]     rep 1/5: 59.3 t/s
[10:07:47]     rep 2/5: 59.3 t/s
[10:07:56]     rep 3/5: 59.3 t/s
[10:08:04]     rep 4/5: 59.2 t/s
[10:08:13]     rep 5/5: 59.2 t/s
[10:08:13]   Result: 59.28 t/s median (Δ-16.36 vs best 75.63)
[10:08:13]   ✗ no improvement (-16.36 t/s) — reverting
[10:08:18]   restarted vllm-genesis
[10:08:48]   still starting... (30s)

## [8/21] no MTP

[10:09:13]   disable speculative decoding entirely — measure raw decode t/s
[10:09:13]   Change: mtp_n = 0
[10:09:20]   restarted vllm-genesis
[10:09:50]   still starting... (30s)
[10:10:20]   still starting... (60s)
[10:10:50]   still starting... (90s)
[10:11:20]   warming up (4 requests, Marlin kernel JIT)...
[10:11:24]     warmup 1/4: 31.4 t/s
[10:11:27]     warmup 2/4: 39.7 t/s
[10:11:30]     warmup 3/4: 39.7 t/s
[10:11:33]     warmup 4/4: 39.7 t/s
[10:11:33]   measuring (5 requests × 512 tokens)...
[10:11:46]     rep 1/5: 40.3 t/s
[10:11:59]     rep 2/5: 40.3 t/s
[10:12:11]     rep 3/5: 40.3 t/s
[10:12:24]     rep 4/5: 40.3 t/s
[10:12:37]     rep 5/5: 40.3 t/s
[10:12:37]   Result: 40.29 t/s median (Δ-35.35 vs best 75.63)
[10:12:37]   ✗ no improvement (-35.35 t/s) — reverting
[10:12:42]   restarted vllm-genesis
[10:13:12]   still starting... (30s)

## [9/21] KV fp16 (auto)

[10:13:37]   fp16 KV: no dequant overhead per layer — costs ~4GB extra VRAM at 32K
[10:13:37]   Change: kv_cache_dtype = 'auto'
[10:13:43]   restarted vllm-genesis
[10:14:13]   still starting... (30s)
[10:14:43]   still starting... (60s)
[10:15:13]   still starting... (90s)
[10:15:43]   still starting... (120s)
[10:16:08]   warming up (4 requests, Marlin kernel JIT)...
[10:16:44]     warmup 1/4: 3.6 t/s
[10:16:46]     warmup 2/4: 69.1 t/s
[10:16:47]     warmup 3/4: 69.0 t/s
[10:16:49]     warmup 4/4: 69.1 t/s
[10:16:49]   measuring (5 requests × 512 tokens)...
[10:16:56]     rep 1/5: 80.6 t/s
[10:17:02]     rep 2/5: 80.6 t/s
[10:17:08]     rep 3/5: 80.6 t/s
[10:17:15]     rep 4/5: 80.6 t/s
[10:17:21]     rep 5/5: 80.6 t/s
[10:17:21]   Result: 80.58 t/s median (Δ+4.95 vs best 75.63)
[10:17:21]   ✓ NEW BEST: 80.58 t/s — updating best config

## [10/21] GMU 0.85

[10:17:21]   more KV cache blocks — ~1.5GB more VRAM for KV at 32K ctx
[10:17:21]   Change: gpu_memory_utilization = 0.85
[10:17:27]   restarted vllm-genesis
[10:17:57]   still starting... (30s)
[10:18:22]   warming up (4 requests, Marlin kernel JIT)...
[10:18:24]     warmup 1/4: 59.1 t/s
[10:18:26]     warmup 2/4: 70.6 t/s
[10:18:27]     warmup 3/4: 70.6 t/s
[10:18:29]     warmup 4/4: 70.5 t/s
[10:18:29]   measuring (5 requests × 512 tokens)...
[10:18:36]     rep 1/5: 73.8 t/s
[10:18:43]     rep 2/5: 74.1 t/s
[10:18:50]     rep 3/5: 74.1 t/s
[10:18:57]     rep 4/5: 74.1 t/s
[10:19:04]     rep 5/5: 74.0 t/s
[10:19:04]   Result: 74.09 t/s median (Δ-6.49 vs best 80.58)
[10:19:04]   ✗ no improvement (-6.49 t/s) — reverting
[10:20:35]   restarted vllm-genesis
[10:21:05]   still starting... (30s)

## [11/21] GMU 0.88

[10:21:30]   max safe GMU tested at 32K ctx — risk: activation workspace OOM
[10:21:30]   Change: gpu_memory_utilization = 0.88
[10:21:35]   restarted vllm-genesis
[10:22:05]   still starting... (30s)
[10:22:30]   warming up (4 requests, Marlin kernel JIT)...
[10:22:32]     warmup 1/4: 59.1 t/s
[10:22:34]     warmup 2/4: 69.1 t/s
[10:22:36]     warmup 3/4: 68.8 t/s
[10:22:38]     warmup 4/4: 69.1 t/s
[10:22:38]   measuring (5 requests × 512 tokens)...
[10:22:44]     rep 1/5: 80.7 t/s
[10:22:50]     rep 2/5: 81.0 t/s
[10:22:57]     rep 3/5: 81.0 t/s
[10:23:03]     rep 4/5: 81.0 t/s
[10:23:09]     rep 5/5: 81.0 t/s
[10:23:09]   Result: 81.03 t/s median (Δ+0.45 vs best 80.58)
[10:23:09]   ~ marginal (+0.45 t/s < threshold 1.5)

## [12/21] sampler default

[10:23:09]   disable FlashInfer sampler, use PyTorch sampler — less overhead for single stream
[10:23:09]   Change: VLLM_USE_FLASHINFER_SAMPLER = '0'
[10:24:40]   restarted vllm-genesis
[10:25:10]   still starting... (30s)
[10:25:40]   still starting... (60s)
[10:26:10]   still starting... (90s)
[10:26:40]   still starting... (120s)
[10:26:50]   warming up (4 requests, Marlin kernel JIT)...
[10:26:53]     warmup 1/4: 38.6 t/s
[10:26:55]     warmup 2/4: 70.5 t/s
[10:26:57]     warmup 3/4: 70.4 t/s
[10:26:59]     warmup 4/4: 70.5 t/s
[10:26:59]   measuring (5 requests × 512 tokens)...
[10:27:06]     rep 1/5: 74.5 t/s
[10:27:13]     rep 2/5: 74.8 t/s
[10:27:19]     rep 3/5: 74.8 t/s
[10:27:26]     rep 4/5: 74.8 t/s
[10:27:33]     rep 5/5: 74.8 t/s
[10:27:33]   Result: 74.77 t/s median (Δ-5.81 vs best 80.58)
[10:27:33]   ✗ no improvement (-5.81 t/s) — reverting
[10:27:39]   restarted vllm-genesis
[10:28:09]   still starting... (30s)

## [13/21] seqs 1

[10:28:34]   single sequence mode — eliminates inter-seq padding and scheduling overhead
[10:28:34]   Change: max_num_seqs = 1
[10:30:04]   restarted vllm-genesis
[10:30:34]   still starting... (30s)
[10:31:04]   still starting... (60s)
[10:31:34]   still starting... (90s)
[10:32:04]   still starting... (120s)
[10:32:14]   warming up (4 requests, Marlin kernel JIT)...
[10:32:18]     warmup 1/4: 37.0 t/s
[10:32:20]     warmup 2/4: 69.1 t/s
[10:32:21]     warmup 3/4: 69.1 t/s
[10:32:23]     warmup 4/4: 69.1 t/s
[10:32:23]   measuring (5 requests × 512 tokens)...
[10:32:30]     rep 1/5: 77.2 t/s
[10:32:37]     rep 2/5: 77.2 t/s
[10:32:43]     rep 3/5: 77.2 t/s
[10:32:50]     rep 4/5: 77.2 t/s
[10:32:57]     rep 5/5: 77.2 t/s
[10:32:57]   Result: 77.19 t/s median (Δ-3.39 vs best 80.58)
[10:32:57]   ✗ no improvement (-3.39 t/s) — reverting
[10:33:02]   restarted vllm-genesis
[10:33:32]   still starting... (30s)

## [14/21] seqs 4

[10:33:57]   4 concurrent — test batch decode throughput
[10:33:57]   Change: max_num_seqs = 4
[10:34:03]   restarted vllm-genesis
[10:34:33]   still starting... (30s)
[10:35:03]   still starting... (60s)
[10:35:33]   still starting... (90s)
[10:36:03]   still starting... (120s)
[10:36:13]   warming up (4 requests, Marlin kernel JIT)...
[10:36:16]     warmup 1/4: 40.5 t/s
[10:36:18]     warmup 2/4: 69.1 t/s
[10:36:20]     warmup 3/4: 69.1 t/s
[10:36:21]     warmup 4/4: 69.1 t/s
[10:36:21]   measuring (5 requests × 512 tokens)...
[10:36:28]     rep 1/5: 80.6 t/s
[10:36:34]     rep 2/5: 80.6 t/s
[10:36:40]     rep 3/5: 80.6 t/s
[10:36:47]     rep 4/5: 80.6 t/s
[10:36:53]     rep 5/5: 80.6 t/s
[10:36:53]   Result: 80.61 t/s median (Δ+0.03 vs best 80.58)
[10:36:53]   ~ marginal (+0.03 t/s < threshold 1.5)

## [15/21] ctx 16K

[10:36:53]   half context — smaller CUDA graph tables, more KV blocks at same GMU
[10:36:53]   Change: max_model_len = 16384
[10:36:59]   restarted vllm-genesis
[10:37:29]   still starting... (30s)
[10:37:59]   still starting... (60s)
[10:38:29]   still starting... (90s)
[10:38:59]   still starting... (120s)
[10:39:09]   warming up (4 requests, Marlin kernel JIT)...
[10:39:12]     warmup 1/4: 38.8 t/s
[10:39:14]     warmup 2/4: 69.0 t/s
[10:39:16]     warmup 3/4: 69.0 t/s
[10:39:18]     warmup 4/4: 69.0 t/s
[10:39:18]   measuring (5 requests × 512 tokens)...
[10:39:24]     rep 1/5: 80.6 t/s
[10:39:30]     rep 2/5: 81.0 t/s
[10:39:37]     rep 3/5: 81.0 t/s
[10:39:43]     rep 4/5: 81.0 t/s
[10:39:49]     rep 5/5: 81.0 t/s
[10:39:49]   Result: 80.98 t/s median (Δ+0.40 vs best 80.58)
[10:39:49]   ~ marginal (+0.40 t/s < threshold 1.5)

## [16/21] ctx 64K + GMU 0.85

[10:39:49]   double context at 0.85 GMU — tests if activation workspace fits
[10:39:49]   Change: max_model_len = 65536 also {'gpu_memory_utilization': 0.85}
[10:41:20]   restarted vllm-genesis
[10:41:50]   still starting... (30s)
[10:42:20]   still starting... (60s)
[10:42:50]   still starting... (90s)
[10:43:20]   still starting... (120s)
[10:43:30]   warming up (4 requests, Marlin kernel JIT)...
[10:43:33]     warmup 1/4: 39.3 t/s
[10:43:35]     warmup 2/4: 70.5 t/s
[10:43:37]     warmup 3/4: 70.4 t/s
[10:43:39]     warmup 4/4: 70.5 t/s
[10:43:39]   measuring (5 requests × 512 tokens)...
[10:43:46]     rep 1/5: 74.1 t/s
[10:43:53]     rep 2/5: 74.3 t/s
[10:43:59]     rep 3/5: 74.4 t/s
[10:44:06]     rep 4/5: 74.4 t/s
[10:44:13]     rep 5/5: 74.4 t/s
[10:44:13]   Result: 74.40 t/s median (Δ-6.18 vs best 80.58)
[10:44:13]   ✗ no improvement (-6.18 t/s) — reverting
[10:45:44]   restarted vllm-genesis
[10:46:14]   still starting... (30s)

## [17/21] CUDA_CONNECTIONS 16

[10:46:39]   more concurrent kernel streams for TP=2 all-reduce overlap
[10:46:39]   Change: CUDA_DEVICE_MAX_CONNECTIONS = '16'
[10:46:45]   restarted vllm-genesis
[10:47:15]   still starting... (30s)
[10:47:40]   warming up (4 requests, Marlin kernel JIT)...
[10:47:42]     warmup 1/4: 63.3 t/s
[10:47:43]     warmup 2/4: 69.1 t/s
[10:47:45]     warmup 3/4: 69.1 t/s
[10:47:47]     warmup 4/4: 69.1 t/s
[10:47:47]   measuring (5 requests × 512 tokens)...
[10:47:54]     rep 1/5: 79.2 t/s
[10:48:00]     rep 2/5: 79.1 t/s
[10:48:07]     rep 3/5: 79.2 t/s
[10:48:13]     rep 4/5: 79.1 t/s
[10:48:20]     rep 5/5: 79.1 t/s
[10:48:20]   Result: 79.14 t/s median (Δ-1.44 vs best 80.58)
[10:48:20]   ✗ no improvement (-1.44 t/s) — reverting
[10:48:25]   restarted vllm-genesis
[10:48:55]   still starting... (30s)

## [18/21] OMP_THREADS 4

[10:49:20]   more CPU threads for MKL/OpenMP ops in GDN layers
[10:49:20]   Change: OMP_NUM_THREADS = '4'
[10:50:51]   restarted vllm-genesis
[10:51:21]   still starting... (30s)
[10:51:41]   warming up (4 requests, Marlin kernel JIT)...
[10:51:43]     warmup 1/4: 63.2 t/s
[10:51:45]     warmup 2/4: 69.1 t/s
[10:51:47]     warmup 3/4: 69.1 t/s
[10:51:49]     warmup 4/4: 69.0 t/s
[10:51:49]   measuring (5 requests × 512 tokens)...
[10:51:55]     rep 1/5: 81.2 t/s
[10:52:01]     rep 2/5: 81.5 t/s
[10:52:07]     rep 3/5: 81.5 t/s
[10:52:14]     rep 4/5: 81.5 t/s
[10:52:20]     rep 5/5: 81.5 t/s
[10:52:20]   Result: 81.52 t/s median (Δ+0.94 vs best 80.58)
[10:52:20]   ~ marginal (+0.94 t/s < threshold 1.5)

## [19/21] Genesis exclusive buffer

[10:52:20]   per-worker Genesis buffers — test if shared pool causes contention
[10:52:20]   Change: GENESIS_BUFFER_MODE = 'exclusive'
[10:52:26]   restarted vllm-genesis
[10:52:56]   still starting... (30s)
[10:53:21]   warming up (4 requests, Marlin kernel JIT)...
[10:53:23]     warmup 1/4: 64.6 t/s
[10:53:24]     warmup 2/4: 69.1 t/s
[10:53:26]     warmup 3/4: 69.1 t/s
[10:53:28]     warmup 4/4: 69.1 t/s
[10:53:28]   measuring (5 requests × 512 tokens)...
[10:53:34]     rep 1/5: 81.7 t/s
[10:53:41]     rep 2/5: 81.6 t/s
[10:53:47]     rep 3/5: 81.6 t/s
[10:53:53]     rep 4/5: 81.6 t/s
[10:54:00]     rep 5/5: 81.6 t/s
[10:54:00]   Result: 81.64 t/s median (Δ+1.05 vs best 80.58)
[10:54:00]   ~ marginal (+1.05 t/s < threshold 1.5)

## [20/21] Genesis prealloc 8192

[10:54:00]   larger token budget pre-allocation for Genesis P64 MTP streaming
[10:54:00]   Change: GENESIS_PREALLOC_TOKEN_BUDGET = '8192'
[10:54:05]   restarted vllm-genesis
[10:54:35]   still starting... (30s)
[10:55:00]   warming up (4 requests, Marlin kernel JIT)...
[10:55:02]     warmup 1/4: 64.4 t/s
[10:55:04]     warmup 2/4: 70.5 t/s
[10:55:06]     warmup 3/4: 70.6 t/s
[10:55:07]     warmup 4/4: 70.6 t/s
[10:55:07]   measuring (5 requests × 512 tokens)...
[10:55:14]     rep 1/5: 74.6 t/s
[10:55:21]     rep 2/5: 74.9 t/s
[10:55:28]     rep 3/5: 74.9 t/s
[10:55:35]     rep 4/5: 74.9 t/s
[10:55:42]     rep 5/5: 74.9 t/s
[10:55:42]   Result: 74.93 t/s median (Δ-5.65 vs best 80.58)
[10:55:42]   ✗ no improvement (-5.65 t/s) — reverting
[10:55:47]   restarted vllm-genesis
[10:56:17]   still starting... (30s)
[10:56:42] [21] SKIP combo 'combo: batched 8192 + P2P on' (no component showed improvement)

## CANONICAL — autoresearch complete

[10:56:42] Baseline:  75.63 t/s
[10:56:42] Best:      80.58 t/s  (Δ+4.95)
[10:56:42] Best config: {'gpu_memory_utilization': 0.82, 'max_model_len': 32768, 'max_num_seqs': 2, 'max_num_batched_tokens': 4096, 'kv_cache_dtype': 'auto', 'mtp_n': 3, 'NCCL_P2P_DISABLE': '1', 'VLLM_USE_FLASHINFER_SAMPLER': '1', 'OMP_NUM_THREADS': '1', 'CUDA_DEVICE_MAX_CONNECTIONS': '8', 'GENESIS_BUFFER_MODE': 'shared', 'GENESIS_PREALLOC_TOKEN_BUDGET': '4096'}
[10:56:42] Improvements found: 1
[10:56:42]   + KV fp16 (auto): kv_cache_dtype=auto → +4.95 t/s
[10:56:48]   restarted vllm-genesis
[10:57:18]   still starting... (30s)
[10:57:43]   warming up (4 requests, Marlin kernel JIT)...
[10:57:46]     warmup 1/4: 62.4 t/s
[10:57:47]     warmup 2/4: 68.9 t/s
[10:57:49]     warmup 3/4: 69.0 t/s
[10:57:51]     warmup 4/4: 69.1 t/s
[10:57:51]   measuring (5 requests × 512 tokens)...
[10:57:58]     rep 1/5: 80.1 t/s
[10:58:04]     rep 2/5: 80.5 t/s
[10:58:10]     rep 3/5: 80.6 t/s
[10:58:17]     rep 4/5: 80.5 t/s
[10:58:23]     rep 5/5: 80.5 t/s
[10:58:23] Final verification: 80.49 t/s median, 80.56 t/s p90
[10:58:23] CANONICAL ✓
     warmup 3/4: 69.0 t/s
[10:57:51]     warmup 4/4: 69.1 t/s
[10:57:51]   measuring (5 requests × 512 tokens)...
[10:57:58]     rep 1/5: 80.1 t/s
[10:58:04]     rep 2/5: 80.5 t/s
[10:58:10]     rep 3/5: 80.6 t/s
[10:58:17]     rep 4/5: 80.5 t/s
[10:58:23]     rep 5/5: 80.5 t/s
[10:58:23] Final verification: 80.49 t/s median, 80.56 t/s p90
[10:58:23] CANONICAL ✓
