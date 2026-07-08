# Ornith-1.0-35B (Tower)

Production model as of 2026-06-27. Deployed as GGUF Q4_K_M (llama.cpp) 2026-06-26, upgraded to AEON NVFP4 (vLLM 0.23) 2026-06-27.

See [aeon-nvfp4-prod.md](aeon-nvfp4-prod.md) for current production config.
See [prod-trial.md](prod-trial.md) for deployment log.

## Verdict

[langchain-brutal-verdict.md](langchain-brutal-verdict.md) — full receipts from 2026-06-25 GGUF eval.

**Summary:** 56/66 (84.8%) on LangChain tool-use suite. 100% typewriter (both variants). NVFP4 re-run pending.

## Speed benchmarks

| Suite | Date | Backend | Peak gen t/s |
|---|---|---|---|
| GGUF direct :8030 | 2026-06-25 | llama.cpp cuda120-nographs | ~130 t/s |
| GGUF prod :8010 | 2026-06-26 | llama.cpp via proxy | 37–93 t/s (warming) |
| NVFP4 prod :8010 | 2026-06-27 | vLLM 0.23 via proxy | 92–124 t/s warm |

Canonical 512-gen: **87 t/s** (via :8010, June 27).

Context scaling (NVFP4, via :8010, June 27):

| Prompt tokens | Gen t/s |
|---|---|
| 1,227 | 87.2 |
| 5,307 | 84.0 |
| 10,827 | 23.1 |
| 21,627 | 21.6 |
| 43,227 | 46.2 |

HumanEval: **43.9% (72/164)** — markdown fence leakage in completions is primary failure mode.

## Article

[langchain-brutal-article.md](langchain-brutal-article.md) — narrative recap for publication.

## Re-run LangChain eval (NVFP4)

```bash
python3 /home/dino/inference-research/tower/ornith/langchain-brutal-eval.py \
  --endpoint http://tower:8010/v1/chat/completions \
  --model local \
  --output /home/dino/logs/model-tests/ornith-nvfp4/langchain-brutal-eval.json
```

## Receipts (versioned)

| File | Contents |
|---|---|
| [langchain-brutal-eval.py](langchain-brutal-eval.py) | Harness |
| [langchain-brutal-eval-ornith.json](langchain-brutal-eval-ornith.json) | Ornith LangChain eval (GGUF) |
| [langchain-brutal-eval-deepseek-v3.2.json](langchain-brutal-eval-deepseek-v3.2.json) | DeepSeek V3.2 head-to-head |
| [humaneval-results.json](humaneval-results.json) | HumanEval 72/164 (GGUF) |
| [suite-20260625-170030.json](suite-20260625-170030.json) | Speed suite — GGUF direct :8030 |
| [suite-20260626-prod.json](suite-20260626-prod.json) | Prod bench day 1 — GGUF via :8010 |
| [suite-20260627-042048.json](suite-20260627-042048.json) | Prod bench day 2 — NVFP4 via :8010 warm |
| [bigctx-20260626.json](bigctx-20260626.json) | Context scaling 1K–32K (NVFP4) |
| [canonical-512.json](canonical-512.json) | Canonical 512-gen (87 t/s) |
| [aeon-nvfp4-prod.md](aeon-nvfp4-prod.md) | NVFP4 production config + KV cache notes |