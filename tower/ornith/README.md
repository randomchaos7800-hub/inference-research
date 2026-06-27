# Ornith-1.0-35B (Tower)

Candidate local agent model — DeepReinforce Ornith 35B GGUF on llama.cpp.

**Prod trial:** fleet `:8010` → `ornith` since 2026-06-26. See [prod-trial.md](prod-trial.md).

## Verdict

[langchain-brutal-verdict.md](langchain-brutal-verdict.md) — full receipts from 2026-06-25 eval.

**Summary:** 56/66 (84.8%) on LangChain tool-use suite. 100% typewriter (both variants).

## Article

[langchain-brutal-article.md](langchain-brutal-article.md) — narrative recap for publication.

## Re-run eval

On tower while Ornith is live on `:8030`:

```bash
python3 /home/dino/inference-research/tower/ornith/langchain-brutal-eval.py \
  --endpoint http://127.0.0.1:8030/v1/chat/completions \
  --model local \
  --output /home/dino/logs/model-tests/ornith-35b-fullsuite/langchain-brutal-eval.json
```

Quick subset: add `--quick`.

DeepSeek head-to-head via fleet proxy:

```bash
python3 /home/dino/inference-research/tower/ornith/langchain-brutal-eval.py \
  --endpoint http://tower:8010/v1/chat/completions \
  --model local \
  --output /home/dino/logs/model-tests/deepseek-v3.2-langchain/langchain-brutal-eval.json
```

## Receipts (versioned)

| File | Contents |
|---|---|
| [langchain-brutal-eval.py](langchain-brutal-eval.py) | Harness |
| [langchain-brutal-eval-ornith.json](langchain-brutal-eval-ornith.json) | Ornith LangChain eval |
| [langchain-brutal-eval-deepseek-v3.2.json](langchain-brutal-eval-deepseek-v3.2.json) | DeepSeek V3.2 head-to-head |
| [humaneval-results.json](humaneval-results.json) | HumanEval 72/164 |
| [suite-20260625-170030.json](suite-20260625-170030.json) | Speed suite |