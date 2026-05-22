#!/bin/bash
# CURRENT BEST: Experiment 8 — Partial expert GPU offload + P-core threading
# Gen: ~69.8 tok/s (+115% vs baseline 32.4)
# Prompt: ~292 tok/s warm (+294% vs baseline 74.1)
# Context: 32768 (unchanged), KV: q8_0 (unchanged)
# VRAM: ~15,785 MiB / 16,311 MiB (55 MiB headroom — avoid concurrent GPU workloads!)
# As of 2026-04-18

export PATH=/usr/local/cuda-12.8/bin:$PATH

exec /home/dino/llama.cpp/build/bin/llama-server \
  --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf \
  --host 127.0.0.1 \
  --port 8081 \
  --n-gpu-layers 999 \
  --override-tensor "blk\.(2[4-9])\..*exps.*=CPU" \
  --flash-attn on \
  -ctk q8_0 \
  -ctv q8_0 \
  --mlock \
  --ctx-size 32768 \
  --ubatch-size 1024 \
  --threads 8 \
  --threads-batch 8 \
  --cpu-range 0-7 \
  --cpu-range-batch 0-7 \
  --cpu-strict 1 \
  --chat-template-kwargs '{"enable_thinking":false}' \
  --alias gemma4
