#!/bin/bash
# Status report for autoresearch-vllm-27b.py — prints a compact summary
LOG=/home/dino/inference-research/autoresearch-vllm-27b-log.md
TSV=/home/dino/inference-research/autoresearch-vllm-27b-results.tsv
PID=$(pgrep -f "autoresearch-vllm-27b.py" | head -1)

echo "=== autoresearch-vllm-27b  $(date '+%H:%M:%S') ==="

# Process health
if [[ -z "$PID" ]]; then
    echo "PROCESS : DEAD ← loop has exited"
else
    echo "PROCESS : running (PID $PID)"
fi

# vLLM state
SVC=$(systemctl --user is-active vllm-genesis 2>/dev/null)
echo "vLLM    : $SVC"

# Current experiment from log
CURRENT=$(grep "^## \[" "$LOG" 2>/dev/null | tail -1)
echo "Current : ${CURRENT:-unknown}"

# What it is doing right now
LAST=$(grep "^\[" "$LOG" 2>/dev/null | tail -1)
echo "Last msg: ${LAST:-none}"

echo ""
echo "--- Results (this run only — skip rows with tg_median=0 for readability) ---"
if [[ -f "$TSV" ]]; then
    # Print header + rows from the most recent run (after last BASELINE line)
    BASELINE_LINES=$(grep -n "^0	baseline" "$TSV" | tail -1 | cut -d: -f1)
    if [[ -n "$BASELINE_LINES" ]]; then
        awk -v start="$BASELINE_LINES" 'NR==1 || NR>=start' "$TSV" \
          | awk -F'\t' '$5 != "0.00" || $8=="BASELINE"' \
          | column -t -s $'\t' \
          | sed 's/^/  /'
        echo ""
        # Summary counts
        TOTAL=$(awk -v start="$BASELINE_LINES" 'NR>=start && $8!="BASELINE"' "$TSV" | wc -l)
        IMPROVED=$(awk -v start="$BASELINE_LINES" 'NR>=start && $8~/IMPROVE/' "$TSV" | wc -l)
        TIMEOUT=$(awk -v start="$BASELINE_LINES" 'NR>=start && $8=="TIMEOUT"' "$TSV" | wc -l)
        echo "  Done: $TOTAL/21  |  Improved: $IMPROVED  |  Timeout/OOM: $TIMEOUT"
        BEST_LINE=$(awk -v start="$BASELINE_LINES" -F'\t' 'NR>=start && $8~/IMPROVE|BASELINE/ {if($5+0>max){max=$5+0; row=$0}} END{print row}' "$TSV")
        [[ -n "$BEST_LINE" ]] && echo "  Best : $(echo "$BEST_LINE" | cut -f2,5,8 | tr '\t' ' @ ')"
    fi
else
    echo "  No TSV yet"
fi
