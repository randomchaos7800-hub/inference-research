# cha0tikhome Infrastructure Runbook
**Last updated: 2026-06-04 (website stack + stale cloudflared rule documented)**
**Machine: Beelink EQI12 — 100.94.10.36 (Tailscale) / 10.0.0.166 (LAN)**

**Canonical private source:** `git@cha0tikforge:cha0tik/home-infra.git`

This file remains usable as an operator runbook, but future private infra updates should be made in `home-infra/runbooks/` first and mirrored here only as needed.
If this file and `home-infra` disagree, `home-infra` wins.

---

## Live Websites

All public sites route through: **cloudflared.service → nginx:8080 (localhost) → static files or upstream**

| Domain | Doc Root | Notes |
|---|---|---|
| dinovitale.com | /home/dino/www/dinovitale.com/ | Personal site |
| localfamouscoffee.com | /home/dino/www/localfamouscoffee.com/ | LFC — Stripe backend via localfamouscoffee.service |
| boundarylabs.org | /home/dino/www/boundarylabs.org/ | Boundary Labs site |
| cha0tik.com | /home/dino/www/cha0tik.com/ | Home lab front |
| localfamo.us | → localfamouscoffee.com | Redirect |

**If a site is down:** check (1) cloudflared.service, (2) nginx, (3) localfamouscoffee.service if LFC-specific.

**Known cleanup pending:** `kato-sms.dinovitale.com` in `~/.cloudflared/config.yml` still points to `:3001` (nothing runs there — kato-sms was retired). Harmless but stale; remove when next editing cloudflared config.

---

## Post-Reboot Checklist

Hand this file to Claude and say "run the reboot checklist." Claude reads this and brings everything back.

### Step 1 — Verify mounts

```bash
df -h / /mnt/jellyfin-media /mnt/jellyfin-backups
```

Both should be present. If missing:
```bash
sudo mount -a
```

| Mount | UUID | Notes |
|---|---|---|
| / | f2caf1c2-42d6-413c-8107-874e4dc4676b | |
| /mnt/jellyfin-media | 28905f09-164f-4e78-9253-763a6a083fdf | |
| /mnt/jellyfin-backups | 173f20e6-c8f1-49af-adf5-c6cee38b620 | |
| /mnt/backup | db7f838d-1491-476c-94be-97e012794ea4 | Removable — not always present, ignore if missing |

### Step 2 — System services

```bash
systemctl is-active tailscaled nginx postgresql jellyfin paperless-web paperless-worker paperless-scheduler vaultwarden adguardhome forgejo
```

All should return `active`. If any are failed:
```bash
sudo systemctl restart <service>
```

| Service | Purpose | Port |
|---|---|---|
| tailscaled | Tailscale VPN — SSH depends on this | — |
| ssh | SSH on Tailscale IP only (100.94.10.36:22) | 22 |
| nginx | Reverse proxy | 80/443 |
| postgresql | Database (paperless, etc.) | 5432 |
| jellyfin | Media server | 8096 |
| paperless-web | Document management | 8000 |
| paperless-worker | Paperless background worker | — |
| paperless-scheduler | Paperless cron | — |
| vaultwarden | Password manager | 8222 |
| adguardhome | DNS ad blocker | 3000/53 |
| forgejo | Local git forge — Tailscale only | 3002 |

**SSH note:** SSH listens on Tailscale IP only. If SSH is unreachable after reboot, tailscaled may have lost the race. Override is at `/etc/systemd/system/ssh.service.d/override.conf` — waits for tailscaled, restarts on failure. Usually self-heals within 30 seconds.

### Step 3 — User services (agents)

```bash
systemctl --user is-active harness.service harness-api.service mike.service mike-irc.service mike-irchighway.service cloudflared.service dashboard.service autoresearch.service localfamouscoffee.service tmux-main.service
```

All should return `active`. Restart any that aren't:
```bash
systemctl --user restart <service>
```

| Service | Purpose | Notes |
|---|---|---|
| harness.service | Frank scheduler daemon | Core |
| harness-api.service | Frank API server | Core — was formerly frank-api.service |
| mike.service | Mike AI — Discord + Telegram + Slack | Core |
| cloudflared.service | Cloudflare tunnel | Core |
| dashboard.service | Status dashboard on :8888 | Core |
| autoresearch.service | Mike autoresearch API on :8001 | Core |
| localfamouscoffee.service | Local Famous Coffee Stripe backend | Core |
| tmux-main.service | Persistent tmux session | QoL |

### Step 4 — Timers

```bash
systemctl --user is-active chronicle.timer cha0tikwiki-compile.timer pandorica-sync.timer pandorica-extract.timer morning-briefing.timer arxiv-sweep.timer daily-research-brief.timer overnight-status.timer recall-summarization.timer tower-watchdog.timer hourly-ops-check.timer nightly-context-sync.timer x-post-morning.timer x-post-afternoon.timer weekly-essay-brief.timer wiki-growth.timer mike-beat.timer mike-consolidation.timer mike-daily-report.timer mike-lighthouse.timer
```

All should return `active` (waiting, not running constantly).

| Timer | Schedule | Purpose | Output |
|---|---|---|---|
| morning-briefing.timer | 4:00 AM | Weather, services, disk, email, schedule | #brief |
| overnight-status.timer | 4:20 AM | Overnight error digest | #brief |
| arxiv-sweep.timer | 7:00 AM | cs.AI + cs.CL papers, top 5 summary | #brief |
| daily-research-brief.timer | 8:00 AM | 3-day arXiv synthesis | #brief |
| weekly-essay-brief.timer | Sun 6:00 PM | Article ideas from week's arXiv | #brief |
| wiki-growth.timer | Mon 6:00 AM | Write new wiki articles from arXiv | #brief |
| x-post-morning.timer | 6:00 AM | Write + post morning tweet | #x |
| x-post-afternoon.timer | 4:00 PM | Write + post afternoon tweet | #x |
| tower-watchdog.timer | Every 5 min | Tower :8010 reachability | #alerts on failure |
| hourly-ops-check.timer | Every hour | Service health, disk | #alerts on anomaly |
| nightly-context-sync.timer | 3:05 AM | Context sync | #alerts on failure |
| recall-summarization.timer | 2:30 AM | Ops log pattern review | #alerts |
| chronicle.timer | 2:00 AM | Nightly Chronicle synthesis | chronicle repo |
| pandorica-sync.timer | Every 30 min | Pandorica sync | — |
| pandorica-extract.timer | 2:00 AM | Pandorica extraction | — |
| cha0tikwiki-compile.timer | 9:00 PM | Wiki compile | — |
| mike-beat.timer | Per schedule | Mike heartbeat | — |
| mike-consolidation.timer | 3:00 AM | Mike memory consolidation | — |
| mike-daily-report.timer | Per schedule | Mike daily report | #mike |
| mike-lighthouse.timer | 2:00 AM | Mike LIGHTHOUSE extraction | — |

Mike IRC services (check separately):
```bash
systemctl --user is-active mike-irc.service mike-irchighway.service
```

### Step 5 — Tower (cha0tiktower — 100.120.50.35)

```bash
ssh dino@100.120.50.35 'systemctl --user is-active nemotron.service; ss -tulpn | grep ":8022 "; curl -sf http://localhost:8010/health; curl -sf http://localhost:8010/active'
```

Expected output:
```
active
tcp LISTEN ... 0.0.0.0:8022 ... llama-server ...
{"status":"ok","active":"nemotron",...}
{"active":"nemotron","url":"http://localhost:8022/v1","model":"nvidia_Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf",...}
```

If nemotron is not active:
```bash
ssh dino@100.120.50.35 'systemctl --user start nemotron.service'
```

**Nemotron is the active backend label** and the live serving path behind it is `nemotron.service`.

Current truth:
- `local-proxy` label: `nemotron`
- `nemotron.service`: owns port `8022`
- process on `8022`: `llama-server`
- model: `nvidia_Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf`
- `local-proxy.service`: owns port `8010` under user systemd
- `cha0tiktower` is inference-first; benchmarking and model testing are valid, but restoring fleet inference takes priority over experiments

`vllm-backend.service` may still exist on tower and may even be enabled, but it is not the active serving path while `nemotron.service` owns `8022`. Treat it as stale unless explicitly restoring a vLLM backend. `vllm-aeon.service` is inactive and should stay that way unless intentionally switching backends.

Proxy switch (if you ever need to change backend):
```bash
ssh dino@100.120.50.35 'proxy-switch nemotron'   # default
ssh dino@100.120.50.35 'proxy-switch deepseek-r1' # optional alternate on 8022
ssh dino@100.120.50.35 'proxy-switch aeon'        # optional alternate on 8023
ssh dino@100.120.50.35 'proxy-switch openrouter'  # fallback
```

Tower UFW is active. Verify after reboot:
```bash
ssh dino@100.120.50.35 'sudo ufw status'
```
Expected: active, default deny incoming. Key rules: tailscale0 open, 8010/8022 allowed from LAN. SSH listens on Tailscale only.

If UFW is inactive after reboot:
```bash
ssh dino@100.120.50.35 'sudo ufw --force enable'
```

### Step 6 — Quick sanity checks

```bash
# Dashboard accessible
curl -sf http://100.94.10.36:8888/api/status | python3 -m json.tool | head -20

# Tower inference reachable
curl -sf http://100.120.50.35:8010/health

# Mike logs
journalctl --user -u mike.service -n 20 --no-pager
```

**Live website smoke test** (all should return 200):
```bash
for domain in dinovitale.com localfamouscoffee.com boundarylabs.org cha0tik.com; do
  code=$(curl -sf -o /dev/null -w "%{http_code}" -L "https://$domain" 2>/dev/null || echo "ERR")
  echo "$domain: $code"
done
```

If any return ERR or non-200:
1. Check nginx: `systemctl is-active nginx`
2. Check cloudflared: `systemctl --user is-active cloudflared.service`
3. Check cloudflared logs: `journalctl --user -u cloudflared.service -n 30 --no-pager`
4. If LFC-specific: `systemctl --user is-active localfamouscoffee.service`

---

## What Is NOT Running (by design)

| Service | Status | Reason |
|---|---|---|
| hermes-gateway.service | RETIRED 2026-05-27 | Nuked + fully cleaned 2026-06-04 (dirs, service, legacy scripts using its send tools, etc.) |
| harness-kato.service | Masked 2026-05-27 | SlackInterface API broke; #kato-comms archived; Kato cron role replaced by standalone scripts |
| harness-sabrina.service | Inactive | Sabrina retired |
| vllm-genesis.service | Stopped | Replaced by nemotron.service (llama.cpp) 2026-05-20 |
| vllm-aeon.service | Stopped/disabled | Replaced; conflicts for VRAM |
| vllm-backend.service | Optional/disabled | DeepSeek-R1 alternate backend slot on tower; not enabled by default |
| jubal.service | Inactive | In progress / on hold |
| cj.service | Masked | RETIRED 2026-05-09 |
| harness-cj.service | Masked | RETIRED 2026-05-09 |
| morty.service | Masked | RETIRED 2026-05-09 |
| harness-morty.service | Masked | RETIRED 2026-05-09 |
| dave.service | Masked | RETIRED 2026-05-09 |
| navidrome.service | Inactive | Deprecated |
| ollama | Inactive | Not in use |

---

## Cron Schedule

All tasks run as standalone scripts via systemd timers (not harness scheduler). Scripts live in `/home/dino/crons/`. If a timer isn't firing, check the script directly:

```bash
systemctl --user status <timer-name>
journalctl --user -u <script-name>.service -n 30 --no-pager
```

Harness schedule.toml still exists but all cron tasks have `enabled = false` — the harness scheduler only drives agent interactions now, not periodic tasks.

Crontab also runs (check `crontab -l`): backups at 3AM, perf-log at 6AM, site-updater hourly, mike-observer every 15min, inference-status every 15min, agent-smoke every 15min.

---

## Slack Channels

| Channel | Purpose |
|---|---|
| #brief | Daily reads: morning briefing, overnight status, arxiv, research brief, weekly essay, wiki growth |
| #alerts | Infra only, fires on failure: tower watchdog, ops check, nightly sync, recall summary |
| #x | X post confirmations (morning + afternoon) |
| #mike | Mike's channel |
| #mike-live | Mike live stream |

Archived (2026-05-27): #kato-comms, #ops-log, #cj-comms, #ai-news, #ai-repos, #x-queue, #groceries, #finance

---

## Key File Locations

| What | Where |
|---|---|
| Forgejo UI | http://cha0tikhome.tailc83c25.ts.net:3002/ (admin: dino, pw: `vault get forgejo_admin_password`) |
| Forgejo SSH | `git@cha0tikforge:cha0tik/<repo>.git` — canonical form for all local repos |
| Forgejo repo root | /var/lib/forgejo/data/forgejo-repositories |
| Forgejo backup | /mnt/jellyfin-backups/forgejo/ (nightly 3:15 AM via /etc/cron.d/forgejo-backup) |
| Shared org | cha0tik (local) / randomchaos7800-hub (GitHub mirror) |
| Shared memory | /home/dino/citadel |
| Cron scripts | /home/dino/crons/ |
| Cron lib (slack, inference) | /home/dino/crons/lib/ |
| Frank harness | /home/dino/harness/ |
| Frank personas | /home/dino/harness/personas/ |
| Mike | /home/dino/mike/ |
| Local Famous Coffee | /home/dino/www/localfamouscoffee.com/ |
| Dashboard | /home/dino/dashboard/main.py |
| Dashboard config | /home/dino/dashboard/monitor.yaml |
| Vault | ~/.vault/secrets.age (key: ~/.vault/key.txt) |
| Gmail check | ~/.kato/scripts/gmail-check.sh |
| Weather | ~/.kato/scripts/get-weather.sh |
| Tower plug | /home/dino/scripts/tower-plug.py |
| Tower nemotron launcher | /home/dino/bin/nemotron-start.sh (on tower) |
| Tower proxy config | /home/dino/local-proxy/config.toml (on tower) |
| SSH override | /etc/systemd/system/ssh.service.d/override.conf |
| fstab | /etc/fstab |
