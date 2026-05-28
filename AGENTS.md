# Dino's Home Lab — Codex Context
**Last updated: 2026-05-27**

**Canonical private source:** `git@cha0tikforge:cha0tik/home-infra.git`

For machine roles, runbooks, recovery procedures, service placement, and infra backlog:
- write new private infra knowledge in `home-infra` first
- treat this file as operator context and summary, not the long-term canonical repo
- if this file and `home-infra` disagree, `home-infra` wins

You are working in Dino Vitale's home lab. Dino is a systems architect who does not write code himself — you implement, he designs. Be direct, no hedging, execute or specify exactly.

---

## Machines

| Host | IP (Tailscale) | IP (LAN) | Role |
|---|---|---|---|
| cha0tikhome | 100.94.10.36 | 10.0.0.166 | Processes, agents, monitoring — you are here |
| cha0tiktower | 100.120.50.35 | 10.0.0.x | Inference-first GPU node; models, harnesses, benchmarking, and research testing live here, but fleet inference is the primary function (RTX 5060 Ti 16GB) |
| cha0tikmac | 100.83.149.28 | — | Mac workstation / mobile operator client (MacBook Air M4) |

SSH to tower: `ssh dino@100.120.50.35` (key auth, Tailscale only, no password).
Tower sudo requires password — cannot be done non-interactively.

---

## Active Services

| Service | Systemd Unit | Port | Notes |
|---|---|---|---|
| Harness | `harness.service` + `harness-api.service` (user) | 8890 (Tailscale-bound) | Agentic harness, `/home/dino/harness/` |
| Mike | `mike.service` + `mike-irc.service` + `mike-irchighway.service` (user) | — | AI agent, Discord/Telegram/Slack/IRC, `/home/dino/mike/` |
| Forgejo | `forgejo.service` (system) | 3002 (Tailscale-bound) | Local collaboration forge, `/var/lib/forgejo/` |

---

## RETIRED — Do Not Restart

These are masked or dead. Do not enable, start, or reference as active:

| Agent | Retired | Notes |
|---|---|---|
| Kato | 2026-05-21 | `~/.kato/` preserved as archive only |
| CJ Craig | 2026-05-09 | Masked, absorbed by Hermes |
| Morty | 2026-05-09 | Masked, archived |
| Dave CFO | 2026-05-09 | Masked, archived |
| Frank | 2026-05-27 | Name retired; code preserved as archive; harness infrastructure continues as descriptive service |
| Hermes | 2026-05-27 | Nuked; old state is stale and not authoritative; fresh reinstall planned |
| Sabrina | 2026-05-27 | Not running; do not restart |

The `harness-kato.service` and `harness-sabrina.service` units in the INFRA_RUNBOOK are stale — Kato is retired.

---

## Inference Stack

All local inference routes through the tower proxy. Never hardcode backend ports.

| Component | Host | Port | Notes |
|---|---|---|---|
| local-proxy | cha0tiktower | 8010 | Single entry point — use this always |
| Nemotron (llama.cpp) | cha0tiktower | 8022 | Active production backend |
| DeepSeek-R1 (vLLM) | cha0tiktower | 8022 | Optional alternate backend slot; not enabled by default |
| AEON (vLLM) | cha0tiktower | 8023 | Optional alternate backend; do NOT run alongside the active 8022 backend if VRAM conflicts |

Model alias through proxy: `"local"`. Real model name from `/v1/models` returns `local`; use `/active` for the actual model ID.

Switch backends: `proxy-switch nemotron|deepseek-r1|aeon|openrouter` on tower.

Operational priority:
- `cha0tiktower` is inference-first. Keep `:8010` stable for the fleet.
- Model benchmarking, backend experimentation, and harness staging on tower are allowed, but they are secondary to production inference continuity.
- Prefer headless/service operation over desktop-session behavior on tower.

---

## Key Services (cha0tikhome)

```bash
# System services
tailscaled nginx postgresql jellyfin paperless-web paperless-worker paperless-scheduler vaultwarden adguardhome cloudflared

# User services
harness-api.service mike.service mike-irc.service mike-irchighway.service
autoresearch.service tmux-main.service

# User timers
chronicle.timer cha0tikwiki-compile.timer pandorica-sync.timer
claude-token-refresh.timer mike-beat.timer mike-consolidation.timer
mike-daily-report.timer mike-lighthouse.timer pandorica-extract.timer
```

`hermes-gateway.service` unit is gone. Hermes was nuked on 2026-05-27; do not treat any prior Hermes runtime, monitor, or cron state as live.

---

## Cron Jobs (system crontab, dino user)

| Schedule | Job |
|---|---|
| 3:00 AM | mike backup, system backup, vault backup (includes vault key → Google Drive) |
| 3:10 AM | www backup |
| 3:20 AM | repo backup to /mnt/jellyfin-backups/repos/ |
| 4h | Claude OAuth keepalive |
| 6:00 AM | perf-log.sh (benchmarks tower proxy) |
| Hourly | site-updater.py (Substack RSS → dinovitale.com) |
| Every 15 min | mike_observer.py, update-inference-status.py |
| Mon 7:00 AM | generate-weekly-recap.py |

---

## Key File Locations

| What | Where |
|---|---|
| Vault (secrets) | `~/.vault/secrets.age` — age-encrypted |
| Vault key | `~/.vault/key.txt` |
| Vault CLI | `~/.vault/vault.sh get <key>` |
| Frank | `~/harness/` |
| Mike | `~/mike/` |
| Citadel shared memory | `~/citadel/` |
| Local Forgejo UI | `http://cha0tikhome.tailc83c25.ts.net:3002/` |
| Local Forgejo repo root | `/var/lib/forgejo/data/forgejo-repositories/` |
| Local Forgejo org | `cha0tik` |
| Wiki | `~/cha0tikwiki/` |
| Website | `~/www/dinovitale.com/` |
| Tower plug script | `~/scripts/tower-plug.py` (Kasa HS103P2 at 10.0.0.30) |
| Weather script | `~/.kato/scripts/get-weather.sh` (still works, Kato retired but script survives) |
| Gmail check | `~/.kato/scripts/gmail-check.sh` (same) |
| Perf logs | `~/logs/perf/` |
| Backups | `/mnt/jellyfin-backups/` |
| Media | `/mnt/jellyfin-media/` |
| INFRA_RUNBOOK | `~/INFRA_RUNBOOK.md` (partially stale — see below) |

**INFRA_RUNBOOK.md is stale as of 2026-05-09.** Kato retirement and security hardening happened after that date. Trust this file over the runbook for agent status.

---

## Security Posture

- SSH listens on Tailscale IP only (`100.94.10.36:22`), `PasswordAuthentication no`, `PermitRootLogin no`
- UFW default deny-incoming on both machines
- Vault is age-encrypted; key never committed to git
- Cloudflare tunnel exposes only nginx (web) and port 3001 — no agent APIs are public
- Known open issues: tower inference ports bind to `0.0.0.0` (UFW-protected but not ideal); AdGuard admin on `0.0.0.0:3000`

---

## Slack Channels

| Channel | Purpose |
|---|---|
| #ops-log | Automated alerts, health checks (anomalies only) |
| #kato-comms | Was Kato's channel — Hermes morning briefing posts here |
| #ai-news | AI news digest |
| #mike | Mike's channel |
| #drafts | Content drafts |

---

## Conventions

- Local inference: always use `http://100.120.50.35:8010/v1` as base URL, model `"local"`
- Never hardcode tower backend ports (8022, 8023) in agent configs
- Secrets: read from vault (`~/.vault/vault.sh get <key>`), never hardcode
- File-based config over databases where possible
- Systemd user services: `systemctl --user` for dino's agents; `sudo systemctl` for system services
- `citadel` is shared memory, not the local forge
- Local collaboration forge is Forgejo at `http://cha0tikhome.tailc83c25.ts.net:3002/`
- Git repos: `~/harness`, `~/mike`, `~/citadel`, `~/.claude` (operator context, syncs nightly to GitHub)
