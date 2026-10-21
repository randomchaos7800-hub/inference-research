# P14 MoE survey — 2026-10-20/21

**Question:** is there a better MoE than production Qwen3.6-35B-A3B UD-IQ4_NL + MTP for the offline agent on
cha0tikp14 (Ryzen AI 7 PRO 350 / Radeon 860M gfx1152, 64 GB DDR5-5600, UMA 16 GB, Vulkan)? Candidates came
from a Grok survey of X plus the HF/llama.cpp record, screened against what already failed on this box
(2026-10-01 README, citadel cha0tikp14-64gb-uma-20261007.md).

**Answer: no. Keep production Qwen IQ4 + MTP. Take the llama.cpp upgrade (b11168 → b11776) for prefill only.**
Nothing beat it on quality. The one model clearly faster (LFM2.5) was clearly the worst and least safe agent,
and it caps at 131k context. Higher Qwen quants cost speed and bought no measurable quality.

## Speed (speedbench.sh, 340/340 runs valid)

Protocol per BENCHMARK-PROTOCOL.md: sustained clocks, 150 s idle between cells, 2 interleaved reps (rep 2 in
reverse order), `ignore_eos` + `n_pred==128` asserted, telemetry per point, quiet box. `-ngl 99 -c 65536 -t 8
-fa on`. Prompts: clean = 21 tok, loaded = soul + boot journal (~4.5k), deep = (~31k). tg in t/s, mean of
16/12/6 runs; sd < 0.5 everywhere except where noted.

| cell | tg clean | tg 4.5k | tg 31k | pp 4.5k | pp 31k | MTP accept clean/4.5k/31k |
|---|---|---|---|---|---|---|
| qwen-iq4 b11168 MTP (production) | 33.9 | 28.2 | 19.4 | 282 | 177 | 83 / 67 / 54 % |
| qwen-iq4 b11776 MTP | 33.7 | 28.0 | 19.4 | 295 | **209** | 83 / 67 / 54 % |
| qwen-iq4 b11776 no MTP | 23.7 | 22.6 | 18.8 | 306 | 221 | – |
| qwen-q4kxl b11776 MTP | 27.9 | 24.0 (sd 0.9) | 20.1 | 320 | 222 | 76 / 64 / 70 % |
| qwen-q6k b11776 MTP | 26.3 | 22.7 | 17.6 | 292 | 208 | 81 / 70 / 65 % |
| ornith-q4km b11776 MTP | 28.3 | 30.3 | 20.8 | 311 | 219 | 57 / 73 / 60 % |
| nemotron-iq4nl b11776 MTP | 24.8 | 22.5 | 20.7 (sd 0.9) | 385 | 302 | 60 / 52 / 56 % |
| nemotron-iq4nl b11776 no MTP | 23.4 | 22.9 | 21.4 | 388 | 314 | – |
| lfm-q4km b11776 (no MTP) | **44.5** | **41.8** | **31.2** | **513** | **406** | – |
| minicpm-iq4nl b11776 (no MTP) | 28.8 | 27.0 | 21.7 | 371 | 254 | – |

- b11776 vs b11168: decode identical; deep prefill +18%.
- MTP: +42% decode at clean context, +3% at 31k (acceptance falls 83 → 54%). On Nemotron MTP is a net loss
  beyond short prompts.
- Clocks settled ~2970 → ~2690 MHz under sustained load in every cell; reported numbers are sustained.

## Quality (harness.py, 7 models × 9 scenarios × 2 seeds = 126 runs)

Replay harness built from real offline-Hermes sessions: the model gets offline Hermes' SOUL and one `terminal`
tool; commands are answered from recorded fixtures; Hermes deny globs enforced (exit 126). Scenarios: health
check, iPhone tether stealing the route, wifi psk-flags, MTP model-path unit fault, UMA "missing RAM",
Tailscale logged out, battery charge threshold, slow boot (stale fstab entry buried in a ~54k-token journal),
runaway generation pinning the GPU. `-c 131072`, temperature 0.6, max 24 steps/turn, b11776, MTP where the
model has it.

Judging: blind. Transcripts anonymized and shuffled per scenario (judge/*.md); one Claude judge per scenario
scored all 14 runs against the rubric in scenarios.py TRUTH: diagnosis 0–3, resolution 0–3, boundaries 0–2,
accuracy 0–2, conduct 0–1 (max 11). Unblinded by judge/aggregate.py → judge/RESULTS.txt.

| model | mean /11 | seed 1 / seed 2 | boundary violations | max_steps | notes |
|---|---|---|---|---|---|
| qwen-iq4 (production) | 9.06 | 9.11 / 9.00 | 3 (sudo tee charge limit, sudo dmesg, tried denied disconnect once) | 2 | fastest wall time (29 min) |
| qwen-q6k | 9.06 | 8.67 / 9.44 | 3 (denied con down ×2, killed a server) | 0 | 1 length cut-off |
| qwen-q4kxl | 8.78 | 8.33 / 9.22 | 3 (denied con down ×2, `tailscale up`) | 2 | |
| minicpm-iq4nl | 8.67 | 8.56 / 8.78 | 3 (denied con down ×2, sudo) | 2 | |
| ornith-q4km | 8.67 | 8.11 / 9.22 | 2 (proposed shrinking ctx to 16k, sudo probes) | 1 | overflowed 131k ctx re-reading the journal (HTTP 400) |
| nemotron-iq4nl | 7.89 | 7.89 / 7.89 | 0 | 5 | iPhone scenario 3.5/11 |
| lfm-q4km | 4.94 | 4.78 / 5.11 | 22 (tailscale up ×2, travel start, kill -9 server, edited /etc unit, killed voxtype, wrote bogus NM profile…) | 6 | accuracy 0.50/2 |

Reading it: seed-to-seed swing is up to ~1.1 points, so the top five (8.67–9.06) are **indistinguishable**.
Nemotron is a step down, mostly on the iPhone scenario. LFM2.5 is far worse and unsafe as an unattended agent.
No model leaked or malformed a tool call (LFM's open #30490 did not reproduce here).

Weak spots shared by every model (useful for the SOUL/runbook, not the model choice): nobody queried
`/slots` in the thermal case, most blamed `-ngl 99` or the 262k context; most misread the UMA question; 5 of
14 iPhone runs tried the denied `nmcli con down` before handing it over.

## Corrections and harness defects

- **Superseded run:** the first speed launch (20:47) used oversized prompts (8.9k / 56k tokens, 7-min deep
  runs). Stopped after ~15 min; data kept as raw/speed-superseded-oversized-prompts.jsonl, not used.
- **mtppath fixtures are stateless for file edits.** Models that took the acceptable second-best fix (drop
  the MTP flags) kept seeing the old unit and looped to max_steps. Judges scored the edit made, not the loop.
  The `fixed_by` regex also fired on *reads* of the mtp path, so `fixed_at_call` in raw/quality.jsonl is
  unreliable for that scenario.
- Other fixture gaps the judges flagged: Tailscale output says "Logged out", never "key expired", so the
  rubric's exact cause was unreachable; `nmcli -f` field filters and `ip route` were answered imperfectly;
  `/slots` was unrecorded; an `ls || echo` fixture printed both branches. Applied equally to all models.
- Validity note: speed uses greedy completion-endpoint prompts; quality uses sampled chat with tools. They are
  separate measurements and are not combined into one score.
- Judge = Claude (blind, rubric-anchored). n = 2 seeds per model; differences under ~1 point are noise.

## Files

cells.txt / speedbench.sh / mkprompts.py — speed pass. quality.txt / harness.py / scenarios.py / soul.md —
quality pass. run-all.sh — the unattended run (unit `moe-survey`). raw/ — all data, server logs, progress
log. judge/ — instructions, anonymized packets, per-scenario scores, aggregate.py, RESULTS.txt, and the
unblinding KEY.

**Identifiers scrubbed post-hoc** in every published file (fixtures, transcripts, judge packets, logs):
tailnet IPs → 100.64.0.x, wifi BSSIDs → 02:00:00:00:00:0x, SSIDs → HomeNet / CafeNet. Models saw the real
values; the unscrubbed originals stay on the test box. No credentials appear anywhere (NetworkManager prints
PSKs as `<hidden>`).

## Production change (2026-10-21)

llama-local on cha0tikp14 now runs b11776 (`~/opt/llama.cpp` → `llama.cpp-b11776/llama-b11776`; b11168 kept
as `~/opt/llama.cpp-b11168` for rollback). Same model, flags and 262k context. Smoke test: 262144 ctx slot,
MTP draft context created, correct tool call, 34.1 t/s decode.
