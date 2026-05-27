#!/usr/bin/env python3
"""Overnight status report — posts to #ops-log at 4:20AM."""

import subprocess
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import slack

CHANNEL = "C0AHPBSK9SP"  # #kato-comms


def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "(timed out)"


def main():
    since = (datetime.now() - timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")
    date = datetime.now().strftime("%A %B %-d")

    # Services
    frank = run("systemctl --user is-active frank-api.service 2>/dev/null || echo inactive")
    mike  = run("systemctl --user is-active mike.service 2>/dev/null || echo inactive")
    inference = run(
        "curl -sf --max-time 5 http://100.120.50.35:8010/health "
        "| python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))\" 2>/dev/null "
        "|| echo unreachable"
    )

    def svc_icon(s): return "✅" if s == "active" else "🔴"
    def inf_icon(s): return "✅" if s == "ok" else "🔴"

    services = (
        f"  {svc_icon(frank)} frank-api: {frank}\n"
        f"  {svc_icon(mike)} mike: {mike}\n"
        f"  {inf_icon(inference)} inference :8010: {inference}"
    )

    # Failed units
    failed = run("systemctl --user is-failed 2>/dev/null | grep -v '^0 units' || echo none")

    # Disk
    disk_raw = run("df -h / /mnt/backup /mnt/jellyfin-backups 2>/dev/null || df -h /")
    disk_lines = []
    for line in disk_raw.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 6:
            pct = int(parts[4].rstrip("%"))
            icon = "🔴" if pct >= 85 else "⚠️" if pct >= 70 else "✅"
            disk_lines.append(f"  {icon} {parts[5]}: {parts[4]}")
    disk = "\n".join(disk_lines) or disk_raw

    # Overnight errors
    errors = run(
        f'journalctl --since "{since}" -p err --no-pager --output=short 2>/dev/null '
        f'| grep -v "^--\\|audit\\|BIOS\\|acpi\\|bluetoothd" | grep -v "^$" | tail -20'
    )
    if not errors or errors == "(no output)":
        errors = "  ✅ Clean"
    else:
        errors = "\n".join(f"  {l}" for l in errors.splitlines()[:15])

    # Service restarts overnight
    restarts = run(
        f'journalctl --since "{since}" --no-pager 2>/dev/null '
        f'| grep -iE "start|restart|stop|killed|crash" | grep -v "^--" | tail -10'
    )
    if not restarts or restarts == "(no output)":
        restarts = "  (none)"
    else:
        restarts = "\n".join(f"  {l}" for l in restarts.splitlines()[:8])

    msg = "\n".join([
        f"*🌙 Overnight Status — {date}*",
        "",
        "*Services*",
        services,
        f"  Failed units: {failed}",
        "",
        "*Disk*",
        disk,
        "",
        "*Errors (last 10h)*",
        errors,
        "",
        "*Service Lifecycle*",
        restarts,
    ])

    slack.post(msg, channel=CHANNEL)
    print(f"Overnight status posted — {date}")


if __name__ == "__main__":
    main()
