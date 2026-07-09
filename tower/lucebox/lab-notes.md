# Lucebox Tower Lab Notes

## Question

Run a reproducible benchmark on `cha0tiktower` to answer one question:

> Is `Luce-Org/lucebox-hub` worth adding as a tower inference path for consumer-hardware speculative decoding?

This is research, not a production change. The tower remains fleet-serving first.

## Context

The Lucebox repo is a speculative inference server with:

- custom kernels
- speculative prefill and speculative decoding
- OpenAI-compatible serving on a local port
- model-specific optimization paths
- explicit support for Qwen 3.6-27B class targets and DFlash drafters

The public README claims its default server path is a Qwen 3.6-27B Q4_K_M target with a Q4_K_M DFlash drafter, built from the `server/` tree with CMake and submodules, and benchmarked with `DDTree` / `fa-window` settings on reference hardware.

## Hardware

`cha0tiktower` is a harder target than Lucebox's reference machine:

- dual `NVIDIA GeForce RTX 5060 Ti 16GB`
- `32 GB` total VRAM, split across two cards
- Intel Core Ultra 7 265F
- Ubuntu 24.04.4 LTS

That makes the tower useful in two ways:

1. It can prove whether Lucebox fits a real consumer dual-GPU setup.
2. It can tell us whether the speculative stack is actually better than the current `vLLM` backend on the same machine.

## Boundaries

- Do not replace the production proxy backend for the experiment.
- Do not point fleet traffic at Lucebox.
- Keep `:8010` stable.
- Use a separate port, default `:8000`, for Lucebox.
- Restore the tower to `genesis` when done.

## Baseline

Current production tower state:

- proxy: `http://tower:8010`
- active backend: `genesis`
- production model id: `qwen3627b`
- current backend class: `vllm`
- current benchmark path: `bench-inference.py` via the tower proxy

The experiment should compare Lucebox against that baseline, not against abstract claims from the repo.

## Expected Outcomes

1. Lucebox will improve TTFT on short prompts by reducing first-token latency.
2. Lucebox will improve decode throughput on medium prompts if the drafter and verify path fit the tower's VRAM layout.
3. If the reference Qwen 3.6-27B target is too large for one 16 GB card, the experiment will surface that quickly and honestly.

## Test Matrix

Run the matrix in this order:

1. Target-only smoke test
2. Default Lucebox target + drafter
3. Draft-disabled fallback
4. Budget sweep
5. Context-window sweep
6. Client compatibility smoke tests

Recommended first-pass sweep:

- `--ddtree` on
- `--ddtree-budget 22` as the initial point
- `--fa-window 2048` as the initial point
- `DFLASH27B_KV_TQ3=1` for the first pass
- draft residency variants only if the default pass is stable

If the default pass fails memory fit, fall back to a smaller or target-only run rather than forcing an unstable configuration.

## Build Notes

```bash
git clone --recurse-submodules https://github.com/Luce-Org/lucebox-hub
cd lucebox-hub
cmake -B server/build -S server -DCMAKE_BUILD_TYPE=Release
cmake --build server/build --target dflash_server -j
```

The repository documents `server/` as the native C++ HTTP server path, with no PyTorch dependency for the server binary itself.

## Model Assets

Use the repo's documented default target pair as the first attempt:

- target: `unsloth/Qwen3.6-27B-GGUF` with `Qwen3.6-27B-Q4_K_M.gguf`
- drafter: `Lucebox/Qwen3.6-27B-DFlash-GGUF` with `dflash-draft-3.6-q4_k_m.gguf`

Store them in the repo-local `server/models/` and `server/models/draft/` locations so the server auto-discovers them.

## Test Procedure

### 1. Launch target-only

Start the server without a draft model first. Confirm:

- the binary starts cleanly
- `/v1/models` responds
- a short prompt returns successfully

### 2. Launch default speculative mode

```bash
DFLASH27B_KV_TQ3=1 \
./server/build/dflash_server server/models/Qwen3.6-27B-Q4_K_M.gguf \
  --draft server/models/draft/dflash-draft-3.6-q4_k_m.gguf \
  --ddtree --ddtree-budget 22 --fa-window 2048 --port 8000
```

### 3. Benchmark with the same prompt suite we already use

Use the existing tower benchmark harness against the Lucebox port so the comparison stays apples-to-apples:

```bash
python3 bench-inference.py (lab script; flags documented inline) \
  --server-url http://127.0.0.1:8000 \
  --model <lucebox-model-name> \
  --prompt "What is 2+2?" \
  --max-tokens 32
```

Repeat with:

- a medium prompt
- a long-context prompt
- at least three runs per configuration

## Metrics Captured

Capture the same fields for every run:

- build commit or tag
- exact command line
- target model file
- drafter model file
- `ttft_ms`
- `tokSOut`
- `tokSTotal`
- completion tokens
- elapsed wall time
- peak VRAM
- GPU utilization if available
- pass/fail status

Also note whether the server used:

- target-only
- speculative decoding
- draft residency changes
- a reduced context window

## Measurements

Date: `2026-06-15`

### Build And Fit

- Clone/build succeeded on `cha0tiktower` from the Lucebox repo root.
- The server binary built cleanly with CMake:
  - `cmake -B server/build -S server -DCMAKE_BUILD_TYPE=Release`
  - `cmake --build server/build --target dflash_server -j2`
- Model files downloaded cleanly into:
  - `server/models/Qwen3.6-27B-Q4_K_M.gguf`
  - `server/models/draft/dflash-draft-3.6-q4_k_m.gguf`
- Target-only mode fit on the tower across both RTX 5060 Ti cards.

### Target-Only Run

Launch:

```bash
CUDA_VISIBLE_DEVICES=0,1 \
./server/build/dflash_server server/models/Qwen3.6-27B-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8000 --max-ctx 8192 \
  --target-devices cuda:0,cuda:1 --target-layer-split 1,1 \
  --peer-access --model-name qwen3.6-27b-target
```

Observed server state:

- `/health` returned `ok`
- `/v1/models` returned `qwen3.6-27b-target`
- log confirmed `target_shards = cuda:0 cuda:1`
- log also confirmed the draft path was `(none)`

Measured prompts:

- Short prompt `What is 2+2?`
  - `ttft_ms`: `16953.0`
  - `completion_tokens`: `8`
  - `end_to_end_tps`: `0.5`
- Medium prompt `Explain transformer attention in 3 sentences.`
  - `ttft_ms`: `17348.1`
  - `completion_tokens`: `87`
  - `end_to_end_tps`: `4.0`

Server log note:

- prefill was the bottleneck on the short prompt
- decode landed around `2.2 tok/s` on the short prompt and `19.7 tok/s` on the medium prompt

### Speculative Run

Launch:

```bash
DFLASH27B_KV_TQ3=1 \
CUDA_VISIBLE_DEVICES=0,1 \
./server/build/dflash_server server/models/Qwen3.6-27B-Q4_K_M.gguf \
  --draft server/models/draft/dflash-draft-3.6-q4_k_m.gguf \
  --host 127.0.0.1 --port 8000 --max-ctx 8192 \
  --target-devices cuda:0,cuda:1 --target-layer-split 1,1 \
  --peer-access --ddtree --ddtree-budget 22 --fa-window 2048 \
  --draft-swa 2048 --draft-device cuda:0 --draft-residency request-scoped \
  --model-name qwen3.6-27b-dflash
```

Observed server state:

- `/health` returned `ok`
- `/v1/models` returned `qwen3.6-27b-dflash`
- the server warned that `fa_window > 0` drops system prompt and tool definitions from attention at long contexts
- the server logged `draft_residency = request-scoped`

Measured prompts:

- Short prompt `What is 2+2?`
  - `ttft_ms`: `1483.8`
  - `completion_tokens`: `10`
  - `end_to_end_tps`: `6.7`
- Medium prompt `Explain transformer attention in 3 sentences.`
  - `ttft_ms`: `1026.8`
  - `completion_tokens`: `85`
  - `end_to_end_tps`: `7.2`
  - `gen_tps`: `7.9`

### Production Baseline

Current tower baseline, measured through the production path before the experiment:

- `ttft_ms`: `97.3`
- `tokSOut`: `69.3`
- `tokSTotal`: `64.3`
- submission status on LocalMaxxing: `APPROVED`

### Decision

Lucebox is a valid research backend on this tower, but it is not a production replacement here.

Why:

- it fit and served requests successfully
- it did not beat the current production backend on latency or throughput
- its speculative mode still landed far behind the vLLM baseline on the actual production path

### Restore Note

The restore helper initially timed out during the backend restart because Lucebox was still holding the GPUs. After stopping the Lucebox experiment service, the tower was manually returned to `genesis` by flipping `the proxy config (config.toml on the lab gateway)` back to `active = "genesis"` and restarting `local-proxy.service`.

Final checked state:

- proxy active backend: `genesis`
- production backend: `vllm-backend.service` running
- Lucebox remained isolated on port `8000`

## Full Sweep

Raw results:

- [`baseline-genesis.json`](baseline-genesis.json)
- [`lucebox-fa2048.json`](lucebox-fa2048.json)
- [`lucebox-fa0.json`](lucebox-fa0.json)

### Baseline `qwen3627b`

| Prompt | TTFT | End-to-end TPS | Decode TPS |
|---|---:|---:|---:|
| short_math | `97.8 ms` | `43.8` | `94.4` |
| medium_attention | `97.8 ms` | `64.2` | `69.3` |
| code_csv | `105.6 ms` | `71.8` | `76.3` |
| agentic_json | `110.5 ms` | `42.4` | `79.7` |

### Lucebox `fa-window=2048`

| Prompt | TTFT | End-to-end TPS | Decode TPS |
|---|---:|---:|---:|
| short_math | `1483.9 ms` | `6.7` | `n/a`* |
| medium_attention | `1012.9 ms` | `7.2` | `7.9` |
| code_csv | `1811.1 ms` | `8.5` | `9.7` |
| agentic_json | `2025.3 ms` | `10.4` | `n/a`* |

### Lucebox `fa-window=0`

| Prompt | TTFT | End-to-end TPS | Decode TPS |
|---|---:|---:|---:|
| short_math | `1486.5 ms` | `6.7` | `n/a`* |
| medium_attention | `1016.9 ms` | `7.2` | `7.9` |
| code_csv | `1811.9 ms` | `8.5` | `9.7` |
| agentic_json | `2023.6 ms` | `10.4` | `n/a`* |

`*` The decode TPS is artificially inflated when generation collapses into a single streamed content chunk. Use TTFT and end-to-end TPS for comparison on those prompts.

### What Changed

- `fa-window=0` did not materially change throughput on this suite.
- Lucebox stayed far behind the production `vLLM` baseline on TTFT and end-to-end throughput.
- The medium and code prompts are the cleanest apples-to-apples comparison here because they include meaningful generation length.

## Receipt Trail

This section is the post-ready receipt trail for the experiment as of `2026-06-15`.

### Environment

- tower: `cha0tiktower`
- GPUs: `2x NVIDIA GeForce RTX 5060 Ti 16GB`
- production baseline model: `qwen3627b`
- Lucebox model: `qwen3.6-27b-dflash`
- Lucebox target file: `server/models/Qwen3.6-27B-Q4_K_M.gguf`
- Lucebox draft file: `server/models/draft/dflash-draft-3.6-q4_k_m.gguf`

### Baseline Receipt

- file: [`baseline-genesis.json`](baseline-genesis.json)
- median TTFT on short_math: `97.8 ms`
- median TTFT on medium_attention: `97.8 ms`
- median end-to-end TPS on medium_attention: `64.2`
- median end-to-end TPS on code_csv: `71.8`
- median end-to-end TPS on agentic_json: `42.4`

### Lucebox Receipt, `fa-window=2048`

- file: [`lucebox-fa2048.json`](lucebox-fa2048.json)
- median TTFT on short_math: `1483.9 ms`
- median TTFT on medium_attention: `1012.9 ms`
- median end-to-end TPS on medium_attention: `7.2`
- median end-to-end TPS on code_csv: `8.5`
- median end-to-end TPS on agentic_json: `10.4`

### Lucebox Receipt, `fa-window=0`

- file: [`lucebox-fa0.json`](lucebox-fa0.json)
- median TTFT on short_math: `1486.5 ms`
- median TTFT on medium_attention: `1016.9 ms`
- median end-to-end TPS on medium_attention: `7.2`
- median end-to-end TPS on code_csv: `8.5`
- median end-to-end TPS on agentic_json: `10.4`

### Interpretation So Far

- The tower baseline is much faster on this exact prompt set.
- The Lucebox dual-GPU split is working, but it is not competitive on latency here.
- `fa-window=0` did not unlock a meaningful improvement.
- The next variables worth testing are draft placement and target layer split, because the current run appears to be constrained by placement rather than basic correctness.

### Follow-up Placement Receipts

Draft on GPU1, target split still `1,1`:

- file: [`lucebox-draft-gpu1.json`](lucebox-draft-gpu1.json)
- median TTFT on short_math: `1485.9 ms`
- median TTFT on medium_attention: `1015.2 ms`
- median end-to-end TPS on medium_attention: `7.2`
- median end-to-end TPS on code_csv: `8.5`
- median end-to-end TPS on agentic_json: `10.4`

Target split `1,2`, draft still on GPU1:

- file: [`lucebox-split-1-2-gpu1.json`](lucebox-split-1-2-gpu1.json)
- median TTFT on short_math: `1516.2 ms`
- median TTFT on medium_attention: `1042.7 ms`
- median end-to-end TPS on medium_attention: `7.2`
- median end-to-end TPS on code_csv: `8.5`
- median end-to-end TPS on agentic_json: `10.4`

### Placement Readout

- moving the draft to GPU1 did not materially improve the run
- shifting the target split to `1,2` also did not materially improve the run
- the bottleneck is therefore not just draft-side placement or a trivial split imbalance
- on this tower, the current Lucebox path behaves like a research backend rather than a production candidate

## Decision Criteria

Promote Lucebox as a serious candidate only if one of these is true:

- it materially improves TTFT with no stability regression
- it materially improves decode throughput on the same prompt suite
- it is the only path that fits a target class the current backend cannot serve well

Reject or park it if:

- it fails fit on the tower with the documented target pair
- it is unstable under repeated runs
- it underperforms the current `vLLM` baseline after accounting for warmup and prompt length

## Public Post Angle

If the numbers are good, the post should tell a method story, not a hype story.

Suggested structure:

1. What we tested
2. Why this stack mattered
3. What the tower hardware actually is
4. How the server was built
5. The benchmark matrix
6. The result table
7. The failure modes
8. The conclusion

Do not lead with the throughput number. Lead with the setup and the constraints.

## What To Archive

Keep these artifacts:

- exact build command
- server launch command
- benchmark command
- raw JSON results
- notes on any OOMs or fit failures
- screenshots or terminal captures only if they add clarity
- the final comparison table versus the current tower backend

## Immediate Next Steps

1. Clone and build Lucebox on the tower.
2. Run target-only smoke tests.
3. Run the default speculative configuration.
4. Benchmark against the current `vLLM` baseline.
5. Decide whether the result is a usable backend, an interesting dead end, or a future comparison candidate.
