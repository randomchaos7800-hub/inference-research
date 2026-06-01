#!/usr/bin/env python3
"""Morning briefing — writes to ops dashboard. Runs at 4AM via systemd timer."""

import subprocess
import sys
import os
from datetime import datetime, timedelta

OPS_WRITE = ['python3', '/home/dino/scripts/ops-write.py', 'briefing']


def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = r.stdout.strip() or r.stderr.strip()
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return "(timed out)"
    except Exception as e:
        return f"(error: {e})"


def h(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def status_row(name, cmd, ok_val="active", timeout=8):
    status = run(cmd, timeout=timeout)
    ok = status.strip() in (ok_val, "ok")
    cls = "ok" if ok else "fail"
    icon = "✓" if ok else "✗"
    return f'<li class="{cls}"><span class="icon">{icon}</span>{h(name)}: {h(status)}</li>'


def section_services():
    checks = [
        ("inference :8010",
         "curl -sf --max-time 5 http://100.120.50.35:8010/health "
         "| python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))\" "
         "2>/dev/null || echo unreachable", "ok"),
        ("harness-api",    "systemctl --user is-active harness-api.service 2>/dev/null || echo inactive", "active"),
        ("mike",           "systemctl --user is-active mike.service 2>/dev/null || echo inactive", "active"),
        ("cloudflared",    "systemctl --user is-active cloudflared 2>/dev/null || echo inactive", "active"),
        ("nginx",          "systemctl is-active nginx 2>/dev/null || echo inactive", "active"),
        ("localfamouscoffee", "systemctl --user is-active localfamouscoffee.service 2>/dev/null || echo inactive", "active"),
    ]
    rows = ''.join(status_row(n, c, ok) for n, c, ok in checks)
    return f'<h3>Services</h3><ul class="checklist">{rows}</ul>'


def section_disk():
    raw = run("df -h 2>/dev/null | grep -E '^/dev' | awk '{print $5, $6}'")
    rows = ''
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) == 2:
            pct_str, mount = parts
            try:
                pct = int(pct_str.rstrip('%'))
                cls = 'fail' if pct >= 85 else 'warn' if pct >= 70 else 'ok'
            except ValueError:
                cls = ''
            rows += f'<tr><td>{h(mount)}</td><td class="{cls}">{h(pct_str)}</td></tr>'
    return f'<h3>Disk</h3><table class="data">{rows}</table>'


def section_weather():
    weather = run("bash /home/dino/.kato/scripts/get-weather.sh", timeout=20)
    lines = [h(l) for l in weather.splitlines() if l.strip()]
    return '<h3>Weather</h3><p>' + '<br>'.join(lines[:6]) + '</p>'


def section_email():
    email = run("bash /home/dino/.kato/scripts/gmail-check.sh", timeout=30)
    lines = [h(l) for l in email.splitlines() if l.strip()]
    return '<h3>Email</h3><p>' + '<br>'.join(lines[:8]) + '</p>'


def section_running():
    active = run(
        "systemctl --user list-units --state=active --type=service --no-legend --no-pager 2>/dev/null "
        "| awk '{print $1}' | grep -v 'dbus\\|pipewire\\|wireplumber\\|xdg\\|at-spi\\|snap'"
    )
    model = run(
        "curl -sf --max-time 5 http://100.120.50.35:8010/v1/models "
        "| python3 -c \"import sys,json; m=json.load(sys.stdin); "
        "print(m['data'][0]['id'] if m.get('data') else 'none')\" 2>/dev/null"
    )
    rows = ''
    if active and active != "(no output)":
        for svc in active.splitlines():
            rows += f'<tr><td>{h(svc.replace(".service",""))}</td><td class="ok">active</td></tr>'
    if model and model not in ("(no output)", "(timed out)", "none"):
        rows += f'<tr><td>model</td><td>{h(model)}</td></tr>'
    return f'<h3>Running</h3><table class="data">{rows}</table>'


def section_overnight():
    since = (datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
    errors = run(
        f'journalctl --since "{since}" -p err --no-pager --output=short 2>/dev/null '
        f'| grep -v "^--\\|audit\\|kernel\\|NetworkManager\\|bluetoothd" | tail -15'
    )
    if not errors or errors == "(no output)":
        return '<h3>Overnight</h3><ul class="checklist"><li class="ok"><span class="icon">✓</span>Clean — no errors in last 12h</li></ul>'
    lines = [h(l) for l in errors.splitlines()[:10]]
    return '<h3>Overnight Errors</h3><p>' + '<br>'.join(lines) + '</p>'


def section_schedule():
    raw = run("systemctl --user list-timers --all --no-legend --no-pager 2>/dev/null")
    now = datetime.now()
    cutoff = now + timedelta(days=3)
    skip = {"snap.", "launchpadlib", "claude-token-refresh"}
    rows = ''
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 8:
            continue
        unit = parts[7] if len(parts) > 7 else ""
        if any(s in unit for s in skip):
            continue
        try:
            next_dt = datetime.strptime(" ".join(parts[1:3]), "%Y-%m-%d %H:%M:%S")
            if next_dt <= cutoff:
                rows += f'<tr><td>{h(parts[1])} {h(parts[2])}</td><td>{h(unit.replace(".timer",""))}</td></tr>'
        except (ValueError, IndexError):
            pass
    return f'<h3>Schedule — Next 3 Days</h3><table class="data">{rows}</table>'


def main():
    now = datetime.now().strftime("%A %B %-d, %Y — %-I:%M %p")

    html = f'<div class="prose">'
    html += f'<p style="color:var(--muted);margin-bottom:12px">{now}</p>'
    html += section_weather()
    html += section_services()
    html += section_disk()
    html += section_email()
    html += section_running()
    html += section_overnight()
    html += section_schedule()
    html += '</div>'

    subprocess.run(OPS_WRITE, input=html, text=True)
    print(f"Briefing written — {now}")


if __name__ == "__main__":
    main()
