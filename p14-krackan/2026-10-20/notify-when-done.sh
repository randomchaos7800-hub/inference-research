#!/usr/bin/env bash
# Backstop: Telegram Dino when the P14 survey finishes or dies, independent of any Claude session.
while sleep 300; do
  st=$(ssh -o ConnectTimeout=10 cha0tikp14 'tail -1 ~/survey-20261020/raw/progress.log; systemctl --user is-active moe-survey' 2>/dev/null)
  [ -z "$st" ] && continue
  if grep -q ALL-DONE <<<"$st"; then
    ~/bin/tg-notify "P14 MoE survey: all runs finished ($(date +%H:%M)). Raw data is in. Claude is judging the quality transcripts and writing it up; results to follow."; exit 0
  fi
  if grep -qx "inactive\|failed" <<<"$(tail -1 <<<"$st")"; then
    ~/bin/tg-notify "P14 MoE survey STOPPED before finishing ($(date +%H:%M)). Last progress: $(head -1 <<<"$st")"; exit 1
  fi
done
