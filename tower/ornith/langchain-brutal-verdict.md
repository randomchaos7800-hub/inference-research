# Ornith-1.0-35B — LangChain brutal tool-use verdict (2026-06-25)

Model: `deepreinforce-ai/Ornith-1.0-35B-GGUF:Q4_K_M`
Engine: llama.cpp `build-cuda120-nographs` on `:8030`
Hardware: 2× RTX 5060 Ti 16GB, layer-split TP (`--tensor-split 1,1`)

## TL;DR

Ornith clears the LangChain agent tool-use bar on the tasks that actually gate production agents:
**100% on both typewriter suites** (1-tool and 26-tool), **75% relational**, **56% multiverse math**.
Overall **56/66 (84.8%)** on the brutal multi-turn suite.

For companion/agent routing, this is a credible local tool-caller. The gaps are reasoning-budget
starvation on multi-hop math and one llama-server JSON-parse 500 on quoted entity names — not
fundamental inability to call tools.

## Serving config (receipt)

```bash
llama-server \
  -m .../ornith-1.0-35b-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8030 \
  --n-gpu-layers auto \
  --ctx-size 131072 \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --flash-attn on \
  --split-mode layer --tensor-split 1,1 \
  --no-warmup
```

Fleet safety during test: `local-proxy` on `openrouter` (`:8010` untouched).

## Benchmark protocol

Harness: [langchain-brutal-eval.py](langchain-brutal-eval.py)

Implements the four canonical LangChain tool-use tasks from
[Benchmarking Agent Tool Use](https://www.langchain.com/blog/benchmarking-agent-tool-use):

| Task | Cases | What it tests |
|---|---:|---|
| Typewriter (1 tool) | 20 | Sequential `type_letter` calls, `a` through `communication` |
| Typewriter (26 tools) | 20 | Alphabet tool selection, no args |
| Multiverse Math | 18 | Altered ops — must use tools, ignore pretrained math |
| Relational Data | 8 | Multi-hop DB-style tool chains |

Multi-turn agent loop until stop or 30 turns. Temperature 0.

Receipts:
- [langchain-brutal-eval-ornith.json](langchain-brutal-eval-ornith.json)
- [langchain-brutal-eval-ornith.log](langchain-brutal-eval-ornith.log)

## Results

| Task | Pass | Rate | Avg turns | Avg latency |
|---|---:|---:|---:|---:|
| Typewriter (1 tool) | 20/20 | 100% | 2.25 | 3.6s |
| Typewriter (26 tools) | 20/20 | 100% | 2.10 | 2.8s |
| Multiverse Math | 10/18 | 55.6% | 1.61 | 3.6s |
| Relational Data | 6/8 | 75.0% | 2.62 | 2.7s |
| **Overall** | **56/66** | **84.8%** | — | — |

### Context: why typewriter matters

LangChain's own benchmark blog uses typewriter to show that even GPT-4 fails on longer strings
(`keyboard`, `communication`) and over-calls on repeats (`aaaa`). Ornith passed every string on
both the 1-tool and 26-tool variants. That is the headline.

### Multiverse math failures (8)

All failures are multi-step composition or pretrained-knowledge override:

- `I ate 1 apple and 2 oranges every day for 7 days` — answered in text, 0 tool calls
- `multiply the result of (log of 100 to base 10) by 3` — 0 tool calls
- `calculate 101 to the power of 0.5` — 0 tool calls
- `ecoli divides every 20 minutes...` — 0 tool calls
- `convert 15 degrees to radians` — used standard math, not tools
- `(1+2) + 5`, `-(1 + 1)`, `Evaluate 1+2+3+4+5` — reasoning text, no tool chain

Single-hop ops (add, subtract, divide, power, pi, negate) pass reliably. Same pattern as
Nemotron's reasoning-budget gotcha: Ornith emits long `reasoning_content` traces before acting.
On simple 1-tool items it still finishes; on 3+ hop chains it sometimes "solves" from training.

**Mitigation:** force tool-use system prompt, raise `max_tokens`, or decompose multi-hop tasks.

### Relational failures (2)

| Case | Result | Cause |
|---|---|---|
| Frank The Cat + Ice Cream allergies | FAIL | llama-server 500: malformed tool-call JSON (`"Frank The Cat` missing close quote) |
| Miami weather | FAIL | Reasoning trace, no tool calls |

Passed: Alice color, Alice umbrella, Bob city, Pizza calories, Charlie email, Salad dairy.

## Other receipts (same session)

| Bench | Result | Notes |
|---|---|---|
| Speed suite (`full-inference-suite.py`) | ~95–130 tok/s | Short context, dual GPU |
| HumanEval (earlier run) | 72/164 (43.9%) | Code completion; markdown fence leakage hurts score |

## Production rules

1. **Tool calling works natively** — no grammar constraint required on `:8030`.
2. **Reasoning model** — expect `reasoning_content` before `tool_calls` or `content`. Budget accordingly (`max_tokens >= 512` for agent turns; prefer 1024+ on multi-hop).
3. **Entity names with quotes** — `"Frank The Cat"` can break tool-arg JSON parsing server-side. Sanitize or use IDs in tool schemas.
4. **Do not serve on `:8010` during experiment** — keep openrouter failover alive; benchmark candidate directly.

## Head-to-head: Ornith vs DeepSeek V3.2 (OpenRouter via :8010)

Same harness, same day. DeepSeek receipts:
[langchain-brutal-eval-deepseek-v3.2.json](langchain-brutal-eval-deepseek-v3.2.json)

| Task | Ornith (local :8030) | DeepSeek V3.2 (OR :8010) |
|---|---:|---:|
| Typewriter (1 tool) | **20/20 (100%)** | 11/20 (55%) |
| Typewriter (26 tools) | **20/20 (100%)** | 20/20 (100%) |
| Multiverse Math | 10/18 (56%) | **18/18 (100%)** |
| Relational Data | 6/8 (75%) | **8/8 (100%)** |
| **Overall** | 56/66 (84.8%) | **57/66 (86.4%)** |
| Avg latency | **~3s** | ~22s |

DeepSeek wins overall by one point, but the profiles are inverted:

- **Ornith owns sequential tool composition.** DeepSeek loops on `typewriter_1` — it hit the
  30-turn cap on `a`, `aa`, `house`, `horse`, `school`, `computer`, `dictionary`, `information`,
  typing repeated garbage (`aaaaaaaa...`, `househousehouse...`). Ornith passed all 20 cleanly.
  This is exactly the failure mode LangChain documented for GPT-4.

- **DeepSeek owns reasoning-heavy tool chains.** Perfect multiverse math (uses tools instead of
  pretrained knowledge) and perfect relational (including Frank The Cat and Miami, where Ornith
  failed). No API cost, but 10× slower.

**Routing implication:** Ornith for high-frequency sequential tool agents (local, fast, no API burn).
DeepSeek for multi-hop reasoning + relational queries where correctness beats latency.

## Bottom line

Ornith-35B Q4 on dual 5060 Ti is a strong local agentic candidate. It beats DeepSeek V3.2 and the
LangChain typewriter bar on sequential composition — the test cloud models famously fail. It is not
yet reliable on adversarial multi-hop math without prompt engineering. For Mike/Hermes-class tool
routing: Ornith for the hot path, DeepSeek for the hard path.