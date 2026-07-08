# Lucebox Qwen3.5 Hardware-vs-Model Note

This is the follow-up pass after the first Lucebox experiment.

The question this time was narrower:

> Was the earlier result mostly a bad hardware/placement fit, or is the Lucebox stack still weak on this tower even when the draft path is placed better?

## Experiment Lock

Before running anything, the tower was put into hard experiment mode:

- `local-proxy` switched to `openrouter`
- `vllm-backend.service` was stopped and runtime-masked
- the tower-side research lock was set so `proxy-switch genesis` refused to run
- GPU state was verified clean before the first benchmark

Lock status now lives in:

- [experiment-mode.md](/home/dino/tower/experiment-mode.md)

## Setup

- target: `Qwen3.5-27B-Q4_K_M.gguf`
- draft: `dflash-draft-3.6-q4_k_m.gguf`
- target split: `--target-gpus=0,1 --target-layer-split=1,1`
- alternate split test: `--target-layer-split=1,2`
- prompt binaries:
  - short: `/tmp/q35_short.bin`
  - medium: `/tmp/q35_medium.bin`
- generation length: `512`
- main comparisons:
  - draft on GPU1
  - draft on GPU0

## Results

### Draft on GPU1, split 1,1

Short prompt:

- prefill: `1.359 s`
- decode: `32.603 s`
- decode speed: `15.70 tok/s`
- draft steps: `61`
- accepted: `462/976 (47.3%)`
- avg commit/step: `8.39`

Medium prompt:

- prefill: `0.421 s`
- decode: `45.233 s`
- decode speed: `11.32 tok/s`
- draft steps: `93`
- accepted: `422/1488 (28.4%)`
- avg commit/step: `5.51`

### Draft on GPU0, split 1,1

Short prompt:

- prefill: `0.184 s`
- decode: `25.085 s`
- decode speed: `20.41 tok/s`
- draft steps: `41`
- accepted: `501/656 (76.4%)`
- avg commit/step: `12.49`

Medium prompt:

- prefill: `0.419 s`
- decode: `45.214 s`
- decode speed: `11.32 tok/s`
- draft steps: `93`
- accepted: `422/1488 (28.4%)`
- avg commit/step: `5.51`

### Draft on GPU0, split 1,2

Short prompt:

- prefill: `0.184 s`
- decode: `25.123 s`
- decode speed: `20.38 tok/s`
- draft steps: `41`
- accepted: `501/656 (76.4%)`
- avg commit/step: `12.49`

## Read

The important signal is not TTFT here. The useful signal is decode throughput and draft acceptance.

What changed materially:

- moving the draft from GPU1 to GPU0 roughly doubled short-prompt acceptance
- short-prompt decode throughput improved from `15.70 tok/s` to about `20.4 tok/s`
- weighted layer split `1,2` did not materially change the GPU0 result

What did not change much:

- the medium prompt stayed around `11.32 tok/s` in both GPU0 and GPU1 cases
- the weighted split did not rescue the medium prompt

## Conclusion

This looks less like a simple “wrong split” problem and more like a mixed result:

- draft placement matters
- the stack does get noticeably better when the draft sits on GPU0
- layer-split weights themselves were not the magic lever
- medium-prompt decode is still much slower than the production vLLM path

So the clean takeaway is:

1. The earlier experiment was not just bad because of missing lock discipline.
2. The hardware layout does matter.
3. Even with better draft placement, Lucebox on this tower is still not obviously competitive with the current production backend.

## Receipt

Raw lock and status receipts:

- [lucebox-qwen35-hardware-vs-model.json](/home/dino/logs/lucebox-experiment/20260615-qwen35-hardware-vs-model.json)
