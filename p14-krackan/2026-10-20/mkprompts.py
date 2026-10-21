"""Write the three speed-pass prompts. Natural text, not a repeated sentence: a repeated
prompt inflates MTP draft acceptance (the generation just continues the pattern)."""
import json, sys
sys.path.insert(0, sys.argv[1])
import scenarios as S

journal = [o for rx, o, ec in S.SCEN["slowboot"]["fixtures"] if rx.startswith("journalctl -b|")][0]
soul = open(sys.argv[1] + "/soul.md").read()
# This journal text runs ~2.1 chars/token (measured: 17k+soul chars -> 8926 tok, 118k -> 56437 tok on Qwen).
# Targets: loaded ~5k tok, deep ~32k tok. n_prompt is recorded per run, so the exact count per tokenizer is in the data.
loaded = soul + "\n\n" + journal[:7300] + "\n\nSummarize what happened during this boot, in plain prose."
deep = soul + "\n\n" + (journal * 2)[:64000] + "\n\nSummarize what happened during this boot, in plain prose."
base = {"n_predict": 128, "cache_prompt": False, "ignore_eos": True, "temperature": 0, "seed": 42}
for name, p in [("clean", "Explain, in a short paragraph, why token generation on an integrated GPU is limited by memory bandwidth."),
                ("loaded", loaded), ("deep", deep)]:
    json.dump(dict(base, prompt=p), open(f"/tmp/sb-{name}.json", "w"))
