# autoresearch-vllm-27b-pass3  started 2026-04-27 12:20

[12:20:35] === Pass 3: Context ceiling sweep ===
[12:20:35] Experiments: 18  (~90 min)
[12:20:35] --- Baseline ---
[12:24:12]   Baseline: 80.65 t/s  p90=80.68

## [1/18] 40K/0.82
[12:24:12] --- Exp 1: 40K/0.82  ctx=40960  gmu=0.82 ---
[12:26:27]   healthy — Marlin warmup (4×128)
[12:26:36]   benchmarking (10×512)
[12:27:41]   median=79.08 t/s  p90=79.11  delta=-1.57 (-1.9%)
[12:27:41]   → new best high-ctx: 40K/0.82  40960 tok  79.08 t/s

## [2/18] 48K/0.82
[12:27:41] --- Exp 2: 48K/0.82  ctx=49152  gmu=0.82 ---
[12:29:57]   healthy — Marlin warmup (4×128)
[12:30:06]   benchmarking (10×512)
[12:31:10]   median=79.52 t/s  p90=79.55  delta=-1.12 (-1.4%)
[12:31:10]   → new best high-ctx: 48K/0.82  49152 tok  79.52 t/s

## [3/18] 64K/0.82
[12:31:10] --- Exp 3: 64K/0.82  ctx=65536  gmu=0.82 ---
[12:34:21]   healthy — Marlin warmup (4×128)
[12:34:29]   benchmarking (10×512)
[12:35:32]   median=81.58 t/s  p90=81.63  delta=+0.93 (+1.2%)
[12:35:32]   → new best high-ctx: 64K/0.82  65536 tok  81.58 t/s

## [4/18] 80K/0.82
[12:35:32] --- Exp 4: 80K/0.82  ctx=81920  gmu=0.82 ---
[12:40:08]   healthy — Marlin warmup (4×128)
[12:40:16]   benchmarking (10×512)
[12:41:19]   median=81.44 t/s  p90=81.49  delta=+0.79 (+1.0%)
[12:41:19]   → new best high-ctx: 80K/0.82  81920 tok  81.44 t/s

## [5/18] 96K/0.82
[12:41:19] --- Exp 5: 96K/0.82  ctx=98304  gmu=0.82 ---
[12:46:00]   TIMEOUT — did not become healthy in 3 min

## [6/18] 128K/0.82
[12:46:00] --- Exp 6: 128K/0.82  ctx=131072  gmu=0.82 ---
[12:49:10]   TIMEOUT — did not become healthy in 3 min

## [7/18] 40K/0.85
[12:49:10] --- Exp 7: 40K/0.85  ctx=40960  gmu=0.85 ---
[12:50:05]   healthy — Marlin warmup (4×128)
[12:50:12]   benchmarking (10×512)
[12:51:16]   median=81.14 t/s  p90=81.18  delta=+0.49 (+0.6%)

## [8/18] 48K/0.85
[12:51:16] --- Exp 8: 48K/0.85  ctx=49152  gmu=0.85 ---
[12:52:16]   healthy — Marlin warmup (4×128)
[12:52:24]   benchmarking (10×512)
[12:53:27]   median=81.03 t/s  p90=81.09  delta=+0.38 (+0.5%)

## [9/18] 64K/0.85
[12:53:27] --- Exp 9: 64K/0.85  ctx=65536  gmu=0.85 ---
[12:54:28]   healthy — Marlin warmup (4×128)
[12:54:35]   benchmarking (10×512)
[12:55:45]   median=73.32 t/s  p90=73.35  delta=-7.33 (-9.1%)

## [10/18] 80K/0.85
[12:55:45] --- Exp 10: 80K/0.85  ctx=81920  gmu=0.85 ---
[12:56:45]   healthy — Marlin warmup (4×128)
[12:56:53]   benchmarking (10×512)
[12:57:56]   median=81.05 t/s  p90=81.11  delta=+0.40 (+0.5%)

## [11/18] 96K/0.85
[12:57:56] --- Exp 11: 96K/0.85  ctx=98304  gmu=0.85 ---
[12:58:57]   healthy — Marlin warmup (4×128)
[12:59:05]   benchmarking (10×512)
[13:00:08]   median=81.07 t/s  p90=81.09  delta=+0.42 (+0.5%)
[13:00:08]   → new best high-ctx: 96K/0.85  98304 tok  81.07 t/s

## [12/18] 128K/0.85
[13:00:08] --- Exp 12: 128K/0.85  ctx=131072  gmu=0.85 ---
[13:03:24]   TIMEOUT — did not become healthy in 3 min

## [13/18] 64K/0.88
[13:03:24] --- Exp 13: 64K/0.88  ctx=65536  gmu=0.88 ---
[13:05:49]   healthy — Marlin warmup (4×128)
[13:05:57]   benchmarking (10×512)
[13:07:00]   median=81.03 t/s  p90=81.07  delta=+0.38 (+0.5%)

## [14/18] 80K/0.88
[13:07:00] --- Exp 14: 80K/0.88  ctx=81920  gmu=0.88 ---
[13:08:01]   healthy — Marlin warmup (4×128)
[13:08:08]   benchmarking (10×512)
[13:09:12]   median=80.07 t/s  p90=80.12  delta=-0.58 (-0.7%)

## [15/18] 96K/0.88
[13:09:12] --- Exp 15: 96K/0.88  ctx=98304  gmu=0.88 ---
[13:10:13]   healthy — Marlin warmup (4×128)
[13:10:20]   benchmarking (10×512)
[13:11:23]   median=81.62 t/s  p90=81.73  delta=+0.97 (+1.2%)

## [16/18] 128K/0.88
[13:11:23] --- Exp 16: 128K/0.88  ctx=131072  gmu=0.88 ---
[13:14:39]   TIMEOUT — did not become healthy in 3 min

## [17/18] 96K/0.90
[13:14:39] --- Exp 17: 96K/0.90  ctx=98304  gmu=0.9 ---
[13:17:04]   healthy — Marlin warmup (4×128)
[13:17:12]   benchmarking (10×512)
[13:18:20]   median=74.51 t/s  p90=74.54  delta=-6.14 (-7.6%)

## [18/18] 128K/0.90
[13:18:20] --- Exp 18: 128K/0.90  ctx=131072  gmu=0.9 ---
[13:19:21]   healthy — Marlin warmup (4×128)
[13:19:30]   benchmarking (10×512)
[13:20:34]   median=80.04 t/s  p90=80.14  delta=-0.60 (-0.8%)
[13:20:34]   → new best high-ctx: 128K/0.90  131072 tok  80.04 t/s
[13:20:34] --- Restoring canonical baseline config (32K/0.82) ---
[13:21:34]   Production baseline restored and healthy
[13:21:34] 
=== PASS 3 COMPLETE ===
[13:21:34]   Baseline:      80.65 t/s @ 32K ctx (GMU 0.82)
[13:21:34]   Best high-ctx: 128K/0.90  131072 tok @ GMU 0.9  80.04 t/s (-0.8%)
[13:21:34]   Production restored to 32K — update manually if you want higher ctx

## PASS 3 COMPLETE — 2026-04-27 13:21
Best high-ctx (≤5% loss): {'ctx': 131072, 'gmu': 0.9, 'median': 80.04475784853958, 'name': '128K/0.90'}
