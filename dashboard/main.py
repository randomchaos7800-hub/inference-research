#!/usr/bin/env python3
"""Boundary Labs — Live Status Dashboard"""

import asyncio
import glob as _glob
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psutil
import yaml
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

TOWER_METRICS_URL = "http://100.120.50.35:8010/metrics/daily?days=8"

app = FastAPI()

_cfg_path = Path(__file__).parent / "monitor.yaml"
_cfg = yaml.safe_load(_cfg_path.read_text())

AGENTS = [(a["id"], a["label"], a["scope"]) for a in _cfg.get("agents", [])]
SERVICES = [(s["id"], s["label"], s["scope"]) for s in _cfg.get("services", [])]
WATCHED_TIMERS = [(t["unit"], t["label"], float(t["stale_hours"])) for t in _cfg.get("timers", [])]
ARTIFACTS = _cfg.get("artifacts", [])

TOWER_HOST = "dino@100.120.50.35"

INFERENCE_URL = "http://100.120.50.35:8010/health"
INFERENCE_STATUS_FILE = Path("/home/dino/www/dinovitale.com/data/inference-status.json")


def check_artifact(glob_pat: str, stale_hours: float) -> dict:
    pattern = glob_pat.replace("~", str(Path.home()))
    matches = sorted(_glob.glob(pattern), key=lambda p: Path(p).stat().st_mtime, reverse=True)
    if not matches:
        return {"status": "missing", "age_h": None}
    age_h = (time.time() - Path(matches[0]).stat().st_mtime) / 3600
    return {"status": "ok" if age_h < stale_hours else "stale", "age_h": round(age_h, 1)}


def check_systemd(service: str, scope: str) -> str:
    try:
        if scope == "user":
            cmd = ["systemctl", "--user", "is-active", service]
        else:
            cmd = ["systemctl", "is-active", service]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        return result.stdout.strip()
    except Exception:
        return "unknown"


async def check_tower_gpu() -> dict:
    try:
        cmd = (
            "nvidia-smi --query-gpu=index,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits; "
            "free -m | awk '/^Mem:/{print $2,$3,$4}'; "
            "grep 'cpu ' /proc/stat | awk '{u=$2+$4; t=$2+$3+$4+$5; print u, t}'"
        )
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", TOWER_HOST, cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8)
        lines = stdout.decode().strip().splitlines()
        gpus, ram, cpu_pct = [], None, None
        cpu_samples = []
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 5:
                gpus.append({
                    "index": int(parts[0]),
                    "temp": int(parts[1]),
                    "util": int(parts[2]),
                    "mem_used": int(parts[3]),
                    "mem_total": int(parts[4]),
                })
            else:
                parts = line.split()
                if len(parts) == 3 and parts[0].isdigit():
                    total, used = int(parts[0]), int(parts[1])
                    ram = {"total_mb": total, "used_mb": used, "pct": round(used / total * 100)}
                elif len(parts) == 2 and parts[0].isdigit():
                    cpu_samples.append((int(parts[0]), int(parts[1])))
        if len(cpu_samples) == 2:
            du = cpu_samples[1][0] - cpu_samples[0][0]
            dt = cpu_samples[1][1] - cpu_samples[0][1]
            cpu_pct = round(du / dt * 100) if dt else 0
        elif len(cpu_samples) == 1:
            u, t = cpu_samples[0]
            cpu_pct = round(u / t * 100) if t else 0
        return {"ok": True, "gpus": gpus, "ram": ram, "cpu_pct": cpu_pct}
    except Exception:
        return {"ok": False, "gpus": [], "ram": None, "cpu_pct": None}


async def check_inference() -> dict:
    base = INFERENCE_URL.rsplit("/health", 1)[0]
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(INFERENCE_URL)
            if r.status_code == 200:
                latency = int(r.elapsed.total_seconds() * 1000)
                model = None
                ctx = None
                tok_s = None
                try:
                    ar = await client.get(f"{base}/active")
                    ad = ar.json()
                    model = ad.get("model") or ad.get("active")
                    mr = await client.get(f"{base}/v1/models")
                    mdata = mr.json().get("data", [])
                    if mdata:
                        ctx = mdata[0].get("max_model_len")
                except Exception:
                    pass
                try:
                    cached = json.loads(INFERENCE_STATUS_FILE.read_text())
                    tok_s = cached.get("tok_s")
                except Exception:
                    pass
                return {"status": "ok", "latency_ms": latency, "model": model, "ctx": ctx, "tok_s": tok_s}
    except Exception:
        pass
    return {"status": "down", "latency_ms": None, "model": None, "ctx": None, "tok_s": None}


def _fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _parse_usec(val: str) -> float | None:
    """Parse systemd timestamp — raw microseconds int or human-readable string."""
    if not val or val.strip() == "0" or val.strip() == "":
        return None
    try:
        usec = int(val.strip())
        return usec / 1e6 if usec > 0 else None
    except ValueError:
        pass
    import re
    try:
        clean = re.sub(r'\s+[A-Z]{2,4}$', '', val.strip())
        dt = datetime.strptime(clean, "%a %Y-%m-%d %H:%M:%S")
        return dt.timestamp()
    except Exception:
        pass
    return None


def _stale_threshold(expr: str) -> float:
    parts = expr.split()[:5]
    if len(parts) != 5:
        return 26.0
    minute, hour, dom, _month, dow = parts
    if minute.startswith("*/"):
        return int(minute[2:]) * 4 / 60
    if hour == "*":
        return 3.0
    if dow != "*" or dom != "*":
        return 9 * 24
    return 26.0


@app.get("/api/crons")
async def get_crons():
    jobs_out = []

    # Append systemd user timers
    for unit, name, threshold in WATCHED_TIMERS:
        try:
            r = subprocess.run(
                ["systemctl", "--user", "show", unit,
                 "--property=ActiveState,LastTriggerUSec"],
                capture_output=True, text=True, timeout=3
            )
            props = dict(
                line.split("=", 1) for line in r.stdout.strip().splitlines() if "=" in line
            )
            active = props.get("ActiveState", "inactive")
            last_ts = _parse_usec(props.get("LastTriggerUSec", ""))

            if last_ts is None:
                age_h = None
                status = "never" if active != "failed" else "stale"
            else:
                age_h = (time.time() - last_ts) / 3600
                status = "ok" if age_h < threshold else "stale"
                if active == "failed":
                    status = "stale"
        except Exception:
            age_h = None
            status = "unknown"

        jobs_out.append({
            "name": name,
            "schedule": "",
            "age_h": round(age_h, 1) if age_h is not None else None,
            "status": status,
            "source": "timer",
        })

    # Append artifact checks
    for art in ARTIFACTS:
        result = check_artifact(art["glob"], float(art["stale_hours"]))
        jobs_out.append({
            "name": art["label"],
            "schedule": "",
            "age_h": result["age_h"],
            "status": result["status"],
            "source": "artifact",
        })

    return JSONResponse({"jobs": jobs_out})


@app.get("/api/tokens")
async def get_tokens():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(TOWER_METRICS_URL)
            data = r.json()
    except Exception as e:
        return JSONResponse({"error": str(e)})
    days = data.get("days", [])
    if not days:
        return JSONResponse({"error": "no data"})
    today = days[0]
    pt = today.get("prompt_tokens", 0)
    ct = today.get("completion_tokens", 0)
    tt = today.get("total_tokens", pt + ct)
    reqs = today.get("requests", 0)
    cost = today.get("sonnet_cost_usd", 0.0)
    week_cost = sum(d.get("sonnet_cost_usd", 0.0) for d in days[:7])
    week_tt = sum(d.get("total_tokens", 0) for d in days[:7])
    return JSONResponse({
        "today_total": _fmt_tokens(tt),
        "today_in": _fmt_tokens(pt),
        "today_out": _fmt_tokens(ct),
        "today_reqs": reqs,
        "today_cost": f"${cost:.2f}",
        "week_cost": f"${week_cost:.2f}",
        "week_total": _fmt_tokens(week_tt),
    })


@app.get("/api/status")
async def get_status():
    agents = []
    for svc, label, scope in AGENTS:
        state = check_systemd(svc + ".service", scope)
        agents.append({"id": svc, "label": label, "state": state})

    services = []
    for svc, label, scope in SERVICES:
        state = check_systemd(svc, scope)
        services.append({"id": svc, "label": label, "state": state})

    inference = await check_inference()
    tower_gpu = await check_tower_gpu()

    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # Backup drive
    try:
        backup = psutil.disk_usage("/mnt/jellyfin-backups")
        backup_pct = backup.percent
        backup_ok = True
    except Exception:
        backup_pct = 0
        backup_ok = False

    return JSONResponse({
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agents": agents,
        "services": services,
        "inference": inference,
        "tower_gpu": tower_gpu,
        "system": {
            "cpu_pct": cpu,
            "mem_pct": mem.percent,
            "mem_used_gb": round(mem.used / 1e9, 1),
            "mem_total_gb": round(mem.total / 1e9, 1),
            "disk_pct": disk.percent,
            "disk_free_gb": round(disk.free / 1e9, 1),
            "backup_ok": backup_ok,
            "backup_pct": backup_pct,
            "uptime_h": round((time.time() - psutil.boot_time()) / 3600, 1),
        }
    })


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1920">
<title>Boundary Labs — Status</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #080c10;
    --surface: #0d1117;
    --border: #1e2a38;
    --green: #00e676;
    --red: #ff1744;
    --yellow: #ffd600;
    --blue: #40c4ff;
    --text: #e0e6ed;
    --muted: #4a5568;
    --accent: #00b4d8;
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    height: 100vh;
    overflow: hidden;
    display: grid;
    grid-template-rows: 70px 1fr 90px 90px;
    grid-template-columns: 1fr;
  }

  /* HEADER */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }
  .logo { font-size: 20px; font-weight: 700; letter-spacing: 4px; color: var(--accent); text-transform: uppercase; }
  .logo span { color: var(--muted); font-weight: 400; }
  .timestamp { font-size: 14px; color: var(--muted); letter-spacing: 2px; }
  .overall-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--green); box-shadow: 0 0 10px var(--green); animation: pulse 2s infinite; }

  /* MAIN */
  main {
    display: grid;
    grid-template-columns: 1fr 1fr 340px;
    gap: 20px;
    padding: 20px 32px;
    overflow: hidden;
  }

  /* CARDS */
  .panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .panel-title {
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 4px;
  }

  /* SERVICE ROWS */
  .item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    background: var(--bg);
    border-radius: 6px;
    border: 1px solid var(--border);
  }
  .item-label { font-size: 15px; letter-spacing: 1px; }
  .badge {
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 4px;
    font-weight: 700;
  }
  .badge-ok      { background: rgba(0,230,118,0.12); color: var(--green); border: 1px solid rgba(0,230,118,0.3); }
  .badge-down    { background: rgba(255,23,68,0.12);  color: var(--red);   border: 1px solid rgba(255,23,68,0.3); }
  .badge-unknown { background: rgba(255,214,0,0.10);  color: var(--yellow);border: 1px solid rgba(255,214,0,0.2); }

  /* INFERENCE PANEL */
  .inference-big {
    text-align: center;
    padding: 20px;
    border-radius: 8px;
    background: var(--bg);
    border: 1px solid var(--border);
  }
  .inference-status { font-size: 28px; font-weight: 700; letter-spacing: 3px; }
  .inference-label  { font-size: 11px; color: var(--muted); letter-spacing: 2px; margin-top: 4px; }
  .inference-latency { font-size: 13px; color: var(--blue); margin-top: 8px; }

  /* FOOTER / STATS */
  footer {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    padding: 16px 32px;
    border-top: 1px solid var(--border);
    background: var(--surface);
  }
  .stat {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .stat-label { font-size: 10px; letter-spacing: 3px; text-transform: uppercase; color: var(--muted); }
  .stat-value { font-size: 22px; font-weight: 700; color: var(--text); }
  .stat-sub   { font-size: 11px; color: var(--muted); }
  .bar {
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }
  .bar-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }
  .bar-green  { background: var(--green); }
  .bar-yellow { background: var(--yellow); }
  .bar-red    { background: var(--red); }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  }
  .dot-ok   { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .dot-down { background: var(--red);   box-shadow: 0 0 6px var(--red); animation: pulse 1s infinite; }
  .dot-unk  { background: var(--yellow);}
  .dot-err  { background: var(--red); box-shadow: 0 0 6px var(--red); }
  .item-left { display: flex; align-items: center; gap: 10px; }

  /* CRON ROWS */
  .cron-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 14px;
    background: var(--bg);
    border-radius: 6px;
    border: 1px solid var(--border);
    margin-bottom: 5px;
  }
  .cron-row:last-child { margin-bottom: 0; }
  .cron-name { font-size: 12px; flex: 1; color: var(--text); letter-spacing: 0.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cron-age  { font-size: 10px; color: var(--muted); letter-spacing: 1px; flex-shrink: 0; }
  .dot-never { background: var(--muted); }
</style>
</head>
<body>

<header>
  <div class="logo">Boundary Labs <span>/ STATUS</span></div>
  <div id="timestamp" class="timestamp">--:--:--</div>
  <div id="overall-dot" class="overall-dot"></div>
</header>

<main>
  <!-- AGENTS + CRONS stacked -->
  <div style="display:flex;flex-direction:column;gap:20px;min-height:0;">
    <div class="panel" style="flex:0 0 auto;">
      <div class="panel-title">Agents</div>
      <div id="agents"></div>
    </div>
    <div class="panel" style="flex:1;overflow-y:auto;">
      <div class="panel-title">Scheduled Jobs</div>
      <div id="crons"><div style="color:var(--muted);font-size:12px;padding:8px 0;">loading…</div></div>
    </div>
  </div>

  <!-- SERVICES -->
  <div class="panel">
    <div class="panel-title">Services</div>
    <div id="services"></div>
  </div>

  <!-- RIGHT COLUMN -->
  <div style="display:flex;flex-direction:column;gap:20px;">
    <div class="panel" style="flex:1;">
      <div class="panel-title">Local Inference</div>
      <div class="inference-big">
        <div id="inf-status" class="inference-status" style="color:var(--muted)">--</div>
        <div class="inference-label">cha0tiktower · RTX 5060 Ti</div>
        <div id="inf-latency" class="inference-latency"></div>
      </div>
      <div class="item">
        <div class="item-left"><div class="dot dot-ok"></div><span class="item-label" id="inf-model">--</span></div>
        <span class="badge badge-ok">LOADED</span>
      </div>
      <div id="token-metrics" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:12px 14px;display:flex;flex-direction:column;gap:8px;">
        <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--muted);">Token Usage</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
          <div>
            <div style="font-size:18px;font-weight:700;color:var(--blue);" id="tok-today">--</div>
            <div style="font-size:10px;color:var(--muted);" id="tok-today-sub">today</div>
          </div>
          <div>
            <div style="font-size:18px;font-weight:700;color:#00e676;" id="tok-saved">--</div>
            <div style="font-size:10px;color:var(--muted);" id="tok-saved-sub">saved today</div>
          </div>
        </div>
        <div style="font-size:11px;color:var(--muted);" id="tok-week"></div>
      </div>
    </div>

    <div class="panel" style="flex:1;">
      <div class="panel-title">Tower GPU</div>
      <div id="tower-gpu">
        <div class="item"><div class="item-left"><div class="dot dot-unk"></div><span class="item-label" style="color:var(--muted)">polling…</span></div></div>
      </div>
    </div>
  </div>
</main>

<footer style="border-top:1px solid var(--border);border-bottom:1px solid var(--border);">
  <div class="stat">
    <div class="stat-label">Tower CPU</div>
    <div id="t-cpu-val" class="stat-value">--%</div>
    <div class="bar"><div id="t-cpu-bar" class="bar-fill bar-green" style="width:0%"></div></div>
    <div class="stat-sub">cha0tiktower</div>
  </div>
  <div class="stat">
    <div class="stat-label">Tower RAM</div>
    <div id="t-mem-val" class="stat-value">-- GB</div>
    <div class="bar"><div id="t-mem-bar" class="bar-fill bar-green" style="width:0%"></div></div>
    <div id="t-mem-sub" class="stat-sub"></div>
  </div>
  <div class="stat">
    <div class="stat-label">GPU0 VRAM</div>
    <div id="t-vram0-val" class="stat-value">-- MiB</div>
    <div class="bar"><div id="t-vram0-bar" class="bar-fill bar-green" style="width:0%"></div></div>
    <div id="t-vram0-sub" class="stat-sub"></div>
  </div>
  <div class="stat">
    <div class="stat-label">GPU1 VRAM</div>
    <div id="t-vram1-val" class="stat-value">-- MiB</div>
    <div class="bar"><div id="t-vram1-bar" class="bar-fill bar-green" style="width:0%"></div></div>
    <div id="t-vram1-sub" class="stat-sub"></div>
  </div>
  <div class="stat">
    <div class="stat-label">Model</div>
    <div id="t-model-val" class="stat-value" style="font-size:14px;">--</div>
    <div id="t-ctx-sub" class="stat-sub"></div>
  </div>
</footer>
<footer>
  <div class="stat">
    <div class="stat-label">CPU</div>
    <div id="cpu-val" class="stat-value">--%</div>
    <div class="bar"><div id="cpu-bar" class="bar-fill bar-green" style="width:0%"></div></div>
    <div class="stat-sub">cha0tikhome</div>
  </div>
  <div class="stat">
    <div class="stat-label">Memory</div>
    <div id="mem-val" class="stat-value">-- GB</div>
    <div class="bar"><div id="mem-bar" class="bar-fill bar-green" style="width:0%"></div></div>
    <div id="mem-sub" class="stat-sub"></div>
  </div>
  <div class="stat">
    <div class="stat-label">Disk /</div>
    <div id="disk-val" class="stat-value">--%</div>
    <div class="bar"><div id="disk-bar" class="bar-fill bar-green" style="width:0%"></div></div>
    <div id="disk-sub" class="stat-sub"></div>
  </div>
  <div class="stat">
    <div class="stat-label">Backup</div>
    <div id="backup-val" class="stat-value">--</div>
    <div class="bar"><div id="backup-bar" class="bar-fill bar-green" style="width:0%"></div></div>
  </div>
  <div class="stat">
    <div class="stat-label">Uptime</div>
    <div id="uptime-val" class="stat-value">-- h</div>
    <div class="stat-sub">cha0tikhome</div>
  </div>
</footer>

<script>
function barColor(pct) {
  if (pct < 70) return 'bar-green';
  if (pct < 90) return 'bar-yellow';
  return 'bar-red';
}

function badge(state) {
  if (state === 'active') return '<span class="badge badge-ok">LIVE</span>';
  if (state === 'inactive' || state === 'failed') return '<span class="badge badge-down">DOWN</span>';
  return '<span class="badge badge-unknown">UNKNOWN</span>';
}

function dot(state) {
  if (state === 'active') return '<div class="dot dot-ok"></div>';
  if (state === 'inactive' || state === 'failed') return '<div class="dot dot-down"></div>';
  return '<div class="dot dot-unk"></div>';
}

function renderList(containerId, items) {
  const el = document.getElementById(containerId);
  el.innerHTML = items.map(i => `
    <div class="item" style="margin-bottom:8px;">
      <div class="item-left">${dot(i.state)}<span class="item-label">${i.label}</span></div>
      ${badge(i.state)}
    </div>`).join('');
}

async function refresh() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();

    document.getElementById('timestamp').textContent = d.ts;

    renderList('agents', d.agents);
    renderList('services', d.services);

    // Inference
    const inf = d.inference;
    const infEl = document.getElementById('inf-status');
    if (inf.status === 'ok') {
      infEl.textContent = 'ONLINE';
      infEl.style.color = 'var(--green)';
      const tokStr = inf.tok_s ? ' · ' + inf.tok_s + ' t/s' : '';
      document.getElementById('inf-latency').textContent = inf.latency_ms + ' ms' + tokStr;
    } else {
      infEl.textContent = 'OFFLINE';
      infEl.style.color = 'var(--red)';
      document.getElementById('inf-latency').textContent = '';
    }
    if (inf.model) document.getElementById('inf-model').textContent = inf.model;

    // System stats
    const s = d.system;
    document.getElementById('cpu-val').textContent = s.cpu_pct + '%';
    const cpuBar = document.getElementById('cpu-bar');
    cpuBar.style.width = s.cpu_pct + '%';
    cpuBar.className = 'bar-fill ' + barColor(s.cpu_pct);

    document.getElementById('mem-val').textContent = s.mem_used_gb + ' GB';
    document.getElementById('mem-sub').textContent = 'of ' + s.mem_total_gb + ' GB';
    const memBar = document.getElementById('mem-bar');
    memBar.style.width = s.mem_pct + '%';
    memBar.className = 'bar-fill ' + barColor(s.mem_pct);

    document.getElementById('disk-val').textContent = s.disk_pct + '%';
    document.getElementById('disk-sub').textContent = s.disk_free_gb + ' GB free';
    const diskBar = document.getElementById('disk-bar');
    diskBar.style.width = s.disk_pct + '%';
    diskBar.className = 'bar-fill ' + barColor(s.disk_pct);

    if (s.backup_ok) {
      document.getElementById('backup-val').textContent = s.backup_pct + '%';
      const bbBar = document.getElementById('backup-bar');
      bbBar.style.width = s.backup_pct + '%';
      bbBar.className = 'bar-fill ' + barColor(s.backup_pct);
    } else {
      document.getElementById('backup-val').textContent = 'N/A';
    }

    document.getElementById('uptime-val').textContent = s.uptime_h + 'h';

    // Tower GPU
    const tg = d.tower_gpu;
    const tgEl = document.getElementById('tower-gpu');
    if (!tg.ok || tg.gpus.length === 0) {
      tgEl.innerHTML = '<div class="item"><div class="item-left"><div class="dot dot-down"></div><span class="item-label">unreachable</span></div></div>';
    } else {
      let html = tg.gpus.map(g => {
        const memPct = Math.round(g.mem_used / g.mem_total * 100);
        const col = g.temp > 80 ? 'var(--red)' : g.temp > 65 ? 'var(--yellow)' : 'var(--green)';
        return `<div class="item" style="margin-bottom:8px;flex-direction:column;align-items:stretch;gap:6px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="item-label">GPU${g.index}</span>
            <span style="color:${col};font-size:13px;font-weight:700;">${g.temp}°C</span>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--muted);">
            <span>util ${g.util}%</span>
            <span>${g.mem_used}/${g.mem_total} MiB</span>
          </div>
          <div class="bar"><div class="bar-fill ${barColor(memPct)}" style="width:${memPct}%"></div></div>
        </div>`;
      }).join('');

      if (tg.ram) {
        const rp = tg.ram.pct;
        const rUsed = (tg.ram.used_mb / 1024).toFixed(1);
        const rTotal = (tg.ram.total_mb / 1024).toFixed(1);
        html += `<div class="item" style="margin-bottom:8px;flex-direction:column;align-items:stretch;gap:6px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="item-label">RAM</span>
            <span style="font-size:12px;color:var(--muted);">${rUsed} / ${rTotal} GB</span>
          </div>
          <div class="bar"><div class="bar-fill ${barColor(rp)}" style="width:${rp}%"></div></div>
        </div>`;
      }

      if (inf.model) {
        const ctxStr = inf.ctx ? (inf.ctx >= 1000 ? Math.round(inf.ctx/1000) + 'K ctx' : inf.ctx + ' ctx') : '';
        html += `<div class="item" style="flex-direction:column;align-items:stretch;gap:4px;">
          <div style="font-size:11px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;">Model</div>
          <div style="font-size:13px;color:var(--blue);word-break:break-all;">${inf.model}</div>
          ${ctxStr ? `<div style="font-size:11px;color:var(--muted);">${ctxStr}</div>` : ''}
        </div>`;
      }

      tgEl.innerHTML = html;
    }

    // Tower footer
    if (tg.ok) {
      const tcp = tg.cpu_pct ?? 0;
      document.getElementById('t-cpu-val').textContent = tcp + '%';
      const tcBar = document.getElementById('t-cpu-bar');
      tcBar.style.width = tcp + '%';
      tcBar.className = 'bar-fill ' + barColor(tcp);

      if (tg.ram) {
        const trUsed = (tg.ram.used_mb / 1024).toFixed(1);
        const trTotal = (tg.ram.total_mb / 1024).toFixed(1);
        document.getElementById('t-mem-val').textContent = trUsed + ' GB';
        document.getElementById('t-mem-sub').textContent = 'of ' + trTotal + ' GB';
        const tmBar = document.getElementById('t-mem-bar');
        tmBar.style.width = tg.ram.pct + '%';
        tmBar.className = 'bar-fill ' + barColor(tg.ram.pct);
      }

      tg.gpus.forEach(g => {
        const pct = Math.round(g.mem_used / g.mem_total * 100);
        const el = document.getElementById(`t-vram${g.index}-val`);
        const bar = document.getElementById(`t-vram${g.index}-bar`);
        const sub = document.getElementById(`t-vram${g.index}-sub`);
        if (el) { el.textContent = g.mem_used + ' MiB'; }
        if (bar) { bar.style.width = pct + '%'; bar.className = 'bar-fill ' + barColor(pct); }
        if (sub) { sub.textContent = 'of ' + g.mem_total + ' MiB · ' + g.temp + '°C'; }
      });

      if (inf.model) {
        document.getElementById('t-model-val').textContent = inf.model;
        const ctxPart = inf.ctx ? Math.round(inf.ctx/1000) + 'K ctx' : '';
        const tokPart = inf.tok_s ? inf.tok_s + ' t/s' : '';
        document.getElementById('t-ctx-sub').textContent = [ctxPart, tokPart].filter(Boolean).join(' · ');
      }
    }

    // Overall dot — red if any agent or service is not active (catches both failed and inactive)
    const anyDown = [...d.agents, ...d.services].some(i => i.state !== 'active');
    document.getElementById('overall-dot').style.background = anyDown ? 'var(--red)' : 'var(--green)';
    document.getElementById('overall-dot').style.boxShadow = anyDown ? '0 0 10px var(--red)' : '0 0 10px var(--green)';

  } catch(e) {
    console.error(e);
  }
}

async function refreshTokens() {
  try {
    const r = await fetch('/api/tokens');
    const d = await r.json();
    if (d.error) return;
    document.getElementById('tok-today').textContent = d.today_total;
    document.getElementById('tok-today-sub').textContent = d.today_in + ' in · ' + d.today_out + ' out · ' + d.today_reqs.toLocaleString() + ' reqs';
    document.getElementById('tok-saved').textContent = d.today_cost;
    document.getElementById('tok-saved-sub').textContent = 'saved today vs Sonnet';
    document.getElementById('tok-week').textContent = '7-day: ' + d.week_total + ' tokens · ' + d.week_cost + ' saved';
  } catch(e) {}
}

function ageStr(age_h) {
  if (age_h === null || age_h === undefined) return 'never';
  if (age_h < 1) return Math.round(age_h * 60) + 'm ago';
  if (age_h < 24) return Math.round(age_h) + 'h ago';
  return Math.round(age_h / 24) + 'd ago';
}

function cronDot(status) {
  if (status === 'ok')      return '<div class="dot dot-ok"></div>';
  if (status === 'error')   return '<div class="dot dot-err"></div>';
  if (status === 'stale')   return '<div class="dot dot-unk"></div>';
  if (status === 'missing') return '<div class="dot dot-err" style="animation:pulse 1s infinite"></div>';
  if (status === 'never')   return '<div class="dot dot-never"></div>';
  return '<div class="dot dot-unk"></div>';
}

async function refreshCrons() {
  try {
    const r = await fetch('/api/crons');
    const d = await r.json();
    if (d.error) return;
    let html = '';
    let timerDividerAdded = false;
    let artifactDividerAdded = false;
    for (const j of d.jobs) {
      if (j.source === 'timer' && !timerDividerAdded) {
        html += `<div style="font-size:9px;letter-spacing:0.18em;text-transform:uppercase;color:var(--muted);padding:8px 14px 4px;border-top:1px solid var(--border);margin-top:4px;">system timers</div>`;
        timerDividerAdded = true;
      }
      if (j.source === 'artifact' && !artifactDividerAdded) {
        html += `<div style="font-size:9px;letter-spacing:0.18em;text-transform:uppercase;color:var(--muted);padding:8px 14px 4px;border-top:1px solid var(--border);margin-top:4px;">artifacts</div>`;
        artifactDividerAdded = true;
      }
      const ageLabel = j.source === 'artifact' && j.status === 'missing' ? 'MISSING' : ageStr(j.age_h);
      html += `<div class="cron-row">
        ${cronDot(j.status)}
        <span class="cron-name">${j.name}</span>
        <span class="cron-age" style="${j.status === 'missing' ? 'color:var(--red)' : ''}">${ageLabel}</span>
      </div>`;
    }
    document.getElementById('crons').innerHTML = html;
  } catch(e) {}
}

refresh();
refreshTokens();
refreshCrons();
setInterval(refresh, 15000);
setInterval(refreshTokens, 60000);
setInterval(refreshCrons, 300000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML
