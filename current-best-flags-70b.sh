#!/bin/bash
# BEST from autoresearch-70b loop
# Gen: 55.6 tok/s

export PATH=/usr/local/cuda-12.8/bin:$PATH

exec /home/dino/llama.cpp/build/bin/llama-server \
  --model /home/dino/models/Llama-3.3-70B-Instruct-IQ4_XS.gguf \
  --host 0.0.0.0 --port 8081 \
  --n-gpu-layers 60 \
  --tensor-split 1,1 \
  --flash-attn on \
  -ctk q4_0 \
  -ctv q4_0 \
  --ctx-size 65536 \
  --ubatch-size 1024 \
  --threads 8 \
  --threads-batch 8 \
  --cpu-range 0-7 \
  --cpu-range-batch 0-7 \
  --cpu-strict 1 \
  --mlock \
  --alias llama70b
