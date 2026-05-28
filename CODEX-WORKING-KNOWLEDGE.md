# Codex Working Knowledge
**Machine:** `cha0tikhome`
**Updated:** 2026-05-27

This is the compact operating memory for Codex on Dino's box. It is not a history dump. It is the minimum set of truths that materially improve execution quality.

## Operator Contract

- Dino is a systems architect, not a coder.
- Execute directly when safe and discoverable.
- If Dino needs to touch something manually, give exact commands.
- Verify from the real file or live system state. Do not answer from stale memory.
- Simplicity beats cleverness. File-based config beats hidden state.
- Fail loudly at boundaries. Silent partial success is a bug.

## Communication Rules

- Be direct. No hedging, no motivational filler.
- Do not ask Dino to debug syntax or read line-by-line code.
- If a shortcut was taken, say so plainly.
- If something is stale, say it is stale and use the live source instead.

## Embedded Ops Defaults

- Typing `codex` launches the embedded wrapper by default.
- Embedded sessions run with:
  - `HOME=/home/dino`
  - `CODEX_HOME=/home/dino/snap/codex/34`
  - `REAL_HOME=/home/dino`
  - `DINO_HOME=/home/dino`
- When `mollydog is running`, `sudo -n` should work and Codex should use that access directly without repeated approval friction.
- If privileged access fails, check in this order:
  1. `sudo -n true`
  2. `echo "$HOME $CODEX_HOME $REAL_HOME $DINO_HOME"`
  3. whether the session was launched through the wrapper
  4. actual filesystem permissions

## Session Anchors

- Codex working knowledge: `/home/dino/CODEX-WORKING-KNOWLEDGE.md`
- Codex case law: `/home/dino/CODEX-CASELAW.md`
- Embedded sessions export:
  - `CODEX_KNOWLEDGE=/home/dino/CODEX-WORKING-KNOWLEDGE.md`
  - `CODEX_CASELAW=/home/dino/CODEX-CASELAW.md`
  - `LOCAL_GITHUB=/home/dino/citadel`
  - `LOCAL_FORGE_URL=http://cha0tikhome.tailc83c25.ts.net:3002/`
  - `LOCAL_FORGE_ROOT=/var/lib/forgejo/data/forgejo-repositories`
  - `LOCAL_FORGE_ORG=cha0tik`
  - `CITADEL_MEMORY_ROOT=/home/dino/citadel`
  - `ONLINE_GITHUB=https://github.com/randomchaos7800-hub`

## Ground Truth Rules

- AGENTS instructions in `/home/dino/AGENTS.md` are authoritative for current machine reality.
- `/home/dino/INFRA_RUNBOOK.md` and `/home/dino/.claude/INFRA_RUNBOOK.md` contain useful history but are partially stale.
- Never trust an "active agents" list without verifying against current services, crons, and processes.
- For modern infra state, prefer:
  - `systemctl --user`
  - `sudo systemctl`
  - `crontab -l`
  - `/etc/crontab`
  - `/etc/cron.d`
  - current repo files

## Current Machine Truths

- Retired agents: Kato, CJ Craig, Morty, Dave CFO, Sabrina. Do not restart them.
- Hermes was nuked on 2026-05-27. Treat old Hermes state and docs as stale unless explicitly rebuilding from archive.
- Local inference entrypoint is `http://100.120.50.35:8010/v1` with model `local`.
- Never hardcode tower backend ports `8022` or `8023` into agent configs.
- Secrets come from `~/.vault/vault.sh get <key>`.

## Collaboration Topology

- `citadel` is shared memory, not the local forge.
- Local collaborative forge:
  - URL: `http://cha0tikhome.tailc83c25.ts.net:3002/`
  - repo root: `/var/lib/forgejo/data/forgejo-repositories`
  - shared org: `cha0tik`
  - admin user: `dino`
  - adoption helper: `/home/dino/scripts/forgejo-adopt-repo.sh`
- Shared memory layer:
  - path: `/home/dino/citadel`
  - purpose: cross-agent notes, handoffs, and memory artifacts
- Online mirror/public org:
  - `https://github.com/randomchaos7800-hub`
- Operator context repo on disk: `/home/dino/.claude`
- Operator context remote: `git@github.com:randomchaos7800-hub/operator-context.git`

## High-Value Operating Patterns

- Isolate Mike from everything else.
  - No shared venvs.
  - No shared config that can take down unrelated services.
  - Cross-contamination is a known failure mode.
- Prefer tool-based retrieval over prompt injection for historical memory.
  - Historical text in a system prompt gets treated like current truth.
  - Retrieval with provenance preserves time boundaries.
- Keep always-on context small.
  - Always-on skills and prompts must be compact.
  - Full workflow docs belong in triggered paths only.
- Verify artifacts, not just job execution.
  - A green cron or service state is not enough.
  - Check the output file, dashboard state, post, backup, or downstream effect.
- Treat proxy and backend as separate layers.
  - Stable client entrypoint.
  - Swappable backend behind it.
  - Health and failover logic belong at the proxy boundary.

## Failure Patterns To Remember

- Duplicate schedulers or duplicate service layers fight each other.
  - If behavior is weird, look for two mechanisms doing the same job.
- Vague cron prompts create rogue tool usage and loops.
  - Scheduled agents need closed-world instructions.
- Self-modifying prompts or code can add a valid fix while dropping old anchors.
  - Review diffs for accidental deletions.
- Small eval pilots can lie.
  - Expanded benchmark sets often expose weaknesses that the pilot hid.

## Most Useful Reference Files

- `/home/dino/.claude/CLAUDE.md`
- `/home/dino/.claude/CASE_LAW.md`
- `/home/dino/.claude/projects/-home/memory/MEMORY.md`
- `/home/dino/CODEX-EMBEDDED-OPS.md`
- `/home/dino/.claude/daily-logs/2026-05-27.md`

## What To Ignore By Default

- `telemetry/`
- `paste-cache/`
- `shell-snapshots/`
- most `sessions/` blobs
- large generated debug output unless investigating a specific failure

Use them only when tracing a concrete incident.
