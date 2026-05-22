# autoresearch-aeon-nvfp4  started 2026-04-28 13:46

[13:46:26] === AEON NVFP4 autoresearch ===
[13:46:26] Baseline: ctx=122880 gmu=0.9 fp8 KV mtp_n=3
[13:46:26] Experiments: 13  (~65 min)
[13:46:26] --- Baseline ---
[13:50:33]   Baseline: 68.86 t/s  p90=69.30

## [1/13] mtp_n=1
[13:50:33] --- Exp 1: mtp_n=1 ---
[13:53:09]   healthy — warmup (4×128)
[13:53:21]   benchmarking (10×512)
[13:55:01]   median=51.51 t/s  p90=51.53  delta=-17.35 (-25.2%)

## [2/13] mtp_n=2
[13:55:01] --- Exp 2: mtp_n=2 ---
[13:57:41]   healthy — warmup (4×128)
[13:57:53]   benchmarking (10×512)
[13:59:15]   median=62.46 t/s  p90=62.81  delta=-6.40 (-9.3%)

## [3/13] mtp_n=4
[13:59:15] --- Exp 3: mtp_n=4 ---
[14:02:30]   TIMEOUT — did not become healthy in 3 min

## [4/13] mtp_n=5
[14:02:30] --- Exp 4: mtp_n=5 ---
[14:07:11]   TIMEOUT — did not become healthy in 3 min

## [5/13] batched=8192
[14:07:11] --- Exp 5: batched=8192 ---
[14:11:16]   healthy — warmup (4×128)
[14:11:27]   benchmarking (10×512)
[14:12:41]   median=69.75 t/s  p90=69.82  delta=+0.89 (+1.3%)

## [6/13] batched=2048
[14:12:41] --- Exp 6: batched=2048 ---
[14:15:11]   healthy — warmup (4×128)
[14:15:23]   benchmarking (10×512)
[14:16:39]   median=67.15 t/s  p90=67.24  delta=-1.71 (-2.5%)

## [7/13] seqs=1
[14:16:39] --- Exp 7: seqs=1 ---
[14:19:35]   healthy — warmup (4×128)
[14:19:46]   benchmarking (10×512)
[14:21:06]   median=63.85 t/s  p90=63.94  delta=-5.01 (-7.3%)

## [8/13] gmu=0.88
[14:21:06] --- Exp 8: gmu=0.88 ---
[14:24:22]   TIMEOUT — did not become healthy in 3 min

## [9/13] gmu=0.92
[14:24:22] --- Exp 9: gmu=0.92 ---
[14:27:12]   healthy — warmup (4×128)
[14:27:21]   benchmarking (10×512)
[14:28:38]   median=66.75 t/s  p90=66.81  delta=-2.11 (-3.1%)

## [10/13] prealloc=8192
[14:28:38] --- Exp 10: prealloc=8192 ---
[14:31:28]   healthy — warmup (4×128)
[14:31:37]   benchmarking (10×512)
[14:32:53]   median=66.96 t/s  p90=67.01  delta=-1.90 (-2.8%)

## [11/13] prealloc=2048
[14:32:53] --- Exp 11: prealloc=2048 ---
[14:34:19]   healthy — warmup (4×128)
[14:34:28]   benchmarking (10×512)
[14:35:43]   median=68.12 t/s  p90=68.18  delta=-0.74 (-1.1%)

## [12/13] mtp_n=4+batched=8192
[14:35:43] --- Exp 12: mtp_n=4+batched=8192 ---
[14:38:59]   TIMEOUT — did not become healthy in 3 min

## [13/13] mtp_n=4+seqs=1
[14:38:59] --- Exp 13: mtp_n=4+seqs=1 ---
[14:43:40]   TIMEOUT — did not become healthy in 3 min
[14:43:40] --- Writing best config: baseline (68.86 t/s) ---
[14:46:30]   Best config live and healthy
[14:46:30] 
=== COMPLETE ===
[14:46:30]   Baseline: 68.86 t/s
[14:46:30]   Best:     68.86 t/s  (+0.0%)  [baseline]
[14:46:30]   Config written to /home/dino/vllm-aeon-nvfp4-start.sh

## COMPLETE — 2026-04-28 14:46
Best: baseline  68.86 t/s  (+0.0%)
