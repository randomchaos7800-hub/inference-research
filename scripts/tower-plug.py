#!/usr/bin/env python3
"""TP-Link Kasa HS103P2 control for cha0tiktower power management.

Bypasses python-kasa's broken IOT.KLAP → KlapTransport routing.
Forces KlapTransportV2 (required for new_klap: 1 devices).

Credentials come from the local vault by default:
  kasa_username
  kasa_password
  kasa_plug_tower_ip

Usage:
    tower-plug status
    tower-plug on
    tower-plug off
    tower-plug cycle [--delay N]   # off, wait N sec (default 10), on
"""
import asyncio
import os
import subprocess
import sys

from kasa import DeviceConfig, Credentials
from kasa.deviceconfig import DeviceConnectionParameters, DeviceFamily, DeviceEncryptionType
from kasa.transports.klaptransport import KlapTransportV2
from kasa.protocols.iotprotocol import IotProtocol
from kasa.iot import IotPlug

VAULT = os.path.expanduser("~/.vault/vault.sh")


def vault_get(key: str, fallback: str = "") -> str:
    if not os.path.exists(VAULT):
        return fallback
    result = subprocess.run(
        [VAULT, "get", key],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return fallback
    return result.stdout.strip() or fallback


HOST = os.environ.get("KASA_PLUG_TOWER_IP") or vault_get("kasa_plug_tower_ip", "10.0.0.30")
USERNAME = os.environ.get("KASA_USERNAME") or vault_get("kasa_username")
PASSWORD = os.environ.get("KASA_PASSWORD") or vault_get("kasa_password")


async def get_plug() -> IotPlug:
    if not USERNAME or not PASSWORD:
        raise RuntimeError("missing Kasa credentials; set env or populate vault keys kasa_username and kasa_password")
    creds = Credentials(USERNAME, PASSWORD)
    conn = DeviceConnectionParameters(
        device_family=DeviceFamily.IotSmartPlugSwitch,
        encryption_type=DeviceEncryptionType.Klap,
        login_version=2,
        https=False,
        http_port=80,
    )
    config = DeviceConfig(host=HOST, credentials=creds, connection_type=conn)
    transport = KlapTransportV2(config=config)
    protocol = IotProtocol(transport=transport)
    return IotPlug(HOST, config=config, protocol=protocol)


async def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    delay = 10
    if "--delay" in sys.argv:
        idx = sys.argv.index("--delay")
        delay = int(sys.argv[idx + 1])

    plug = await get_plug()
    await plug.update()

    if cmd == "status":
        state = "ON" if plug.is_on else "OFF"
        print(f"Tower plug ({HOST}): {state} | alias={plug.alias}")
    elif cmd == "on":
        await plug.turn_on()
        print(f"Tower plug: turned ON")
    elif cmd == "off":
        await plug.turn_off()
        print(f"Tower plug: turned OFF")
    elif cmd == "cycle":
        print(f"Tower plug: cycling (off → {delay}s → on)...")
        await plug.turn_off()
        print("OFF. Waiting...")
        await asyncio.sleep(delay)
        await plug.turn_on()
        print("ON.")
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

    try:
        await plug.protocol._transport._http_client.client.close()
    except Exception:
        pass


asyncio.run(main())
