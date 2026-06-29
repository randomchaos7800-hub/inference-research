# Ornith production (2026-06-27)

Fleet inference on `:8010` → **AEON Ornith NVFP4** (vLLM 0.23). Canonical doc: `home-infra/research/inference/tower/ornith/aeon-nvfp4-prod.md`.

## Live state

| Item | Value |
|---|---|
| Proxy backend | `ornith` |
| Backend | `ornith-backend.service` → `:8030` |
| Engine | vLLM 0.23, fp8 KV, 131072 ctx |
| Client | `http://100.120.50.35:8010/v1`, model `local` |

## GGUF baseline eval

LangChain brutal **56/66 (84.8%)** — GGUF only (2026-06-25). NVFP4 not re-run.