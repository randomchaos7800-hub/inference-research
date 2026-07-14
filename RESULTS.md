# Results Index

One line per research program. Numbers link to the verdict docs; raw logs/TSVs sit
next to each verdict in the same directory.

| Program | Model / Focus | Headline | Verdict / receipts |
|---|---|---|---|
| [ornith](tower/ornith/) | Ornith-1.0-35B Q4_K_M, llama.cpp → AEON NVFP4, vLLM 0.23 | **84.8%** (56/66) LangChain brutal tool-use, 100% both typewriter suites (GGUF run; NVFP4 re-run 56/66 with 19/20 + 20/20); won sequential tool composition vs DeepSeek V3.2 (20/20 vs 11/20, ~10× faster) — DeepSeek won overall by one point (57/66); **production trial 2026-06-26 → 2026-07-03**, ~101 tok/s warm at 131K ctx | [verdict](tower/ornith/langchain-brutal-verdict.md) · [NVFP4 prod config](tower/ornith/aeon-nvfp4-prod.md) · [prod trial](tower/ornith/prod-trial.md) · [article](tower/ornith/langchain-brutal-article.md) |
| [genesis](tower/genesis/) | Qwen3.6-27B INT4 AutoRound, Genesis-patched vLLM 0.21 | **~97 tok/s warm** re-verified [2026-07-08](tower/genesis/warm-20260708.json); broke the GDN wall with MTP n=3; **current production backend** (May–June, restored 2026-07-03) | [replication guide](tower/genesis/README.md) |
| [nemotron](tower/nemotron/) | Nemotron 3 Nano 30B A3B (Mamba/SSM hybrid MoE) | **100% (22/22)** tool-calling hard-smoke (verdict-level; no per-case JSON); 117.34 t/s med / 117.60 peak on llama.cpp | [tool-call verdict](tower/nemotron/nemotron-toolcall-VERDICT.md) · [shootout receipt](tower/nemotron/nemotron-shootout-results.md) · [TRT-LLM NVFP4 notes](tower/nemotron/trtllm-nvfp4-nemotron-2026-05-21.md) |
| [gdn-blackwell](tower/gdn-blackwell/) | GDN architecture on SM120 (Blackwell) | Found and mapped the llama.cpp GDN wall; SGLang vs vLLM shootout on SM120 | [sglang-vs-vllm](tower/gdn-blackwell/sglang-vs-vllm-sm120.md) · [agentic behavior](tower/gdn-blackwell/qwen3-27b-agentic-behavior.md) |
| [lucebox](tower/lucebox/) | Speculative decoding, experiment isolation | Hardware-vs-model attribution under hard experiment locks | [qwen35 hw-vs-model](tower/lucebox/qwen35-hardware-vs-model.md) · [qwen36 hard lock](tower/lucebox/qwen36-hard-lock.md) |
| [frank](tower/frank/) | Autoresearch sweep (Frank workflow) | Multi-run TSV sweeps, loop-rebuild before/after | [log](tower/frank/autoresearch-frank-log.md) · [results TSV](tower/frank/autoresearch-frank-results.tsv) |
| [deepseek14b](tower/deepseek14b/) | DeepSeek 14B sweep | Autoresearch driver + runs | [driver](tower/deepseek14b/autoresearch-deepseek14b.py) |
| [prism-pro](tower/prism-pro/) | Prism Pro sweep | Autoresearch driver + runs | [driver](tower/prism-pro/autoresearch-prism-pro.py) |
| [benchmarks](tower/benchmarks/) | Shared tooling | Big-context bench, TRT-LLM NVFP4 bench, MTP batched-tokens test | [MTP test](tower/benchmarks/mtp-batched-tokens-test-2026-05-09.md) |
| [profiling](tower/profiling/) | Decode profiling, 2× RTX 5060 Ti | Spec decode +59%, CUDA graphs +60–75%, TP>PP; all-reduce sized at ~20% of token budget then **shelved** (prod-risk not justified for ~15%, reopen path documented) | [decode profile](tower/profiling/decode-profile-2x5060ti-20260710.md) |
| [moe](tower/moe/) | MoE playbook (pre-test) | Can sparse activation beat dense's quantization tradeoff on this hardware? 6-model, 7-phase experiment design ready to run — no live benchmarks yet | [design](tower/moe/EXPERIMENT-DESIGN.md) |

**Method:** every benchmark runs under [experiment-mode](tower/experiment-mode.md) —
production services stopped and disabled, VRAM drained and verified, one variable at
a time. Two models never share VRAM.
