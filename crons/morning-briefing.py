#!/usr/bin/env python3
"""Morning briefing — standalone script, no agent needed. Runs at 4AM via systemd timer."""

import subprocess
import json
import urllib.request
import sys
import os
from datetime import datetime, timedelta

SLACK_CHANNEL = "C0AHPBSK9SP"  # #kato-comms
VAULT = os.path.expanduser("~/.vault/vault.sh")


def get_slack_token():
    r = subprocess.run([VAULT, "get", "slack_kato_bot_token"], capture_output=True, text=True)
    return r.stdout.strip()


def slack_post(token, text):
    payload = json.dumps({
        "channel": SLACK_CHANNEL,
        "text": text,
        "unfurl_links": False,
        "mrkdwn": True,
    }).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        resp = json.loads(r.read())
        if not resp.get("ok"):
            print(f"Slack error: {resp.get('error')}", file=sys.stderr)


def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = r.stdout.strip() or r.stderr.strip()
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return "(timed out)"
    except Exception as e:
        return f"(error: {e})"


# ── Sections ──────────────────────────────────────────────────────────────────

def section_weather():
    return run("bash /home/dino/.kato/scripts/get-weather.sh", timeout=20)


def section_services():
    checks = [
        ("inference :8010",
         "curl -sf --max-time 5 http://100.120.50.35:8010/health "
         "| python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))\" "
         "2>/dev/null || echo unreachable"),
        ("frank-api",     "systemctl --user is-active frank-api.service 2>/dev/null || echo inactive"),
        ("mike",          "systemctl --user is-active mike.service 2>/dev/null || echo inactive"),
        ("cloudflared",   "systemctl --user is-active cloudflared 2>/dev/null || echo inactive"),
        ("nginx",         "systemctl is-active nginx 2>/dev/null || echo inactive"),
        ("pandorica",     "systemctl --user is-active pandorica-sync.service 2>/dev/null || echo inactive"),
    ]
    lines = []
    for name, cmd in checks:
        status = run(cmd, timeout=8)
        icon = "✅" if status in ("active", "ok") else "🔴"
        lines.append(f"  {icon} {name}: {status}")
    return "\n".join(lines)


def section_disk():
    raw = run("df -h 2>/dev/null | grep -E '^/dev|^tmpfs' | grep -v 'tmpfs.*tmpfs' | awk '{print $5, $6}'")
    lines = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) == 2:
            pct_str, mount = parts
            try:
                pct = int(pct_str.rstrip("%"))
                icon = "🔴" if pct >= 85 else "⚠️" if pct >= 70 else "✅"
            except ValueError:
                icon = "  "
            lines.append(f"  {icon} {mount}: {pct_str}")
    return "\n".join(lines) if lines else raw


def section_email():
    return run("bash /home/dino/.kato/scripts/gmail-check.sh", timeout=30)


def section_what_running():
    lines = []

    # Systemd user services that are active
    active = run("systemctl --user list-units --state=active --type=service --no-legend --no-pager 2>/dev/null "
                 "| awk '{print $1}' | grep -v 'dbus\\|pipewire\\|wireplumber\\|xdg\\|at-spi\\|snap'")
    if active and active != "(no output)":
        for svc in active.splitlines():
            lines.append(f"  ▸ {svc.replace('.service','')}")

    # Inference model currently loaded
    model = run("curl -sf --max-time 5 http://100.120.50.35:8010/v1/models "
                "| python3 -c \"import sys,json; m=json.load(sys.stdin); "
                "print(m['data'][0]['id'] if m.get('data') else 'none')\" 2>/dev/null")
    if model and model not in ("(no output)", "(timed out)", "none"):
        lines.append(f"  🧠 model: {model}")

    return "\n".join(lines) if lines else "  (nothing notable running)"


def section_overnight():
    since = (datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
    # System-level errors
    errors = run(
        f'journalctl --since "{since}" -p err --no-pager --output=short 2>/dev/null '
        f'| grep -v "^--\\|audit\\|kernel\\|NetworkManager\\|bluetoothd" | tail -15'
    )
    if not errors or errors == "(no output)":
        return "  ✅ Clean — no errors in last 12h"
    # Summarize: count unique units
    units = set()
    lines = []
    for line in errors.splitlines():
        if ": " in line:
            unit = line.split(": ")[0].split()[-1]
            units.add(unit)
        lines.append(f"  {line}")
    summary = f"  ⚠️ Errors from: {', '.join(sorted(units))}\n"
    return summary + "\n".join(lines[:10])


def section_schedule():
    # Systemd timers — next fire time
    raw = run("systemctl --user list-timers --all --no-legend --no-pager 2>/dev/null")
    lines = []
    now = datetime.now()
    cutoff = now + timedelta(days=3)
    skip = {"snap.", "launchpadlib", "claude-token-refresh"}

    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 8:
            continue
        unit = parts[7] if len(parts) > 7 else ""
        if any(s in unit for s in skip):
            continue
        next_str = " ".join(parts[:4])
        try:
            # systemd format: "Wed 2026-05-27 02:00:00 PDT"
            next_dt = datetime.strptime(" ".join(parts[1:3]), "%Y-%m-%d %H:%M:%S")
            if next_dt <= cutoff:
                lines.append(f"  {parts[1]} {parts[2]} — {unit.replace('.timer','')}")
        except (ValueError, IndexError):
            lines.append(f"  {next_str} — {unit.replace('.timer','')}")

    # Notable cron jobs (daily/less frequent only)
    cron_notable = [
        "3:00 AM  — backups (mike, system, vault, www)",
        "6:00 AM  — perf-log",
        "8:00 AM  — disk-alert",
    ]
    lines += [f"  {c}" for c in cron_notable]

    return "\n".join(lines) if lines else "  (no timers in next 3 days)"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    token = get_slack_token()
    if not token:
        print("ERROR: no slack_kato_bot_token in vault", file=sys.stderr)
        sys.exit(1)

    now = datetime.now().strftime("%A %B %-d, %Y — %-I:%M %p")

    msg = "\n".join([
        f"*🌅 Morning Briefing — {now}*",
        "",
        f"*Weather*",
        section_weather(),
        "",
        f"*Services*",
        section_services(),
        "",
        f"*Disk*",
        section_disk(),
        "",
        f"*Email*",
        section_email(),
        "",
        f"*What's Running*",
        section_what_running(),
        "",
        f"*Broke Overnight*",
        section_overnight(),
        "",
        f"*Schedule — Next 3 Days*",
        section_schedule(),
    ])

    slack_post(token, msg)
    print(f"Briefing posted — {now}")


if __name__ == "__main__":
    main()
