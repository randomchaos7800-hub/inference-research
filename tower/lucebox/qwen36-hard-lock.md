# Lucebox Qwen3.6 Hard-Lock Follow-Up

This note is the corrected rerun of the original Lucebox question.

The earlier pass drifted into a side branch and the tower kept reintroducing the production backend during experiments. This rerun fixes that by using the hard experiment lock first.

## Experiment Lock

The tower was put into hard experiment mode before any benchmark started.

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

- decode speed: `15.01 tok/s`
- acceptance: `455/960 (47.4%)`

### Medium prompt

- decode speed: `10.98 tok/s`
- acceptance: `418/1520 (27.5%)`

## Read

The lock worked, the production backend stayed out of the way, and the qwen3.6 path still did not show a compelling decode-side win on this tower.

## Receipt

- `logs/lucebox-experiment/20260615-qwen36-hard-lock.json`
