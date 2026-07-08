# Tower Research Programs

Working index for the tower (2× RTX 5060 Ti) research programs. Newest and most
consequential first — the one-line results live in [../RESULTS.md](../RESULTS.md).

## Programs

- [ornith/](ornith/) — **Ornith-1.0-35B** tool-use eval (LangChain brutal suite) — current production model
- [genesis/](genesis/) — **production replication guide** for Qwen3.6-27B on Genesis-patched vLLM (flags, install, ops)
- [nemotron/](nemotron/) — Nemotron 3 Nano 30B tool-calling + TRT-LLM NVFP4
- [gdn-blackwell/](gdn-blackwell/) — the GDN architecture wall on SM_120; SGLang vs vLLM
- [lucebox/](lucebox/) — speculative decoding + hardware-vs-model attribution under hard locks
- [benchmarks/](benchmarks/) — shared benchmark tooling; MTP batched-tokens test
- [frank/](frank/) — autoresearch sweep (TSV receipts, loop-rebuild comparison)
- [deepseek14b/](deepseek14b/) — DeepSeek 14B autoresearch sweep
- [prism-pro/](prism-pro/) — Prism Pro autoresearch sweep

## Method

- [experiment-mode.md](experiment-mode.md) — the protocol every benchmark runs under:
  production stopped **and disabled**, VRAM drained and verified, one variable at a time.

## How to read a program directory

1. `README.md` — what was tested and the verdict, links first.
2. `*-verdict.md` / `*-VERDICT.md` — the claims.
3. `*.tsv`, `*.json`, `*.log` — the raw receipts behind the claims.
4. `*.py` — the exact driver that produced them.
