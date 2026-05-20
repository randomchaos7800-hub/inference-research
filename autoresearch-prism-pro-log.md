# autoresearch-prism-pro — 2026-05-19

Model: /home/dino/models/Qwen3.6-27B-PRISM-PRO-DQ/Qwen3.6-27B-PRISM-PRO-DQ.gguf

## Results

| rank | id | tg_med | wall_med | delta | flags |
|------|-----|--------|----------|-------|-------|
| 1 | mtp_n2 | 39.30 | 37.82 | +4.52 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 1 --reasoning off` |
| 2 | kv_q8_mtp2 | 38.48 | 37.02 | +3.70 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 1 --reasoning off --cache-type-k q8_0 --cache-type-v q8_0` |
| 3 | mtp_n2_min2 | 37.84 | 37.48 | +3.06 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 2 --reasoning off` |
| 4 | kv_q4 | 35.70 | 34.67 | +0.92 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --cache-type-k q4_0 --cache-type-v q4_0` |
| 5 | threads_16 | 35.60 | 34.73 | +0.82 | `--n-gpu-layers 999 --ctx-size 32768 --threads 16 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off` |
| 6 | ctx_16k | 35.58 | 33.94 | +0.80 | `--n-gpu-layers 999 --ctx-size 16384 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off` |
| 7 | ctx_64k_q8 | 35.56 | 35.20 | +0.78 | `--n-gpu-layers 999 --ctx-size 65536 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --cache-type-k q8_0 --cache-type-v q8_0` |
| 8 | kv_q8 | 35.45 | 34.53 | +0.66 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --cache-type-k q8_0 --cache-type-v q8_0` |
| 9 | ubatch_1024 | 35.41 | 34.74 | +0.63 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --ubatch-size 1024` |
| 10 | ctx_64k | 35.34 | 34.42 | +0.56 | `--n-gpu-layers 999 --ctx-size 65536 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off` |
| 11 | mtp_n3 | 35.13 | 35.07 | +0.35 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-n-min 1 --reasoning off` |
| 12 | ubatch_256 | 34.93 | 33.68 | +0.15 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --ubatch-size 256` |
| 13 | baseline | 34.78 | 34.50 | +0.00 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off` |
| 14 | mtp_n0 | 26.25 | 25.86 | -8.54 | `--n-gpu-layers 999 --ctx-size 32768 --threads 8 --reasoning off` |
| 15 | threads_4 | 20.94 | 26.87 | -13.84 | `--n-gpu-layers 999 --ctx-size 32768 --threads 4 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off` |

## Winner

`--n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 1 --reasoning off`

## Full log

```
[21:28:20] autoresearch-prism-pro starting — 2026-05-19T21:28:20.573667
[21:28:20] model: /home/dino/models/Qwen3.6-27B-PRISM-PRO-DQ/Qwen3.6-27B-PRISM-PRO-DQ.gguf
[21:28:20] experiments: 16
[21:28:20] 
============================================================
[21:28:20] EXP: baseline — MTP n_max=1 (current)
[21:28:23]   GPU clean: [15761, 15834] MiB free
[21:28:23]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off
[21:28:27]   server ready
[21:28:27]   warmup (2 runs)...
[21:28:57]   bench (5 runs)...
[21:29:13]     run 1: 33.04 t/s (wall)
[21:29:28]     run 2: 34.50 t/s (wall)
[21:29:42]     run 3: 35.18 t/s (wall)
[21:29:57]     run 4: 35.22 t/s (wall)
[21:30:13]     run 5: 31.63 t/s (wall)
[21:30:13]   server tg readings: [34.64, 33.38, 33.55, 33.72, 33.68, 34.73, 34.95, 34.83, 35.35, 36.04, 35.91, 35.6, 35.92, 35.42, 36.15, 35.53, 36.11, 33.91, 30.04, 31.44, 31.89, 32.27]
[21:30:13]   RESULT: wall=34.50 t/s  server_tg=34.78 t/s
[21:30:15]   baseline set: 34.78 t/s
[21:30:15] 
============================================================
[21:30:15] EXP: mtp_n0 — no speculative decoding (sanity baseline)
[21:30:18]   GPU clean: [15761, 15834] MiB free
[21:30:18]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --reasoning off
[21:30:22]   server ready
[21:30:22]   warmup (2 runs)...
[21:31:01]   bench (5 runs)...
[21:31:21]     run 1: 25.86 t/s (wall)
[21:31:41]     run 2: 25.87 t/s (wall)
[21:32:01]     run 3: 25.86 t/s (wall)
[21:32:21]     run 4: 25.87 t/s (wall)
[21:32:40]     run 5: 25.86 t/s (wall)
[21:32:40]   server tg readings: [26.43, 26.32, 26.26, 26.23, 26.22, 26.2, 26.42, 26.32, 26.26, 26.23, 26.22, 26.2, 26.42, 26.32, 26.26, 26.23, 26.22, 26.2, 26.42, 26.32, 26.26, 26.23, 26.22, 26.2, 26.43, 26.32, 26.26, 26.23, 26.22, 26.2]
[21:32:40]   RESULT: wall=25.86 t/s  server_tg=26.25 t/s
[21:32:42]   vs baseline: -8.54 t/s (-24.5%)
[21:32:42] 
============================================================
[21:32:42] EXP: mtp_n2 — MTP n_max=2
[21:32:45]   GPU clean: [15761, 15834] MiB free
[21:32:45]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 1 --reasoning off
[21:32:49]   server ready
[21:32:49]   warmup (2 runs)...
[21:33:17]   bench (5 runs)...
[21:33:32]     run 1: 35.24 t/s (wall)
[21:33:46]     run 2: 37.54 t/s (wall)
[21:33:59]     run 3: 37.94 t/s (wall)
[21:34:12]     run 4: 38.87 t/s (wall)
[21:34:26]     run 5: 37.82 t/s (wall)
[21:34:26]   server tg readings: [40.03, 37.2, 35.73, 35.5, 40.98, 39.57, 38.22, 38.55, 40.03, 41.48, 39.68, 39.03, 44.08, 41.21, 40.63, 41.12, 36.66, 38.71, 37.41, 38.7]
[21:34:26]   RESULT: wall=37.82 t/s  server_tg=39.30 t/s
[21:34:28]   vs baseline: +4.52 t/s (+13.0%)
[21:34:28] 
============================================================
[21:34:28] EXP: mtp_n3 — MTP n_max=3
[21:34:31]   GPU clean: [15761, 15834] MiB free
[21:34:31]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-n-min 1 --reasoning off
[21:34:35]   server ready
[21:34:35]   warmup (2 runs)...
[21:35:13]   bench (5 runs)...
[21:35:39]     run 1: 19.47 t/s (wall)
[21:35:54]     run 2: 35.06 t/s (wall)
[21:36:08]     run 3: 36.48 t/s (wall)
[21:36:22]     run 4: 38.20 t/s (wall)
[21:36:36]     run 5: 35.07 t/s (wall)
[21:36:36]   server tg readings: [19.99, 19.66, 18.71, 19.85, 17.54, 19.35, 19.84, 22.14, 20.71, 20.91, 23.32, 19.87, 37.24, 34.19, 35.22, 35.05, 37.84, 38.57, 37.42, 37.02, 37.22, 37.78, 37.01, 37.81, 37.51, 37.2, 36.38, 36.17]
[21:36:36]   RESULT: wall=35.07 t/s  server_tg=35.13 t/s
[21:36:38]   vs baseline: +0.35 t/s (+1.0%)
[21:36:38] 
============================================================
[21:36:38] EXP: mtp_n2_min2 — MTP n_max=2 n_min=2 (force 2 drafts always)
[21:36:41]   GPU clean: [15761, 15834] MiB free
[21:36:41]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 2 --reasoning off
[21:36:45]   server ready
[21:36:45]   warmup (2 runs)...
[21:37:13]   bench (5 runs)...
[21:37:28]     run 1: 35.81 t/s (wall)
[21:37:42]     run 2: 35.69 t/s (wall)
[21:37:56]     run 3: 37.48 t/s (wall)
[21:38:09]     run 4: 38.56 t/s (wall)
[21:38:22]     run 5: 37.71 t/s (wall)
[21:38:22]   server tg readings: [33.76, 34.79, 36.11, 36.88, 36.63, 36.23, 36.61, 35.74, 37.81, 37.96, 38.34, 37.87, 40.11, 40.76, 40.13, 39.8, 35.97, 37.88, 38.69, 38.47]
[21:38:22]   RESULT: wall=37.48 t/s  server_tg=37.84 t/s
[21:38:24]   vs baseline: +3.06 t/s (+8.8%)
[21:38:24] 
============================================================
[21:38:24] EXP: kv_q8 — KV cache q8_0 (halves KV VRAM)
[21:38:27]   GPU clean: [15761, 15834] MiB free
[21:38:27]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --cache-type-k q8_0 --cache-type-v q8_0
[21:38:31]   server ready
[21:38:31]   warmup (2 runs)...
[21:39:00]   bench (5 runs)...
[21:39:15]     run 1: 34.13 t/s (wall)
[21:39:30]     run 2: 34.29 t/s (wall)
[21:39:45]     run 3: 34.64 t/s (wall)
[21:39:59]     run 4: 35.61 t/s (wall)
[21:40:14]     run 5: 34.53 t/s (wall)
[21:40:14]   server tg readings: [33.39, 35.15, 35.25, 34.93, 36.42, 36.55, 35.9, 35.23, 34.31, 35.46, 35.25, 35.43, 37.85, 36.86, 35.92, 36.18, 35.51, 35.4, 36.0, 35.4]
[21:40:14]   RESULT: wall=34.53 t/s  server_tg=35.45 t/s
[21:40:16]   vs baseline: +0.66 t/s (+1.9%)
[21:40:16] 
============================================================
[21:40:16] EXP: kv_q4 — KV cache q4_0 (quarters KV VRAM)
[21:40:19]   GPU clean: [15761, 15834] MiB free
[21:40:19]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --cache-type-k q4_0 --cache-type-v q4_0
[21:40:23]   server ready
[21:40:23]   warmup (2 runs)...
[21:40:53]   bench (5 runs)...
[21:41:09]     run 1: 33.50 t/s (wall)
[21:41:23]     run 2: 34.67 t/s (wall)
[21:41:38]     run 3: 34.44 t/s (wall)
[21:41:53]     run 4: 34.96 t/s (wall)
[21:42:07]     run 5: 35.17 t/s (wall)
[21:42:07]   server tg readings: [36.53, 35.88, 35.28, 34.93, 34.25, 36.64, 35.6, 35.23, 35.24, 36.99, 36.24, 34.76, 34.72, 36.39, 35.3, 35.75, 35.8, 34.87, 36.21, 36.18, 35.7]
[21:42:07]   RESULT: wall=34.67 t/s  server_tg=35.70 t/s
[21:42:09]   vs baseline: +0.92 t/s (+2.6%)
[21:42:09] 
============================================================
[21:42:09] EXP: kv_q8_mtp2 — q8 KV + MTP n=2 (combo)
[21:42:13]   GPU clean: [15761, 15834] MiB free
[21:42:13]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 1 --reasoning off --cache-type-k q8_0 --cache-type-v q8_0
[21:42:17]   server ready
[21:42:17]   warmup (2 runs)...
[21:42:46]   bench (5 runs)...
[21:43:00]     run 1: 35.12 t/s (wall)
[21:43:14]     run 2: 35.88 t/s (wall)
[21:43:28]     run 3: 37.02 t/s (wall)
[21:43:42]     run 4: 38.33 t/s (wall)
[21:43:55]     run 5: 38.61 t/s (wall)
[21:43:55]   server tg readings: [36.97, 35.87, 36.09, 35.96, 35.41, 36.0, 36.17, 36.79, 41.46, 41.36, 38.48, 37.81, 41.48, 40.26, 38.49, 38.95, 39.95, 39.74, 39.62, 39.64]
[21:43:55]   RESULT: wall=37.02 t/s  server_tg=38.48 t/s
[21:43:57]   vs baseline: +3.70 t/s (+10.7%)
[21:43:57] 
============================================================
[21:43:57] EXP: ctx_16k — ctx-size 16384
[21:44:00]   GPU clean: [15761, 15834] MiB free
[21:44:00]   flags: --n-gpu-layers 999 --ctx-size 16384 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off
[21:44:04]   server ready
[21:44:04]   warmup (2 runs)...
[21:44:33]   bench (5 runs)...
[21:44:48]     run 1: 33.76 t/s (wall)
[21:45:04]     run 2: 33.10 t/s (wall)
[21:45:19]     run 3: 33.94 t/s (wall)
[21:45:34]     run 4: 34.77 t/s (wall)
[21:45:48]     run 5: 35.57 t/s (wall)
[21:45:48]   server tg readings: [32.81, 34.23, 34.52, 34.28, 35.68, 35.53, 35.17, 34.94, 33.64, 37.01, 36.51, 35.58, 35.12, 37.08, 37.1, 36.41, 36.18, 35.57, 36.31, 36.27, 36.25]
[21:45:48]   RESULT: wall=33.94 t/s  server_tg=35.58 t/s
[21:45:50]   vs baseline: +0.80 t/s (+2.3%)
[21:45:50] 
============================================================
[21:45:50] EXP: ctx_64k — ctx-size 65536
[21:45:53]   GPU clean: [15761, 15834] MiB free
[21:45:53]   flags: --n-gpu-layers 999 --ctx-size 65536 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off
[21:45:57]   server ready
[21:45:57]   warmup (2 runs)...
[21:46:27]   bench (5 runs)...
[21:46:42]     run 1: 33.93 t/s (wall)
[21:46:57]     run 2: 34.42 t/s (wall)
[21:47:12]     run 3: 34.64 t/s (wall)
[21:47:26]     run 4: 36.12 t/s (wall)
[21:47:41]     run 5: 33.76 t/s (wall)
[21:47:41]   server tg readings: [34.46, 34.01, 34.37, 34.07, 36.96, 36.06, 35.61, 34.81, 36.96, 36.41, 35.28, 35.26, 38.35, 37.98, 37.43, 37.03, 35.41, 35.04, 34.83, 34.93]
[21:47:41]   RESULT: wall=34.42 t/s  server_tg=35.34 t/s
[21:47:43]   vs baseline: +0.56 t/s (+1.6%)
[21:47:43] 
============================================================
[21:47:43] EXP: ctx_64k_q8 — ctx-size 65536 + q8 KV
[21:47:46]   GPU clean: [15761, 15834] MiB free
[21:47:46]   flags: --n-gpu-layers 999 --ctx-size 65536 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --cache-type-k q8_0 --cache-type-v q8_0
[21:47:50]   server ready
[21:47:50]   warmup (2 runs)...
[21:48:20]   bench (5 runs)...
[21:48:34]     run 1: 34.67 t/s (wall)
[21:48:50]     run 2: 33.83 t/s (wall)
[21:49:04]     run 3: 35.20 t/s (wall)
[21:49:18]     run 4: 35.47 t/s (wall)
[21:49:33]     run 5: 35.32 t/s (wall)
[21:49:33]   server tg readings: [35.48, 35.54, 35.91, 35.33, 35.22, 34.73, 33.69, 34.01, 34.29, 35.58, 36.02, 35.33, 38.53, 36.79, 36.79, 36.31, 36.1, 36.48, 35.49, 36.1]
[21:49:33]   RESULT: wall=35.20 t/s  server_tg=35.56 t/s
[21:49:35]   vs baseline: +0.78 t/s (+2.2%)
[21:49:35] 
============================================================
[21:49:35] EXP: threads_4 — 4 CPU threads
[21:49:38]   GPU clean: [15761, 15834] MiB free
[21:49:38]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 4 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off
[21:49:42]   server ready
[21:49:42]   warmup (2 runs)...
[21:50:12]   bench (5 runs)...
[21:50:27]     run 1: 34.03 t/s (wall)
[21:50:46]     run 2: 26.87 t/s (wall)
[21:51:12]     run 3: 20.21 t/s (wall)
[21:51:34]     run 4: 23.10 t/s (wall)
[21:51:48]     run 5: 35.10 t/s (wall)
[21:51:48]   server tg readings: [35.45, 36.09, 34.98, 34.93, 35.78, 35.95, 35.55, 35.79, 28.8, 20.55, 20.46, 20.48, 20.61, 20.93, 20.26, 20.85, 20.27, 20.95, 20.41, 20.82, 21.55, 20.6, 20.01, 21.44, 20.86, 17.86, 18.05, 18.18, 19.69, 22.25, 33.88, 35.01, 35.93, 36.32]
[21:51:48]   RESULT: wall=26.87 t/s  server_tg=20.94 t/s
[21:51:50]   vs baseline: -13.84 t/s (-39.8%)
[21:51:50] 
============================================================
[21:51:50] EXP: threads_16 — 16 CPU threads
[21:51:53]   GPU clean: [15761, 15834] MiB free
[21:51:53]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 16 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off
[21:51:57]   server ready
[21:51:57]   warmup (2 runs)...
[21:52:27]   bench (5 runs)...
[21:52:42]     run 1: 33.88 t/s (wall)
[21:52:57]     run 2: 34.02 t/s (wall)
[21:53:12]     run 3: 34.93 t/s (wall)
[21:53:26]     run 4: 35.33 t/s (wall)
[21:53:41]     run 5: 34.73 t/s (wall)
[21:53:41]   server tg readings: [33.9, 34.14, 34.91, 35.07, 37.33, 35.62, 35.45, 34.98, 34.67, 36.34, 36.52, 35.6, 35.47, 35.74, 36.1, 35.77, 36.11, 35.51, 35.95, 35.46, 35.8]
[21:53:41]   RESULT: wall=34.73 t/s  server_tg=35.60 t/s
[21:53:43]   vs baseline: +0.82 t/s (+2.4%)
[21:53:43] 
============================================================
[21:53:43] EXP: ubatch_256 — ubatch-size 256
[21:53:46]   GPU clean: [15761, 15834] MiB free
[21:53:46]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --ubatch-size 256
[21:53:50]   server ready
[21:53:50]   warmup (2 runs)...
[21:54:20]   bench (5 runs)...
[21:54:36]     run 1: 33.07 t/s (wall)
[21:54:51]     run 2: 33.45 t/s (wall)
[21:55:06]     run 3: 34.33 t/s (wall)
[21:55:20]     run 4: 35.80 t/s (wall)
[21:55:36]     run 5: 33.68 t/s (wall)
[21:55:36]   server tg readings: [32.25, 32.92, 32.55, 33.27, 33.11, 34.39, 34.51, 34.2, 35.65, 35.18, 35.04, 34.93, 36.31, 36.72, 36.39, 36.82, 36.31, 35.68, 34.91, 35.12, 34.37]
[21:55:36]   RESULT: wall=33.68 t/s  server_tg=34.93 t/s
[21:55:38]   vs baseline: +0.15 t/s (+0.4%)
[21:55:38] 
============================================================
[21:55:38] EXP: ubatch_1024 — ubatch-size 1024
[21:55:41]   GPU clean: [15761, 15834] MiB free
[21:55:41]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --ubatch-size 1024
[21:55:45]   server ready
[21:55:45]   warmup (2 runs)...
[21:56:15]   bench (5 runs)...
[21:56:30]     run 1: 33.35 t/s (wall)
[21:56:45]     run 2: 34.73 t/s (wall)
[21:57:00]     run 3: 34.96 t/s (wall)
[21:57:14]     run 4: 35.47 t/s (wall)
[21:57:29]     run 5: 34.74 t/s (wall)
[21:57:29]   server tg readings: [32.76, 33.49, 33.9, 34.36, 35.36, 35.66, 35.9, 35.46, 35.36, 35.31, 34.78, 35.22, 36.26, 36.64, 36.43, 36.29, 33.3, 35.61, 35.55, 35.72]
[21:57:29]   RESULT: wall=34.74 t/s  server_tg=35.41 t/s
[21:57:31]   vs baseline: +0.63 t/s (+1.8%)
[21:57:31] 
============================================================
[21:57:31] EXP: flash_attn — flash-attn (attention layers in hybrid)
[21:57:34]   GPU clean: [15761, 15834] MiB free
[21:57:34]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 1 --spec-draft-n-min 1 --reasoning off --flash-attn
[21:59:34]   FAIL: server did not come up in 120s
[21:59:34]   skipping flash_attn (server failed)
[21:59:34] 
============================================================
[21:59:34] FINAL RESULTS
[21:59:34] ============================================================
[21:59:34]   mtp_n2                tg= 39.30  wall= 37.82  (+4.52)
[21:59:34]   kv_q8_mtp2            tg= 38.48  wall= 37.02  (+3.70)
[21:59:34]   mtp_n2_min2           tg= 37.84  wall= 37.48  (+3.06)
[21:59:34]   kv_q4                 tg= 35.70  wall= 34.67  (+0.92)
[21:59:34]   threads_16            tg= 35.60  wall= 34.73  (+0.82)
[21:59:34]   ctx_16k               tg= 35.58  wall= 33.94  (+0.80)
[21:59:34]   ctx_64k_q8            tg= 35.56  wall= 35.20  (+0.78)
[21:59:34]   kv_q8                 tg= 35.45  wall= 34.53  (+0.66)
[21:59:34]   ubatch_1024           tg= 35.41  wall= 34.74  (+0.63)
[21:59:34]   ctx_64k               tg= 35.34  wall= 34.42  (+0.56)
[21:59:34]   mtp_n3                tg= 35.13  wall= 35.07  (+0.35)
[21:59:34]   ubatch_256            tg= 34.93  wall= 33.68  (+0.15)
[21:59:34]   baseline              tg= 34.78  wall= 34.50  (+0.00)
[21:59:34]   mtp_n0                tg= 26.25  wall= 25.86  (-8.54)
[21:59:34]   threads_4             tg= 20.94  wall= 26.87  (-13.84)
[21:59:34] 
WINNER: mtp_n2 — 39.30 t/s
[21:59:34]   flags: --n-gpu-layers 999 --ctx-size 32768 --threads 8 --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 1 --reasoning off
[21:59:34] 
TSV: /home/dino/inference-research/autoresearch-prism-pro-results.tsv
```
