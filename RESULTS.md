# Results Index

One line per research program. Numbers link to the verdict docs; raw logs/TSVs sit
next to each verdict in the same directory.

| Program | Model / Focus | Headline | Verdict / receipts |
|---|---|---|---|
| [ornith](tower/ornith/) | Ornith-1.0-35B Q4_K_M, llama.cpp → AEON NVFP4, vLLM 0.23 | **84.8%** (56/66) LangChain brutal tool-use, 100% both typewriter suites; beat DeepSeek V3.2 head-to-head; **in production** since 2026-06-26, ~101 tok/s warm at 131K ctx | [verdict](tower/ornith/langchain-brutal-verdict.md) · [NVFP4 prod config](tower/ornith/aeon-nvfp4-prod.md) · [prod trial](tower/ornith/prod-trial.md) · [article](tower/ornith/langchain-brutal-article.md) |
| [genesis](tower/genesis/) | Qwen3.6-27B INT4 AutoRound, Genesis-patched vLLM 0.21 | **~98 tok/s, ~98 ms TTFT** verified 2026-06-22; broke the GDN wall with MTP n=3; ran production May–June | [replication guide](tower/genesis/README.md) |
| [nemotron](tower/nemotron/) | Nemotron 3 Nano 30B A3B (Mamba/SSM hybrid MoE) | **100% (22/22)** tool-calling hard-smoke; 117.6 tok/s hardware peak on llama.cpp | [tool-call verdict](tower/nemotron/nemotron-toolcall-VERDICT.md) · [TRT-LLM NVFP4 notes](tower/nemotron/trtllm-nvfp4-nemotron-2026-05-21.md) |
| [gdn-blackwell](tower/gdn-blackwell/) | GDN architecture on SM120 (Blackwell) | Found and mapped the llama.cpp GDN wall; SGLang vs vLLM shootout on SM120 | [sglang-vs-vllm](tower/gdn-blackwell/sglang-vs-vllm-sm120.md) · [agentic behavior](tower/gdn-blackwell/qwen3-27b-agentic-behavior.md) |
| [lucebox](tower/lucebox/) | Speculative decoding, experiment isolation | Hardware-vs-model attribution under hard experiment locks | [qwen35 hw-vs-model](tower/lucebox/qwen35-hardware-vs-model.md) · [qwen36 hard lock](tower/lucebox/qwen36-hard-lock.md) |
| [frank](tower/frank/) | Autoresearch sweep (Frank workflow) | Multi-run TSV sweeps, loop-rebuild before/after | [log](tower/frank/autoresearch-frank-log.md) · [results TSV](tower/frank/autoresearch-frank-results.tsv) |
| [deepseek14b](tower/deepseek14b/) | DeepSeek 14B sweep | Autoresearch driver + runs | [driver](tower/deepseek14b/autoresearch-deepseek14b.py) |
| [prism-pro](tower/prism-pro/) | Prism Pro sweep | Autoresearch driver + runs | [driver](tower/prism-pro/autoresearch-prism-pro.py) |
| [benchmarks](tower/benchmarks/) | Shared tooling | Big-context bench, TRT-LLM NVFP4 bench, MTP batched-tokens test | [MTP test](tower/benchmarks/mtp-batched-tokens-test-2026-05-09.md) |

**Method:** every benchmark runs under [experiment-mode](tower/experiment-mode.md) —
production services stopped and disabled, VRAM drained and verified, one variable at
a time. Two models never share VRAM.
