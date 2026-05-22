# autoresearch-gemma4-awq  started 2026-05-06 14:25

[14:25:43] === Gemma 4 31B AWQ autoresearch ===
[14:25:43] Baseline: ctx=65536 gmu=0.9 kv=fp8 seqs=2
[14:25:43] Experiments: 16  (~96 min est)
[14:25:43] --- Baseline (server already up) ---
[14:25:43]   warmup (4×128)
[14:28:36]   Baseline: 32.77 t/s  p90=32.79

## [1/16] kv=auto
[14:28:36] --- Exp 1: kv=auto ---
[14:32:49]   TIMEOUT — skipping

## [2/16] gmu=0.92
[14:32:49] --- Exp 2: gmu=0.92 ---
[14:34:33]   healthy — warmup (4×128)
[14:34:49]   benchmarking (10×512)
[14:37:26]   median=32.73 t/s  p90=32.74  delta=-0.04 (-0.1%)

## [3/16] gmu=0.95
[14:37:26] --- Exp 3: gmu=0.95 ---
[14:41:39]   TIMEOUT — skipping

## [4/16] gmu=0.88
[14:41:39] --- Exp 4: gmu=0.88 ---
[14:42:42]   healthy — warmup (4×128)
[14:42:57]   benchmarking (10×512)
[14:45:34]   median=32.72 t/s  p90=32.75  delta=-0.05 (-0.1%)

## [5/16] ctx=131072
[14:45:34] --- Exp 5: ctx=131072 ---
