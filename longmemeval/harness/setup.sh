#!/usr/bin/env bash
# LongMemEval setup — installs deps and verifies dataset access
set -euo pipefail

MIKE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="$MIKE_ROOT/venv"

echo "=== LongMemEval Setup ==="
source "$VENV/bin/activate"

echo "→ Installing dependencies..."
pip install -q datasets huggingface_hub

echo "→ Downloading dataset (xiaowu0162/longmemeval-cleaned, split s)..."
python - <<'EOF'
from huggingface_hub import hf_hub_download
import json, pathlib

dest_dir = pathlib.Path("/tmp/longmemeval_data")
dest_dir.mkdir(parents=True, exist_ok=True)

path = hf_hub_download(
    repo_id="xiaowu0162/longmemeval-cleaned",
    filename="longmemeval_s_cleaned.json",
    repo_type="dataset",
    local_dir=str(dest_dir),
)
print(f"  Downloaded to: {path}")

with open(path) as f:
    data = json.load(f)

print(f"  Examples: {len(data)}")
ex = data[0]
total_turns = sum(len(s) for s in ex.get("haystack_sessions", []))
print(f"  Fields: {list(ex.keys())}")
print(f"  Sample question_type: {ex.get('question_type')}")
print(f"  Sample turns: {total_turns} across {len(ex.get('haystack_sessions',[]))} sessions")
print(f"  Sample Q: {str(ex.get('question',''))[:80]}")
print(f"  Sample A: {str(ex.get('answer',''))[:60]}")

from collections import Counter
types = Counter(d['question_type'] for d in data)
print(f"  Question types: {dict(types)}")
EOF

echo ""
echo "=== Setup complete ==="
echo ""
echo "Run the benchmark:"
echo "  cd $MIKE_ROOT"
echo "  source venv/bin/activate && source <(vault)"
echo "  python tests/longmemeval/runner.py --limit 25"
echo ""
echo "Options:"
echo "  --limit N         number of test cases (default 25)"
echo "  --split s         s (default, ~550 turns) | oracle (long)"
echo "  --tasks TYPE      all | single-session-user | multi-session | temporal-reasoning | ..."
echo "  --no-extract      skip extraction (tests context recall only)"
echo "  --no-llm-judge    skip LLM judge scoring (exact match only, faster)"
