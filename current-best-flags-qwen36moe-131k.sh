#!/bin/bash
# Qwen3.6-35B-A3B 131K — best from autoresearch pass 2
# tg512: 97.34 tok/s  |  pp512: 2426 tok/s
# Generated: 2026-04-22 12:09
export PATH=/usr/local/cuda-12.8/bin:$PATH

exec /home/dino/llama.cpp/build/bin/llama-server \
  --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8081 \
  --n-gpu-layers 999 \
  --flash-attn on \
  -ctk q4_0 -ctv q4_0 \
  --ctx-size 131072 \
  --ubatch-size 4096 \
  -b 2048 \
  --split-mode layer \
  -nkvo 0 \
  -mg 0 \
  --threads 8 \
  --threads-batch 8 \
  --cpu-range 0-7 --cpu-range-batch 0-7 \
  --cpu-strict 1 \
  --mlock \
  --chat-template-kwargs '{"enable_thinking":false}' \
  --alias qwen36moe
