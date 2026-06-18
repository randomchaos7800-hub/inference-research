# Dino's Home Lab — Agent Bootstrap
**Last updated: 2026-06-17**

You are working in Dino Vitale's home lab. Dino is a systems architect who does not write code — you implement, he designs. Be direct. Execute or specify exactly.

## Canonical Protocol — Read First

**All collab agents (Claude Code, Codex, Grok, Hermes) follow the same rules:**

```
~/citadel/shared/PROTOCOL.md
```

Do not maintain a parallel copy of operating rules. If this file and citadel disagree, **citadel wins** — then verify live state.

Quick references in citadel:
- `shared/topology.md` — vault, forge, GitHub, inference paths
- `shared/infrastructure.md` — machines and services
- `shared/case-law.md` — durable failure patterns
- `shared/agent-entrypoints.md` — per-agent entrypoints

Private infra runbooks: `git@cha0tikforge:cha0tik/home-infra.git` (if citadel and home-infra disagree on infra, home-infra wins)

## Grok-Specific

- Entrypoint: `~/citadel/agents/grok/ENTRYPOINT.md`
- Runtime: `~/.grok/`
- Commit prefix in citadel: `grok:`

## One Vault, One Forge, One GitHub

| System | Path |
|---|---|
| Secrets | `~/.vault/vault.sh get <key>` |
| Knowledge | `~/citadel/` |
| Local forge | `git@cha0tikforge:cha0tik/<repo>.git` (push first) |
| GitHub mirror | `git@github.com:randomchaos7800-hub/<repo>.git` |
| Inference | `http://100.120.50.35:8010/v1`, model `local` |