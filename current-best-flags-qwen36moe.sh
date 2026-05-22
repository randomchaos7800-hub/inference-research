#!/bin/bash
# Qwen3.6-35B-A3B — best from autoresearch
# tg512: 100.24 tok/s  |  pp512: 2436 tok/s
# Generated: 2026-04-22 11:42
export PATH=/usr/local/cuda-12.8/bin:$PATH

exec /home/dino/llama.cpp/build/bin/llama-server \
  --model /home/dino/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf \
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
  --alias qwen36moe
