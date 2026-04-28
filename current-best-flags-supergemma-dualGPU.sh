#!/bin/bash
# Best from autoresearch-supergemma-dualGPU
# tg512: 107.23 tok/s  |  pp2048: 3745 tok/s
# Generated: 2026-04-20 22:35
export PATH=/usr/local/cuda-12.8/bin:$PATH

exec /home/dino/llama.cpp/build/bin/llama-server \
  --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8081 \
  --n-gpu-layers 999 \
  --flash-attn on \
  -ctk f16 \
  -ctv f16 \
  --ctx-size 65536 \
  --ubatch-size 4096 \
  -b 2048 \
  --split-mode layer \
  --threads 8 \
  --threads-batch 8 \
  --cpu-range 0-7 \
  --cpu-range-batch 0-7 \
  --cpu-strict 1 \
  --mlock \
  --chat-template-kwargs '{"enable_thinking":false}' \
  --alias gemma4
