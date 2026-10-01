# Inference Research — Boundary Labs

**Local inference research on consumer NVIDIA hardware — verdicts, replication
guides, and the raw run logs (215+ benchmark runs) behind every claim.**

This repo is the receipts: each research program's verdict document plus the raw
TSVs, JSONs, and logs it was derived from. The narrative version — an interactive
timeline of the 30+ milestone experiments — lives at
**[localfamo.us](https://localfamo.us)**, and live production numbers are on
**[dinovitale.com/benchmarks](https://dinovitale.com/benchmarks.html)**.

## The short version

One person, two machines, five eras. From 10.4 tok/s on a mini-PC CPU to a
35B model running a production trial at ~101 tok/s on two consumer GPUs:

| Era | tok/s | What happened |
|---|---|---|
| **CPU** | 10.4 | Beelink mini-PC, i5-1235U, Gemma-4 26B, chronic swap thrashing |
| **Tower** | 32 → 107 | RTX 5060 Ti ×1 then ×2 — GPU offload, SWA discovery, the PCIe ceiling |
| **Genesis** | 22 → 88 | GDN architecture wall in llama.cpp; Genesis-patched vLLM + MTP n=3 broke it open |
| **Nemotron** | 117.6 | Mamba/SSM hybrid MoE — new hardware peak on llama.cpp |
| **Ornith** | ~130 | 35B GGUF beats DeepSeek V3.2 on sequential tool composition (loses overall by 1 pt); NVFP4 production trial at 131K ctx |

**Currently in production:** Genesis — Qwen3.6-27B INT4, vLLM — restored as default 2026-07-03 after the Ornith trial (2026-06-26 → 2026-07-03). ~97 tok/s warm, [verified 2026-07-08](tower/genesis/warm-20260708.json). Ornith numbers stand as dated campaign results.

## Start here

- **[RESULTS.md](RESULTS.md)** — every research program, its headline number, and a link to the verdict
- **[HARDWARE.md](HARDWARE.md)** — the exact rigs, so "consumer hardware" is a checkable claim
- **[tower/genesis/](tower/genesis/)** — full production replication guide (flags, install, ops)
- **[BENCHMARK-PROTOCOL.md](BENCHMARK-PROTOCOL.md)** — how measurements are taken here: boost vs sustained clocks,
  order effects, single-variable discipline, what every published figure must carry. Each rule is there because
  breaking it produced a number we had to retract
- **[tower/experiment-mode.md](tower/experiment-mode.md)** — tower-era operational lockout (freeing the GPUs for a run)
- **[papers/](papers/)** — *Commodity Hardware for Persistent AI Companions* and
  *What the Score Measured: Failure Attribution in an Agent Memory Evaluation*
  (Vitale & Guo, Zenodo preprint, [10.5281/zenodo.22980060](https://doi.org/10.5281/zenodo.22980060))
- **[p14-krackan/](p14-krackan/)** — ROCm vs Vulkan on an AMD Krackan Point iGPU: the compiler beats the
  backend, and ROCm loses on power, not compute
- **[longmemeval/](longmemeval/)** — does agent memory survive a model change? Harness, three-reader run,
  instrumented rerun, four-rater blind judging. Written up in [*What the Score Measured*](https://doi.org/10.5281/zenodo.22980060)

## How to read the receipts

Each program directory under [`tower/`](tower/) contains the experiment driver
(Python), the raw outputs (TSV / JSON / logs), and a verdict document. The verdicts
make claims; the raw files are the evidence. Nothing is cherry-picked — failed runs
and dead ends are committed alongside the wins, because the failures are usually
where the useful information is.

Internal endpoints in older logs are anonymized (`tower`, `home-server`,
`tailscale-host`); the numbers are untouched.

## Who

[Dino Vitale](https://dinovitale.com) — Boundary Labs.
Writing at [dinovitale.com](https://dinovitale.com), longer essays on
[Substack](https://dinovitale.substack.com).
