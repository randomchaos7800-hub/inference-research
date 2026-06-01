#!/usr/bin/env python3
"""Overnight status — writes to ops dashboard at 4:20AM."""

import subprocess
import sys
import os
from datetime import datetime, timedelta

OPS_WRITE = ['python3', '/home/dino/scripts/ops-write.py', 'overnight']


def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "(timed out)"


def h(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def svc_row(name, cmd, ok_val="active"):
    status = run(cmd, timeout=8)
    ok = status.strip() == ok_val
    cls = "ok" if ok else "fail"
    icon = "✓" if ok else "✗"
    return f'<li class="{cls}"><span class="icon">{icon}</span>{h(name)}: {h(status)}</li>'


def main():
    since = (datetime.now() - timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")
    date = datetime.now().strftime("%A %B %-d")

    html = '<div class="prose">'

    # Services
    rows = ''
    rows += svc_row("harness-api", "systemctl --user is-active harness-api.service 2>/dev/null || echo inactive")
    rows += svc_row("mike", "systemctl --user is-active mike.service 2>/dev/null || echo inactive")
    rows += svc_row("inference :8010",
        "curl -sf --max-time 5 http://100.120.50.35:8010/health "
        "| python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))\" 2>/dev/null "
        "|| echo unreachable", ok_val="ok")
    html += f'<h3>Services</h3><ul class="checklist">{rows}</ul>'

    # Failed units
    failed = run("systemctl --user is-failed 2>/dev/null | grep -v '^0 units' || echo none")
    if failed.strip() not in ("none", "(no output)"):
        html += f'<h3>Failed Units</h3><p style="color:var(--fail)">{h(failed)}</p>'

    # Disk
    disk_raw = run("df -h / /mnt/backup /mnt/jellyfin-backups 2>/dev/null || df -h /")
    disk_rows = ''
    for line in disk_raw.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 6:
            pct = int(parts[4].rstrip('%'))
            cls = 'fail' if pct >= 85 else 'warn' if pct >= 70 else 'ok'
            disk_rows += f'<tr><td>{h(parts[5])}</td><td class="{cls}">{h(parts[4])}</td></tr>'
    html += f'<h3>Disk</h3><table class="data">{disk_rows}</table>'

    # Overnight errors
    errors = run(
        f'journalctl --since "{since}" -p err --no-pager --output=short 2>/dev/null '
        f'| grep -v "^--\\|audit\\|BIOS\\|acpi\\|bluetoothd" | grep -v "^$" | tail -20'
    )
    if not errors or errors == "(no output)":
        html += '<h3>Errors</h3><ul class="checklist"><li class="ok"><span class="icon">✓</span>Clean</li></ul>'
    else:
        lines = [f'<li class="fail"><span class="icon">✗</span>{h(l)}</li>' for l in errors.splitlines()[:10]]
        html += f'<h3>Errors (last 10h)</h3><ul class="checklist">{"".join(lines)}</ul>'

    # Service restarts
    restarts = run(
        f'journalctl --since "{since}" --no-pager 2>/dev/null '
        f'| grep -iE "start|restart|stop|killed|crash" | grep -v "^--" | tail -10'
    )
    if restarts and restarts != "(no output)":
        lines = [h(l) for l in restarts.splitlines()[:8]]
        html += '<h3>Service Lifecycle</h3><p>' + '<br>'.join(lines) + '</p>'

    html += '</div>'

    subprocess.run(OPS_WRITE, input=html, text=True)
    print(f"Overnight status written — {date}")


if __name__ == "__main__":
    main()
