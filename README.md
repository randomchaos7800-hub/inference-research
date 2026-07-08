# Inference Research — Boundary Labs

**215+ real inference experiments on consumer NVIDIA hardware. Every model, every
quantization, every failure — with the raw logs to back it.**

This repo is the receipts. The narrative version lives at
**[localfamo.us](https://localfamo.us)** (interactive timeline of every experiment),
and live production numbers are on
**[dinovitale.com/benchmarks](https://dinovitale.com/benchmarks.html)**.

## The short version

One person, two machines, five eras. From 10.4 tok/s on a mini-PC CPU to a
35B model in production at ~101 tok/s (124 peak) on two consumer GPUs:

| Era | tok/s | What happened |
|---|---|---|
| **CPU** | 10.4 | Beelink mini-PC, i5-1235U, Gemma-4 26B, chronic swap thrashing |
| **Tower** | 32 → 107 | RTX 5060 Ti ×1 then ×2 — GPU offload, SWA discovery, the PCIe ceiling |
| **Genesis** | 22 → 88 | GDN architecture wall in llama.cpp; Genesis-patched vLLM + MTP n=3 broke it open |
| **Nemotron** | 117.6 | Mamba/SSM hybrid MoE — new hardware peak on llama.cpp |
| **Ornith** | ~130 | 35B GGUF beats DeepSeek V3.2 on tool-use; NVFP4 in production, 131K ctx |

**Currently in production:** Ornith-1.0-35B-AEON-Ultimate — ~101 tok/s warm, 124 peak.

## Start here

- **[RESULTS.md](RESULTS.md)** — every research program, its headline number, and a link to the verdict
- **[HARDWARE.md](HARDWARE.md)** — the exact rigs, so "consumer hardware" is a checkable claim
- **[tower/genesis/](tower/genesis/)** — full production replication guide (flags, install, ops)
- **[tower/experiment-mode.md](tower/experiment-mode.md)** — the protocol every benchmark runs under
- **[papers/](papers/)** — *Commodity Hardware for Persistent AI Companions* (Zenodo preprint)

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
