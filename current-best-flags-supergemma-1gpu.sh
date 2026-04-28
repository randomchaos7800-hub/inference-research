#!/bin/bash
# Best from autoresearch-supergemma single-GPU
# Gen: 71.1 tok/s

export PATH=/usr/local/cuda-12.8/bin:$PATH
export CUDA_VISIBLE_DEVICES=0

exec /home/dino/llama.cpp/build/bin/llama-server \
  --model /home/dino/models/supergemma4-26b-uncensored-fast-v2-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8081 \
  --n-gpu-layers 999 \
  --flash-attn on \
  -ctk q4_0 \
  -ctv q4_0 \
  --ctx-size 32768 \
  --ubatch-size 512 \
  --threads 4 \
  --threads-batch 4 \
  --cpu-range 0-7 \
  --cpu-range-batch 0-7 \
  --cpu-strict 1 --mlock \
  --override-tensor "blk\.(2[6-9])\..*exps.*=CPU" \
  --parallel \
  2 \
  --alias gemma4
