#!/usr/bin/env bash
# Tower watchdog — staged recovery for proxy/backend failures, power-cycle only as last resort.
set -euo pipefail

exec /usr/bin/python3 "$HOME/scripts/tower-recover.py" watchdog
