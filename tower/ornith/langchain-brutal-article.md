# We Put a 35B Local Model Through LangChain's Cruelest Agent Benchmark

*2026-06-25 — cha0tiktower, dual RTX 5060 Ti*

On Thursday we spun up a new candidate on the tower: **Ornith-1.0-35B**, a GGUF quant running on two consumer RTX 5060 Ti cards in a home lab. Not a datacenter. Not a rented A100. Two $350-ish GPUs and llama.cpp.

The question wasn't whether it could chat. Every model can chat. The question was whether it could *agent* — call tools in sequence, pick the right function from a pile of options, and override its own training when the rules of the universe change mid-task.

LangChain published a benchmark for exactly this in late 2023. They called it tool-use evaluation, and the results were humbling even for GPT-4. Models that ace MMLU would loop endlessly typing the letter "a" thirty times when asked to type it once. Models that reason beautifully about math would ignore their calculator tools and answer from memory — getting the wrong answer in a universe where 2+2 equals 5.2.

We ran that benchmark. All four tasks. Sixty-six cases. Multi-turn agent loops until the model stopped or hit a thirty-turn cap. Then we ran the same harness against **DeepSeek V3.2** through OpenRouter on the same tower proxy, same day, same prompts.

## The Setup

**Ornith** served on port 8030 via llama.cpp, layer-split across both GPUs, 131k context, flash attention, q4 KV cache. About 11.7 GB VRAM per card. The fleet proxy on port 8010 stayed on OpenRouter the whole time — production path untouched.

**DeepSeek V3.2** ran through that fleet proxy (`:8010` → `https://openrouter.ai/api/v1`). Not loaded on GPU. Cloud inference via OpenRouter providers.

Harness: [langchain-brutal-eval.py](langchain-brutal-eval.py)

## The Typewriter Test

In the single-tool variant, the model gets one function: `type_letter(letter)`. To type "cat," it must call `type_letter("c")`, then `type_letter("a")`, then `type_letter("t")`, then stop. The dataset runs from single characters through ten-letter words like "communication."

LangChain's original blog showed GPT-4 failing on "keyboard" and looping on "aaaa."

**Ornith passed both suites perfectly.** 20/20 single-tool. 20/20 twenty-six-tool. ~3s per case locally.

**DeepSeek V3.2 scored 11/20 on single-tool.** It hit the thirty-turn cap on `a`, `aa`, `house`, `horse`, `school` — typing `aaaaaaaa...` and `househousehouse...`. It recovered on the 26-tool variant: 20/20.

## The Math Test

Multiverse math uses altered arithmetic. The system prompt says: do not use your training. Use the tools.

**DeepSeek: 18/18.** Perfect multi-hop composition.

**Ornith: 10/18.** Reliable on single-hop ops; fails when it "solves" from pretrained knowledge instead of chaining tools.

## The Relational Test

Eight questions over fake user/location/food tables. Multi-hop tool chains required.

**DeepSeek: 8/8.** Including Frank The Cat and Miami weather.

**Ornith: 6/8.** One llama-server 500 on quoted entity names; one no-tool answer on Miami.

## The Scoreboard

| Task | Ornith (local :8030) | DeepSeek V3.2 (OR :8010) |
|---|---:|---:|
| Typewriter (1 tool) | **20/20** | 11/20 |
| Typewriter (26 tools) | 20/20 | 20/20 |
| Multiverse Math | 10/18 | **18/18** |
| Relational Data | 6/8 | **8/8** |
| **Overall** | 56/66 (84.8%) | **57/66 (86.4%)** |
| Avg latency | **~3s** | ~22s |

DeepSeek wins by one point. The profiles are inverted.

## What This Means

Sequential tool composition — the thing that breaks frontier models in LangChain's own benchmark — is Ornith's strength. A 35B GGUF on consumer GPUs beats DeepSeek V3.2 on the exact task GPT-4 was shown failing. Locally. In three seconds.

Multi-hop reasoning over altered rules and relational data is DeepSeek's strength. It composes correctly when the answer contradicts training. It loops when you ask it to type "a" once.

**Ornith for the hot path.** Sequential tool agents. Local. Fast. No API burn.

**DeepSeek for the hard path.** Multi-hop reasoning. Relational queries. When correctness beats latency.

## Receipts (in-repo)

| File | Contents |
|---|---|
| [langchain-brutal-eval-ornith.json](langchain-brutal-eval-ornith.json) | Ornith per-case results |
| [langchain-brutal-eval-deepseek-v3.2.json](langchain-brutal-eval-deepseek-v3.2.json) | DeepSeek per-case results |
| [langchain-brutal-verdict.md](langchain-brutal-verdict.md) | Technical verdict + head-to-head |
| [humaneval-results.json](humaneval-results.json) | HumanEval 72/164 (43.9%) |
| [suite-20260625-170030.json](suite-20260625-170030.json) | Speed suite (~95–130 tok/s short ctx) |