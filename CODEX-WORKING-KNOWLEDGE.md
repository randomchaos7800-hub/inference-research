# Codex Entrypoint

**Read first:** `~/citadel/shared/PROTOCOL.md`

All operating rules live in citadel. This file is Codex-specific only.

## Embedded Launch

- Default: `codex` → `~/scripts/codex-embedded`
- `HOME=/home/dino`, `CODEX_HOME=/home/dino/snap/codex/34`
- Mollydog for sudo: `~/scripts/mollydog.sh` — phrase: "mollydog is running"
- Full embedded ops: `~/CODEX-EMBEDDED-OPS.md`

## Env Vars (set by launcher)

```
CITADEL_ROOT=/home/dino/citadel
CITADEL_PROTOCOL=/home/dino/citadel/shared/PROTOCOL.md
REAL_HOME=/home/dino
DINO_HOME=/home/dino
```

## Codex-Specific References

- Citadel entrypoint: `~/citadel/agents/codex/ENTRYPOINT.md`
- Case law: `~/citadel/shared/case-law.md`