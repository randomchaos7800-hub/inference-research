"""Publish-safe metadata from a requests_<ts>.jsonl.

The raw log holds every reader request in full: the agent's private system prompt plus ~100
dataset messages per call. Publishing it would expose the prompt and re-publish 34 MB of
LongMemEval content that anyone can regenerate from the dataset and the harness.

This keeps what the claims actually rest on — how many messages the reader received, which
tools it was offered, and whether the system prompt was stable across runs — as hashes and
counts. Prompt drift between runs stays detectable; the prompt itself is not published.
system_sha256_canonical sorts the prompt's paragraphs first, because the agent assembles two
always-on directives from a frozenset and their order varies per process (see README).

Usage: python3 requests_meta.py <in.jsonl> <out.jsonl>
"""
import hashlib, json, re, sys

def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def canon(s): return sha("\n".join(sorted(p.strip() for p in re.split(r"\n\s*\n", s) if p.strip())))

with open(sys.argv[1]) as f, open(sys.argv[2], "w") as o:
    for line in f:
        d = json.loads(line)
        msgs = d.get("messages") or []
        sysmsg = next((m.get("content") or "" for m in msgs if m.get("role") == "system"), "")
        o.write(json.dumps({
            "test_id": d.get("test_id"), "ts": d.get("ts"), "model": d.get("model"),
            "n_messages": d.get("n_messages"),
            "roles": [m.get("role") for m in msgs],
            "system_chars": len(sysmsg),
            "system_sha256": sha(sysmsg),
            "system_sha256_canonical": canon(sysmsg),
            "nonsystem_sha256": sha(json.dumps([m.get("content") for m in msgs if m.get("role") != "system"], default=str)),
            "tools": d.get("tools"),
        }) + "\n")
print(f"{sys.argv[1].split('/')[-1]} -> {sys.argv[2].split('/')[-1]}")
