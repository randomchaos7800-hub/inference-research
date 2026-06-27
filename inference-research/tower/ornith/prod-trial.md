# Ornith production trial (2026-06-26)

Fleet inference on `:8010` is pointed at **Ornith-1.0-35B Q4_K_M** for a multi-day soak.

## Live state

| Item | Value |
|---|---|
| Proxy backend | `ornith` |
| Backend service | `ornith-backend.service` (port `:8030`) |
| Engine | llama.cpp `build-cuda120-nographs`, layer-split dual GPU |
| Context | 131072 tokens |
| Client path | `http://100.120.50.35:8010/v1`, model `local` |
| Verify | `curl http://100.120.50.35:8010/active` |

## Rollback

```bash
ssh dino@100.120.50.35 '/home/dino/bin/tower-return-prod'   # restores genesis
# or
ssh dino@100.120.50.35 '/home/dino/bin/proxy-switch openrouter'  # cloud failover
```

## Rationale

LangChain brutal eval (2026-06-25): **56/66 (84.8%)**, 100% on typewriter suites, ~127 tok/s short-gen.
DeepSeek V3.2 via OpenRouter scored 57/66 but at ~22s/case and cloud cost.

## Review target

Re-evaluate ~2026-06-30. Keep if agent tool-use and latency hold in real fleet traffic; roll back to genesis if regressions appear.