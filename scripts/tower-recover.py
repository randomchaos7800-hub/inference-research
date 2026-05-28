#!/usr/bin/env python3
"""Tower recovery controller with staged remediation and verification."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TOWER = "100.120.50.35"
SSH_DEST = f"dino@{TOWER}"
PROXY_BASE = f"http://{TOWER}:8010"
VAULT = os.path.expanduser("~/.vault/vault.sh")
CHANNEL = "C0B651Z4C0P"

LOCK_PATH = Path("/tmp/tower-recover.lock")
STATE_PATH = Path.home() / ".cache" / "tower-recover" / "state.json"
PING_TIMEOUT = 3
HTTP_TIMEOUT = 5
SSH_TIMEOUT = 5
RECOVERY_WAIT = 120
BOOT_WAIT = 480
POWER_CYCLE_COOLDOWN = 1800

BACKEND_UNITS = {
    "nemotron": "nemotron.service",
    "genesis": "vllm-backend.service",
    "deepseek-r1": "vllm-backend.service",
    "aeon": "vllm-aeon.service",
}


def run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(cmd, 124, exc.stdout or "", exc.stderr or "timeout")


def vault_get(key: str) -> str:
    result = run([VAULT, "get", key], timeout=5)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def alert(message: str) -> None:
    token = vault_get("slack_kato_bot_token")
    if not token:
        return
    payload = json.dumps(
        {
            "channel": CHANNEL,
            "text": f"[tower-recover] {message}",
            "mrkdwn": True,
            "unfurl_links": False,
        }
    ).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def ping_ok() -> bool:
    result = run(["ping", "-c", "1", "-W", str(PING_TIMEOUT), TOWER], timeout=PING_TIMEOUT + 2)
    return result.returncode == 0


def ssh_ok() -> bool:
    result = run(
        ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={SSH_TIMEOUT}", SSH_DEST, "echo ok"],
        timeout=SSH_TIMEOUT + 2,
    )
    return result.returncode == 0 and result.stdout.strip() == "ok"


def fetch_json(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def health_ok() -> bool:
    payload = fetch_json(f"{PROXY_BASE}/health")
    return bool(payload and payload.get("status") == "ok")


def active_backend() -> str | None:
    payload = fetch_json(f"{PROXY_BASE}/active")
    if payload and payload.get("active"):
        return str(payload["active"])

    if not ssh_ok():
        return None

    cmd = "grep '^active = ' /home/dino/local-proxy/config.toml | head -1 | sed 's/^active = \"//; s/\"$//'"
    result = run(["ssh", SSH_DEST, cmd], timeout=10)
    return result.stdout.strip() or None


def units_for_backend(backend: str | None) -> list[str]:
    units = ["local-proxy.service"]
    if backend in BACKEND_UNITS:
        units.insert(0, BACKEND_UNITS[backend])
    return units


def wait_for(predicate, timeout: int, interval: int = 5) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def remote_units_active(units: list[str]) -> bool:
    cmd = "systemctl --user is-active " + " ".join(units)
    result = run(["ssh", SSH_DEST, cmd], timeout=20)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return result.returncode == 0 and lines and all(line == "active" for line in lines)


def remote_restart(backend: str | None) -> tuple[bool, str]:
    units = units_for_backend(backend)
    quoted = " ".join(units)
    cmd = (
        f"systemctl --user daemon-reload && "
        f"systemctl --user reset-failed {quoted} || true; "
        f"systemctl --user restart {quoted}"
    )
    result = run(["ssh", SSH_DEST, cmd], timeout=60)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return False, detail or "remote restart failed"
    return True, f"restarted {' '.join(units)}"


def power_cycle() -> tuple[bool, str]:
    result = run(["python3", os.path.expanduser("~/scripts/tower-plug.py"), "cycle", "--delay", "15"], timeout=60)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return False, detail or "power cycle failed"
    return True, "power-cycled tower plug"


def mark_action(state: dict, action: str) -> None:
    state["last_action"] = action
    state["last_action_ts"] = int(time.time())
    save_state(state)


def status_line() -> str:
    health = fetch_json(f"{PROXY_BASE}/health")
    active = fetch_json(f"{PROXY_BASE}/active")
    backend = None
    units = []
    unit_states = {}
    if active and active.get("active"):
        backend = str(active["active"])
        units = units_for_backend(backend)
    elif ssh_ok():
        backend = active_backend()
        units = units_for_backend(backend)
    if ssh_ok() and units:
        cmd = "systemctl --user is-active " + " ".join(units)
        result = run(["ssh", SSH_DEST, cmd], timeout=20)
        unit_states = dict(zip(units, [line.strip() for line in result.stdout.splitlines() if line.strip()]))
    return json.dumps(
        {
            "ping": ping_ok(),
            "ssh": ssh_ok(),
            "health": health,
            "active": active,
            "unit_states": unit_states,
        },
        indent=2,
        sort_keys=True,
    )


def recover(auto: bool) -> int:
    state = load_state()
    ping = ping_ok()
    ssh = ssh_ok() if ping else False
    backend = active_backend() if (ssh or health_ok()) else None
    units = units_for_backend(backend)
    if health_ok() and ((not ssh) or remote_units_active(units)):
        return 0

    if ping and ssh:
        ok, detail = remote_restart(backend)
        if ok and wait_for(lambda: health_ok() and remote_units_active(units), RECOVERY_WAIT):
            mark_action(state, "remote_restart")
            if auto:
                alert(f"Recovered tower without power cycle. Backend: `{backend or 'unknown'}`. Action: {detail}")
            return 0

    now = int(time.time())
    last_power = int(state.get("last_power_cycle_ts", 0))
    if now - last_power < POWER_CYCLE_COOLDOWN:
        remaining = POWER_CYCLE_COOLDOWN - (now - last_power)
        message = (
            f"Tower still unhealthy but power-cycle cooldown active for {remaining}s. "
            f"ping={ping} ssh={ssh} backend={backend or 'unknown'}"
        )
        if auto:
            alert(message)
        else:
            print(message, file=sys.stderr)
        return 1

    ok, detail = power_cycle()
    if not ok:
        if auto:
            alert(f"Tower recovery failed before reboot: {detail}")
        else:
            print(detail, file=sys.stderr)
        return 1

    state["last_power_cycle_ts"] = now
    mark_action(state, "power_cycle")

    if wait_for(ping_ok, BOOT_WAIT, interval=10) and wait_for(ssh_ok, 180, interval=10) and wait_for(health_ok, 240, interval=10):
        if auto:
            alert(f"Tower recovered after power cycle. Backend: `{active_backend() or 'unknown'}`")
        return 0

    if auto:
        alert("Tower power cycle completed but readiness checks still failed after boot.")
    return 1


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "recover"
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        if mode == "status":
            print(status_line())
            return 0
        if mode == "watchdog":
            return recover(auto=True)
        if mode == "recover":
            return recover(auto=False)
        if mode == "cycle":
            ok, detail = power_cycle()
            print(detail if ok else detail, file=sys.stdout if ok else sys.stderr)
            return 0 if ok else 1

        print("Usage: tower-recover.py [status|recover|watchdog|cycle]", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
