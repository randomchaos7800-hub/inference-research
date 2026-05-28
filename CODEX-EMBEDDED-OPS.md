# Codex Embedded Ops Profile

This file defines the practical operating baseline for Codex sessions on `cha0tikhome`.

## Goal

Codex should behave like an embedded systems operator on this box, not a read-only advisor.

## Required Access

Codex should be able to read and operate on:

- `/home/dino/**`
- `/etc/**`
- `/var/spool/cron/**`
- `/var/log/**`
- `/mnt/jellyfin-backups/**`
- `/home/dino/.config/systemd/user/**`
- `/home/dino/.claude/**`
- `/home/dino/.hermes/**`
- `/home/dino/mike-memory/**`

## Expected Command Surface

These commands are normal and expected for this machine:

- `systemctl --user ...`
- `sudo systemctl ...`
- `journalctl ...`
- `crontab -l`
- `sudo crontab -l`
- `find /etc ...`
- `find /var/spool ...`
- `cat /etc/crontab`
- `ls /etc/cron.d`
- `git -C <repo> status|pull|log|show`
- `python3 <script>`
- `bash <script>`

## Mollydog

- `mollydog` is the session-scoped sudo grant for this machine.
- Wrapper path: `/home/dino/scripts/mollydog.sh`
- It installs `/etc/sudoers.d/agent-session` with `dino ALL=(ALL) NOPASSWD: ALL`
- Access auto-revokes when the mollydog terminal exits or after 4 hours
- When Dino says `mollydog is active` or equivalent, treat that as explicit authorization to execute needed `sudo` commands directly without asking again during that session
- Canonical phrase on this machine: `mollydog is running`

## Launch Codex In Embedded Mode

- Default command: `codex`
- Interactive: `/home/dino/scripts/codex-embedded`
- Non-interactive: `/home/dino/scripts/codex-embedded-exec "your prompt"`
- Optional shell aliases live in: `/home/dino/scripts/codex-embedded-env.sh`
- These launch Codex with `--dangerously-bypass-approvals-and-sandbox`
- `/home/dino/bin/codex` wraps the embedded launcher so typing `codex` from any directory uses the embedded profile by default
- Embedded launchers export:
  - `HOME=/home/dino`
  - `CODEX_HOME=/home/dino/snap/codex/34`
  - `REAL_HOME=/home/dino`
  - `DINO_HOME=/home/dino`
  - `CODEX_KNOWLEDGE=/home/dino/CODEX-WORKING-KNOWLEDGE.md`
  - `CODEX_CASELAW=/home/dino/CODEX-CASELAW.md`
  - `LOCAL_GITHUB=/home/dino/citadel`
  - `LOCAL_FORGE_URL=http://cha0tikhome.tailc83c25.ts.net:3002/`
  - `LOCAL_FORGE_ROOT=/var/lib/forgejo/data/forgejo-repositories`
  - `LOCAL_FORGE_ORG=cha0tik`
  - `CITADEL_MEMORY_ROOT=/home/dino/citadel`
  - `ONLINE_GITHUB=https://github.com/randomchaos7800-hub`

## Important Boundary

- The launcher removes Codex's own approval and sandbox layer.
- It does not create OS privilege by itself.
- Root still depends on `mollydog` being active for the shell session that launches Codex.

## Operating Rules

- Use `~/.vault/vault.sh get <key>` for secrets. Never hardcode secrets.
- Use `http://100.120.50.35:8010/v1` with model `local` for local inference.
- Never hardcode tower backend ports `8022` or `8023` in configs.
- Prefer non-interactive commands.
- Prefer editing file-based config over hidden database state.
- Do not restart retired agents: Kato, CJ Craig, Morty, Dave CFO, Sabrina.

## Known Limitation

Codex-side rule approvals can reduce friction for command execution, but they do not override the outer runtime sandbox. If `/etc`, `/var/spool`, `sudo`, or hidden home paths are still blocked, the launcher/runtime policy must also grant those reads and command escalations.

Embedded sessions now use Dino's real home directly, so `~` resolves to `/home/dino`. `CODEX_HOME` stays pinned to `/home/dino/snap/codex/34` so Codex state remains isolated from the rest of the home directory.
