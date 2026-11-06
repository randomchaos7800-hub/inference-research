#!/usr/bin/env bash
# Dino 2026-11-06: speed answered the question; cut the run before the quality pass.
P=/home/dino/bench/2026-11-06/raw/progress.log
until grep -qE "speed done|speed exited nonzero|START quality|ALL-DONE" "$P" 2>/dev/null; do sleep 15; done
systemctl --user stop model-survey-1106
pkill -x llama-server 2>/dev/null; sleep 3; pkill -9 -x llama-server 2>/dev/null
echo "$(date -Is) STOPPED-AFTER-SPEED (Dino: quality pass skipped; speed settled it)" >> "$P"
[ -x "$HOME/bin/tg-notify" ] && "$HOME/bin/tg-notify" "P14 Groot survey: speed pass complete, run stopped before the quality pass as agreed ($(date +%H:%M))." >/dev/null 2>&1 || true
