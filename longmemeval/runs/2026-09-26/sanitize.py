"""Apply this repo's path convention to run artifacts before publishing.

The 2026-09-21 public logs rewrite the agent's real tree to ~/agent / ~/agent-memory. This does
the same for the 2026-09-26 run and also rewrites the reasoning-journal directory name, so the
public record shows the shape of a tool call without publishing the operator's layout.
Idempotent. Usage: python3 sanitize.py <file> ...
"""
import re, sys

SUBS = [
    (r"/home/dino/mike-memory", "~/agent-memory"),
    (r"/home/dino/mike", "~/agent"),
    (r"~/mike-memory", "~/agent-memory"),
    (r"~/mike", "~/agent"),
    (r"/home/dino/\.nvm/versions/node/v[0-9.]+/bin/npx", "~/.nvm/.../npx"),
    (r"LIGHTHOUSE", "JOURNAL"),
    (r"dino_model\.md", "operator_model.md"),
    (r"/home/dino", "~"),           # bare home dir, e.g. a tool arg of base_path=/home/dino
    (r"\bdino\b", "operator"),      # the operator's username in tool args and log lines
]
for path in sys.argv[1:]:
    s = open(path).read(); orig = s
    for pat, rep in SUBS: s = re.sub(pat, rep, s)
    if s != orig:
        open(path, "w").write(s); print(f"  sanitized {path.split('/')[-1]}")
