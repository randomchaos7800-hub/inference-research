# Ornith production (2026-06-27)

Fleet inference on `:8010` → **AEON Ornith NVFP4** (vLLM 0.23). See [aeon-nvfp4-prod.md](aeon-nvfp4-prod.md) for full config.

## Live state

| Item | Value |
|---|---|
| Proxy backend | `ornith` |
| Backend service | `ornith-backend.service` (port `:8030`) |
| Engine | vLLM 0.23, Marlin + flashinfer_b12x, fp8 KV |
| Context | 131072 tokens |
| Client path | `http://tower:8010/v1`, model `local` |
| Verify | `curl http://tower:8010/active` |

## Prior trial (2026-06-26)

GGUF Q4_K_M via llama.cpp — rolled forward to AEON NVFP4 after native x86 port validated.

## Rollback

```bash
ssh dino@tower '/home/dino/bin/proxy-switch openrouter'
ssh dino@tower 'cp /home/dino/bin/ornith-llama-start.sh.bak /home/dino/bin/ornith-start.sh && systemctl --user restart ornith-backend'
ssh dino@tower '/home/dino/bin/tower-return-prod'
```

## Rationale

- LangChain brutal: **56/66 (84.8%)** on both GGUF (2026-06-25) and AEON NVFP4 (2026-06-28)
- AEON uncensored build; native vLLM tooling; ~101 tok/s short-gen
- Context parity with GGUF requires **`--kv-cache-dtype fp8`** (BF16 KV falsely capped at 32k)