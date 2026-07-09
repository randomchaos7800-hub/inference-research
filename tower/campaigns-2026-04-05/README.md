# April–May 2026 autoresearch campaigns (archive)

Raw receipts from the April–May 2026 optimization campaigns, ported from the repo's
pre-restructure flat layout so the full run record lives on one branch. Each campaign is
a scripted autoresearch loop: the `.py` file is the driver, the `-results.tsv` is one row
per iteration (config + measured throughput), and the `-log.md` is the running lab note.

Campaigns: Qwen3.6-35B MoE (single/dual GPU, 131K), SuperGemma, Gemma4 AWQ, GLM-4.7,
Llama 70B, DeepSeek 14B, Prism-Pro, AEON NVFP4, Genesis vLLM 0.21 passes, Nemotron,
Qwen2.5-7B (M4 baseline), and the model-eval TSV snapshots.

Highlights that graduated to verdict docs:
- Nemotron shootout → [../nemotron/nemotron-shootout-results.md](../nemotron/nemotron-shootout-results.md)
  (the 117.34 t/s median / 117.60 t/s peak receipt, 2026-05-20)
- Genesis passes → [../genesis/](../genesis/) replication guide
- Counting method for the public run total → [../../COUNT.md](../../COUNT.md)

Endpoints in these files use scrubbed placeholders (`tower`, `home-server`); the numbers
are untouched. Raw stdout/server logs from these campaigns are retained offline.
