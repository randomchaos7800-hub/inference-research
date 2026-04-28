#!/bin/bash
LOG=/home/dino/inference-research/autoresearch-vllm-27b-pass2-log.md
TSV=/home/dino/inference-research/autoresearch-vllm-27b-pass2-results.tsv
PID=$(pgrep -f "autoresearch-vllm-27b-pass2.py" | head -1)

echo "=== autoresearch pass2  $(date '+%H:%M:%S') ==="
[[ -z "$PID" ]] && echo "PROCESS : DEAD" || echo "PROCESS : running (PID $PID)"
echo "vLLM    : $(systemctl --user is-active vllm-genesis 2>/dev/null)"
echo "Current : $(grep '^## \[' "$LOG" 2>/dev/null | tail -1)"
echo "Last msg: $(grep '^\[' "$LOG" 2>/dev/null | tail -1)"
echo ""
echo "--- Results ---"
if [[ -f "$TSV" ]]; then
    awk -F'\t' '$5 != "0.00" || $8=="BASELINE"' "$TSV" | column -t -s $'\t' | sed 's/^/  /'
    echo ""
    TOTAL=$(awk -F'\t' 'NR>1 && $8!="BASELINE" && $8!="FINAL"' "$TSV" | wc -l)
    IMPROVED=$(awk -F'\t' 'NR>1 && $8~/IMPROVE/' "$TSV" | wc -l)
    TIMEOUT=$(awk -F'\t' 'NR>1 && $8=="TIMEOUT"' "$TSV" | wc -l)
    echo "  Done: $TOTAL/12  |  Improved: $IMPROVED  |  Timeout/OOM: $TIMEOUT"
    BEST=$(awk -F'\t' 'NR>1 && $8~/IMPROVE|BASELINE/ {if($5+0>max){max=$5+0; row=$0}} END{print row}' "$TSV" | cut -f2,5,8 | tr '\t' ' @ ')
    [[ -n "$BEST" ]] && echo "  Best : $BEST"
fi
