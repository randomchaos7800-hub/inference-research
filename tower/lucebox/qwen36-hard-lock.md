# Lucebox Qwen3.6 Hard-Lock Follow-Up

This note is the corrected rerun of the original Lucebox question.

The earlier pass drifted into a side branch and the tower kept reintroducing the production backend during experiments. This rerun fixes that by using the hard experiment lock first.

## Experiment Lock

The tower was put into hard experiment mode before any benchmark started:

- `local-proxy` switched to `openrouter`
- `vllm-backend.service` stopped and runtime-masked
- the tower-side research lock was set so `proxy-switch genesis` refused to run
- GPU state was verified clean

## Setup

- target: `Qwen3.6-27B-Q4_K_M.gguf`
- draft: `dflash-draft-3.6-q4_k_m.gguf`
- target split: `--target-gpus=0,1 --target-layer-split=1,1`
- draft placement tested here: `--draft-gpu=0`
- generation length: `512`
- prompt binaries:
  - short: `/tmp/q36_short.bin`
  - medium: `/tmp/q36_medium.bin`

## Results

### Short prompt

- prefill: `0.337 s`
- decode: `34.114 s`
- decode speed: `15.01 tok/s`
- draft steps: `60`
- accepted: `455/960 (47.4%)`
- avg commit/step: `8.53`

### Medium prompt

- prefill: `0.482 s`
- decode: `46.617 s`
- decode speed: `10.98 tok/s`
- draft steps: `95`
- accepted: `418/1520 (27.5%)`
- avg commit/step: `5.39`

## Read

This rerun answers the original question more cleanly:

- the lock worked
- the production backend stayed out of the way
- the qwen3.6 path still did not show a compelling decode-side win on this tower
- the short prompt acceptance stayed around the same band as the earlier runs
- the medium prompt remained slow on decode

## Conclusion

The corrected qwen3.6 rerun did not turn Lucebox into a production contender on this hardware.

What it did do is separate the signal from the experiment contamination:

- the tower was actually locked down
- the benchmark path was the intended qwen3.6 setup
- the result still does not justify switching the tower over

## Receipt

- [lucebox-qwen36-hard-lock.json](/home/dino/logs/lucebox-experiment/20260615-qwen36-hard-lock.json)
