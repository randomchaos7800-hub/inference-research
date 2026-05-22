# Genesis 0.21.0 Autoresearch — 2026-05-16 06:07

**Baseline:** 67.63 t/s (INT4, auto KV, MTP n=3, GMU 0.90)
**Threshold:** ±1.0 t/s to call a win/loss

## Results

| ID | Label | Median t/s | Delta | Outcome |
|---|---|---|---|---|
| baseline | Genesis baseline (INT4, auto KV, MTP n=3, GMU 0.90) | 67.63 | — | NEUTRAL |
| nvfp4_kv | nvfp4 KV cache (vLLM 0.21.0 native Blackwell FP4) | 73.66 | +6.03 | WIN |
| fp8_kv | fp8 KV cache (halves KV footprint vs auto, more KV blocks) | 68.01 | +0.38 | NEUTRAL |
| mtp_n2 | MTP 2 speculative tokens (higher accept rate) | 67.67 | +0.04 | NEUTRAL |
| mtp_n4 | MTP 4 speculative tokens (more parallelism) | 68.39 | +0.76 | NEUTRAL |
| mtp_n5 | MTP 5 speculative tokens (ceiling test) | 68.71 | +1.08 | WIN |
| batched_8192 | max_num_batched_tokens 8192 (more throughput headroom) | FAIL | — | FAIL |
| nccl_16mb | NCCL_BUFFSIZE 16MB (was +1.06 t/s in pass2) | 64.63 | -3.00 | LOSS |
| gmu_092 | GMU 0.92 (more KV blocks, slightly more VRAM) | 68.01 | +0.38 | NEUTRAL |
| nvfp4_mtp4 | nvfp4 KV + MTP n=4 (best-case combo) | 67.67 | +0.04 | NEUTRAL |

## Recommendation

**Deploy `nvfp4_kv`** — 73.66 t/s (+6.03 vs baseline). Update genesis start script.

## Log

```
[05:45:43] Genesis 0.21.0 autoresearch  2026-05-16 05:45:43
[05:45:43] Base script: /home/dino/bin/vllm-genesis-start.sh
[05:45:43] Experiments: 10
[05:45:43] 
============================================================
[05:45:43] EXPERIMENT: baseline
[05:45:43]   Genesis baseline (INT4, auto KV, MTP n=3, GMU 0.90)
[05:45:46]   killed GPU procs: [2511715]
[05:46:55]   WARNING: GPU not fully clean after 60s: [751, 1487]
[05:46:55]   script: /tmp/genesis-test-lu2w446z.sh
[05:46:59]   starting genesis...
[05:46:59]   pid=2513016 pgid=2513016
[05:46:59]   ready at 05:46:59
[05:46:59]   VRAM free: 751/1487 MiB
[05:46:59]   warmup x2...
[05:47:07]     warmup 1: 66.20 t/s
[05:47:15]     warmup 2: 67.51 t/s
[05:47:15]   bench x5...
[05:47:22]     run 1: 67.16 t/s
[05:47:30]     run 2: 67.04 t/s
[05:47:38]     run 3: 67.63 t/s
[05:47:45]     run 4: 67.82 t/s
[05:47:53]     run 5: 67.81 t/s
[05:47:53]   stopping pid=2513016...
[05:48:03]   RESULT: 67.63 t/s  (+0.00 vs baseline)  [NEUTRAL]
[05:48:03] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
[05:48:03] 
============================================================
[05:48:03] EXPERIMENT: nvfp4_kv
[05:48:03]   nvfp4 KV cache (vLLM 0.21.0 native Blackwell FP4)
[05:49:07]   WARNING: GPU not fully clean after 60s: [751, 1487]
[05:49:07]   script: /tmp/genesis-test-bnp5nsxa.sh
[05:49:11]   starting genesis...
[05:49:11]   pid=2514918 pgid=2514918
[05:49:11]   ready at 05:49:11
[05:49:11]   VRAM free: 751/1487 MiB
[05:49:11]   warmup x2...
[05:49:18]     warmup 1: 72.30 t/s
[05:49:25]     warmup 2: 73.61 t/s
[05:49:25]   bench x5...
[05:49:32]     run 1: 73.60 t/s
[05:49:39]     run 2: 72.95 t/s
[05:49:46]     run 3: 73.66 t/s
[05:49:53]     run 4: 74.00 t/s
[05:50:00]     run 5: 73.97 t/s
[05:50:00]   stopping pid=2514918...
[05:50:10]   RESULT: 73.66 t/s  (+6.03 vs baseline)  [WIN]
[05:50:10] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
[05:50:10] 
============================================================
[05:50:10] EXPERIMENT: fp8_kv
[05:50:10]   fp8 KV cache (halves KV footprint vs auto, more KV blocks)
[05:51:14]   WARNING: GPU not fully clean after 60s: [751, 1487]
[05:51:14]   script: /tmp/genesis-test-gsorzp4a.sh
[05:51:18]   starting genesis...
[05:51:18]   pid=2516825 pgid=2516825
[05:51:18]   ready at 05:51:18
[05:51:18]   VRAM free: 751/1487 MiB
[05:51:18]   warmup x2...
[05:51:26]     warmup 1: 66.44 t/s
[05:51:34]     warmup 2: 67.90 t/s
[05:51:34]   bench x5...
[05:51:41]     run 1: 67.73 t/s
[05:51:49]     run 2: 67.42 t/s
[05:51:56]     run 3: 68.01 t/s
[05:52:04]     run 4: 68.18 t/s
[05:52:11]     run 5: 68.19 t/s
[05:52:11]   stopping pid=2516825...
[05:52:21]   RESULT: 68.01 t/s  (+0.38 vs baseline)  [NEUTRAL]
[05:52:21] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
[05:52:21] 
============================================================
[05:52:21] EXPERIMENT: mtp_n2
[05:52:21]   MTP 2 speculative tokens (higher accept rate)
[05:53:25]   WARNING: GPU not fully clean after 60s: [751, 1487]
[05:53:25]   script: /tmp/genesis-test-4lm23p6o.sh
[05:53:30]   starting genesis...
[05:53:30]   pid=2518764 pgid=2518764
[05:53:30]   ready at 05:53:30
[05:53:30]   VRAM free: 731/1487 MiB
[05:53:30]   warmup x2...
[05:53:38]     warmup 1: 67.87 t/s
[05:53:45]     warmup 2: 67.52 t/s
[05:53:45]   bench x5...
[05:53:53]     run 1: 67.37 t/s
[05:54:00]     run 2: 67.03 t/s
[05:54:08]     run 3: 67.67 t/s
[05:54:15]     run 4: 67.84 t/s
[05:54:23]     run 5: 67.83 t/s
[05:54:23]   stopping pid=2518764...
[05:54:33]   RESULT: 67.67 t/s  (+0.04 vs baseline)  [NEUTRAL]
[05:54:33] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
[05:54:33] 
============================================================
[05:54:33] EXPERIMENT: mtp_n4
[05:54:33]   MTP 4 speculative tokens (more parallelism)
[05:55:37]   WARNING: GPU not fully clean after 60s: [751, 1487]
[05:55:37]   script: /tmp/genesis-test-bclciohm.sh
[05:55:41]   starting genesis...
[05:55:41]   pid=2520643 pgid=2520643
[05:55:41]   ready at 05:55:41
[05:55:41]   VRAM free: 751/1487 MiB
[05:55:41]   warmup x2...
[05:55:49]     warmup 1: 66.83 t/s
[05:55:57]     warmup 2: 68.25 t/s
[05:55:57]   bench x5...
[05:56:04]     run 1: 68.10 t/s
[05:56:12]     run 2: 67.77 t/s
[05:56:19]     run 3: 68.39 t/s
[05:56:27]     run 4: 68.58 t/s
[05:56:34]     run 5: 68.58 t/s
[05:56:34]   stopping pid=2520643...
[05:56:44]   RESULT: 68.39 t/s  (+0.76 vs baseline)  [NEUTRAL]
[05:56:44] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
[05:56:44] 
============================================================
[05:56:44] EXPERIMENT: mtp_n5
[05:56:44]   MTP 5 speculative tokens (ceiling test)
[05:57:48]   WARNING: GPU not fully clean after 60s: [751, 1487]
[05:57:48]   script: /tmp/genesis-test-z5k3lfpo.sh
[05:57:52]   starting genesis...
[05:57:52]   pid=2522574 pgid=2522574
[05:57:52]   ready at 05:57:52
[05:57:52]   VRAM free: 751/1487 MiB
[05:57:52]   warmup x2...
[05:58:00]     warmup 1: 67.40 t/s
[05:58:07]     warmup 2: 68.62 t/s
[05:58:07]   bench x5...
[05:58:15]     run 1: 68.44 t/s
[05:58:22]     run 2: 68.13 t/s
[05:58:30]     run 3: 68.71 t/s
[05:58:37]     run 4: 68.94 t/s
[05:58:45]     run 5: 68.91 t/s
[05:58:45]   stopping pid=2522574...
[05:58:55]   RESULT: 68.71 t/s  (+1.08 vs baseline)  [WIN]
[05:58:55] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
[05:58:55] 
============================================================
[05:58:55] EXPERIMENT: batched_8192
[05:58:55]   max_num_batched_tokens 8192 (more throughput headroom)
[05:59:58]   WARNING: GPU not fully clean after 60s: [751, 1487]
[05:59:58]   script: /tmp/genesis-test-v3sgfyn_.sh
[06:00:03]   starting genesis...
[06:00:03]   pid=2524581 pgid=2524581
[06:00:03]   ready at 06:00:03
[06:00:03]   VRAM free: 731/1487 MiB
[06:00:03]   warmup x2...
[06:00:11]     warmup 1: 69.69 t/s
[06:00:18]     warmup 2: 69.31 t/s
[06:00:18]   bench x5...
[06:00:21]     run 1 ERROR: HTTP Error 500: Internal Server Error
[06:00:21]     run 2 ERROR: HTTP Error 500: Internal Server Error
[06:00:21]     run 3 ERROR: HTTP Error 500: Internal Server Error
[06:00:21]     run 4 ERROR: HTTP Error 500: Internal Server Error
[06:00:21]     run 5 ERROR: HTTP Error 500: Internal Server Error
[06:00:21]   stopping pid=2524581...
[06:00:31]   RESULT: FAILED
[06:00:31] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
[06:00:31] 
============================================================
[06:00:31] EXPERIMENT: nccl_16mb
[06:00:31]   NCCL_BUFFSIZE 16MB (was +1.06 t/s in pass2)
[06:01:35]   WARNING: GPU not fully clean after 60s: [751, 1487]
[06:01:35]   script: /tmp/genesis-test-r5629q2l.sh
[06:01:40]   starting genesis...
[06:01:40]   pid=2526042 pgid=2526042
[06:01:40]   ready at 06:01:40
[06:01:40]   VRAM free: 751/1487 MiB
[06:01:40]   warmup x2...
[06:01:48]     warmup 1: 63.33 t/s
[06:01:56]     warmup 2: 64.45 t/s
[06:01:56]   bench x5...
[06:02:04]     run 1: 63.91 t/s
[06:02:12]     run 2: 64.38 t/s
[06:02:20]     run 3: 64.63 t/s
[06:02:28]     run 4: 64.74 t/s
[06:02:36]     run 5: 64.72 t/s
[06:02:36]   stopping pid=2526042...
[06:02:46]   RESULT: 64.63 t/s  (-3.00 vs baseline)  [LOSS]
[06:02:46] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
[06:02:46] 
============================================================
[06:02:46] EXPERIMENT: gmu_092
[06:02:46]   GMU 0.92 (more KV blocks, slightly more VRAM)
[06:03:49]   WARNING: GPU not fully clean after 60s: [751, 1487]
[06:03:49]   script: /tmp/genesis-test-sjvvtyg1.sh
[06:03:54]   starting genesis...
[06:03:54]   pid=2528021 pgid=2528021
[06:03:54]   ready at 06:03:54
[06:03:54]   VRAM free: 751/1487 MiB
[06:03:54]   warmup x2...
[06:04:02]     warmup 1: 66.48 t/s
[06:04:09]     warmup 2: 67.88 t/s
[06:04:09]   bench x5...
[06:04:17]     run 1: 67.69 t/s
[06:04:24]     run 2: 67.42 t/s
[06:04:32]     run 3: 68.01 t/s
[06:04:39]     run 4: 68.19 t/s
[06:04:47]     run 5: 68.19 t/s
[06:04:47]   stopping pid=2528021...
[06:04:57]   RESULT: 68.01 t/s  (+0.38 vs baseline)  [NEUTRAL]
[06:04:57] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
[06:04:57] 
============================================================
[06:04:57] EXPERIMENT: nvfp4_mtp4
[06:04:57]   nvfp4 KV + MTP n=4 (best-case combo)
[06:06:01]   WARNING: GPU not fully clean after 60s: [751, 1487]
[06:06:01]   script: /tmp/genesis-test-h3lriwkx.sh
[06:06:05]   starting genesis...
[06:06:05]   pid=2529913 pgid=2529913
[06:06:05]   ready at 06:06:05
[06:06:05]   VRAM free: 751/1487 MiB
[06:06:05]   warmup x2...
[06:06:13]     warmup 1: 66.27 t/s
[06:06:21]     warmup 2: 67.52 t/s
[06:06:21]   bench x5...
[06:06:28]     run 1: 67.37 t/s
[06:06:36]     run 2: 67.06 t/s
[06:06:43]     run 3: 67.67 t/s
[06:06:51]     run 4: 67.83 t/s
[06:06:59]     run 5: 67.82 t/s
[06:06:59]   stopping pid=2529913...
[06:07:09]   RESULT: 67.67 t/s  (+0.04 vs baseline)  [NEUTRAL]
[06:07:09] TSV → /home/dino/inference-research/autoresearch-genesis-021-results.tsv
```
