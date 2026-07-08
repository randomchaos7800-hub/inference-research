# Lucebox Qwen3.5 Hardware-vs-Model Note

This is the follow-up pass after the first Lucebox experiment.

The question this time was narrower:

> Was the earlier result mostly a bad hardware/placement fit, or is the Lucebox stack still weak on this tower even when the draft path is placed better?

## Experiment Lock

Before running anything, the tower was put into hard experiment mode.

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

- short prompt decode speed: `15.70 tok/s`
- short prompt acceptance: `462/976 (47.3%)`
- medium prompt decode speed: `11.32 tok/s`
- medium prompt acceptance: `422/1488 (28.4%)`

### Draft on GPU0, split 1,1

- short prompt decode speed: `20.41 tok/s`
- short prompt acceptance: `501/656 (76.4%)`
- medium prompt decode speed: `11.32 tok/s`
- medium prompt acceptance: `422/1488 (28.4%)`

### Draft on GPU0, split 1,2

- short prompt decode speed: `20.38 tok/s`
- short prompt acceptance: `501/656 (76.4%)`

## Read

The important signal is decode throughput and draft acceptance.

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

## Receipt

Raw lock and status receipts:

- `logs/lucebox-experiment/20260615-qwen35-hardware-vs-model.json`
