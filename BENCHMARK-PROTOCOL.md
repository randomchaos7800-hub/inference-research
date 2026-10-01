# Benchmark Protocol

How inference measurements are taken here, and why each rule exists. Every rule
below was written because breaking it produced a wrong number that we published
to ourselves and had to retract. The citations are to our own runs.

This is the measurement protocol. `tower/experiment-mode.md` is a separate,
machine-specific operational lockout (keeping production traffic off the cards
during a run) from the tower era — it says how to free the hardware, not how to
measure it.

---

## 1. Throughput is not a property of the software until you state the clock

On a power- or thermally-limited part, the same binary doing the same work
returns different numbers depending on how long it has been running.

**cha0tikp14, 2026-10-01.** The APU boosts to ~50 W at ~2200 MHz for about 25
seconds, then settles to a sustained ~36 W at ~1050 MHz. A ROCm cell measured
across five runs fell 19.95 → 15.16 t/s (−24%) with no software cause: a server
restart did not reset it, and RSS was identical across restarts. Package
temperature plateaued at 68–72 °C, nowhere near a limit — and the Vulkan control
ran *hotter* (80 °C) without throttling at all. It was the package power budget.

**Rules**
- **Discard the boost window.** On this class of hardware, the first ~30 s of GPU
  load is not a rate the machine can hold. Report the sustained tail.
- **Never report a mean that spans both regimes.** It is a number the hardware
  never produced. Report boost and sustained separately, or sustained only.
- **Cold-start every cell with an equal idle gap** so no cell inherits a budget
  the previous one spent.
- **Record machine state with every data point**: GPU clock, package power,
  temperature, and what else was on the CPU. A throughput figure without the
  clock beside it cannot be compared to anything.

## 2. Order is a variable until you prove it is not

**Same run.** ROCm was measured first with a fresh boost budget; Vulkan ran
immediately after, already in sustained mode. That single ordering produced
"Vulkan +23%". Measured sustained-vs-sustained the real figure was **+41%** —
and it then matched the loaded-context cells (+40.7%), which had been
both-sustained all along, to within half a percent.

**Rules**
- **Interleave and repeat.** Never run all of condition A then all of B.
- Residual drift then shows up as disagreement *between repetitions* rather than
  as a silent bias in favour of whoever went first.

## 3. One variable, and prove it is one

- **Same commit.** A backend comparison against a differently-versioned binary
  measures the version too. (Here: `07fc586e3` for all three binaries.)
- **Same compiler.** If the comparison binaries differ in toolchain, build a
  control that isolates it. We built Vulkan twice — Clang 22 and GCC 11.4 — so
  backend and compiler could be separated rather than assumed independent.
- **Same model file.** Two GGUFs that differ only in an MTP layer are two
  different experiments. Pointing documented flags at the wrong file cost a run.
- **Same everything else**: context length, thread count, governor, AC vs
  battery, offload depth.

## 4. Separate the metrics that move in opposite directions

Decode is memory-bandwidth bound; prefill is compute bound. **They can and do
split.** In the matched run ROCm lost decode by 41% and *won* prefill by 5.7%. A
single combined tokens/sec figure would have reported neither.

- Report **prefill and decode separately, always.**
- Report **clean and loaded-context separately.** The loaded number is the one
  that governs real sessions; the clean number is the headline that flatters.
- A prefill figure from a short prompt is launch overhead, not prefill. Measure
  it at a realistic prompt length (we use ~5k tokens).

## 5. Check the sample before you believe the rate

A cell reported ~20.8 t/s off **two generated tokens** — the model hit EOS
immediately on a repetitive prompt. The rate was arithmetically fine and
meaningless.

**Rules**
- Set `ignore_eos` for throughput cells, and **assert the token count** in the
  output. A cell whose `n_pred` is not what you asked for is void.
- Keep void cells in the raw file, marked. Deleting them hides that the protocol
  had a hole.

## 6. Run enough times to see the shape, and report the spread

Averaging hides the mechanism. The ROCm power story was only visible as a
*monotonic decline across the sequence*; the mean alone (17.46) described nothing
real. Conversely, speculative decoding is content-dependent and genuinely noisy:
MTP-on varied ±6.6% run to run while MTP-off was deterministic to ±0.09%.

- **≥5 runs minimum, 12 for anything published**, and report min–max and sd, not
  just the mean.
- **Report the sequence, not just the statistics,** whenever a cell is not flat.
- A single-run A/B against a speculative-decoding build can be off by 17%.

## 7. Quiet the box, and verify it stayed quiet

A browser was consuming ~19% CPU across an entire measurement session. On a part
where CPU and GPU share one power budget, background load is not merely noise —
it is throughput you are measuring away.

- Kill browsers and user applications; drop caches; verify idle immediately
  before each cell **and record the top process with each data point.**
- Warm up twice, unscored, after dropping caches — otherwise an mmap-based
  backend eats page-fault cost that a copy-based one does not.

## 8. A failure is a result

ROCm could not load an 17.1 GB model at a 16 GiB carve-out at all, and could not
run MTP at any offload depth there. Those are findings about the platform, not
gaps in the table.

- Record **why** it failed, with the error text, in the results file.
- Re-verify failures under the final protocol rather than citing an earlier run.
- State the constraint that forced any workaround — a partial-offload number is
  not a full-offload number, and the reader needs to know which they are reading.

## 9. Orchestration hygiene (these cost real time)

- `pgrep -f` / `pkill -f` match **any** command line containing the pattern,
  including the shell running your own command and orphaned watchers from
  earlier runs. Use `pgrep -x <binary>` or the bracket trick (`[l]lama-server`).
- **The bracket trick protects the pattern, not the command.** `pkill -f
  "[l]lama-server"` still kills your own shell if anything *else* in the same
  command line contains the literal string — e.g. a later
  `~/opt/llama.cpp/llama-server --version`. Put the kill in its own invocation,
  separate from anything that names the target.
- A local `timeout` that kills an ssh client **does not kill the remote
  command.** Orphaned watchers linger and will be matched by their successors —
  one such orphan made a watcher wait forever on an install that had already
  finished.
- Prefer a sentinel line in an output file over process-matching to decide that
  a run is done.
- Kill stray watchers before measuring. They wake up mid-run.

---

## Reporting checklist

Every published figure carries: commit, compiler, backend, model file and quant,
offload depth, context length, thread count, governor, power source, carve-out,
kernel, run count, min–max, sd, whether it is boost or sustained, and the GPU
clock and package power it was produced at. Anything missing is a caveat stated
in the text, not an omission.
