#!/bin/bash
# Qwen3.6-27B AutoRound INT4 — vLLM + Genesis — dual RTX 5060 Ti (32GB)
# Config: pass3 best high-ctx — 128K/0.90/auto — 80.04 t/s verified 2026-04-27
# Config: 2026-06-06 update — fp8 KV cache, qwen3_coder parser, SM_120 FlashInfer routing, DMABUF
# Config: {gpu_memory_utilization: 0.87, max_model_len: 65536, max_num_seqs: 2, max_num_batched_tokens: 4096, kv_cache_dtype: fp8, mtp_n: 3}
#
# Canonical copy: inference-research/tower/genesis/vllm-genesis-start.sh
# Live install:    /home/dino/bin/vllm-genesis-start.sh (cha0tiktower)

export PATH=/usr/local/cuda-13.0/bin:$PATH
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}:/usr/local/cuda-13.0/lib64
export CUDA_HOME=/usr/local/cuda-13.0

export VLLM_NO_USAGE_STATS=1
export VLLM_USE_FLASHINFER_SAMPLER=1
export VLLM_FLOAT32_MATMUL_PRECISION=high
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export VLLM_LOGGING_LEVEL=WARNING
export VLLM_MARLIN_USE_ATOMIC_ADD=1
export VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE=268435456
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512
export NCCL_P2P_DISABLE=1
export NCCL_BUFFSIZE=4194304
export NCCL_DMABUF_ENABLE=1
export OMP_NUM_THREADS=1
export CUDA_DEVICE_MAX_CONNECTIONS=8

# Force FlashInfer to route SM_120 native kernels instead of falling back to SM89
export FLASHINFER_CUDA_ARCH_LIST=12.0f
export FLASHINFER_FORCE_SM=120f
export FLASHINFER_DISABLE_VERSION_CHECK=1

export GENESIS_ENABLE_P60_GDN_NGRAM_FIX=1
export GENESIS_ENABLE_P60B_TRITON_KERNEL=1
export GENESIS_ENABLE_P64_QWEN3CODER_MTP_STREAMING=1
export GENESIS_ENABLE_P67_TQ_MULTI_QUERY_KERNEL=1
export GENESIS_ENABLE_P67B=1
export GENESIS_ENABLE_P70_AUTO_STRICT_NGRAM=1
export GENESIS_ENABLE_P72_PROFILE_RUN_CAP=1
export GENESIS_ENABLE_P74_CHUNK_CLAMP=1
export GENESIS_ENABLE_P77_ADAPTIVE_NGRAM_K=1
export GENESIS_ENABLE_P78_TOLIST_CAPTURE_GUARD=1
export GENESIS_ENABLE_P82=1
export GENESIS_P82_THRESHOLD_SINGLE=0.3
export GENESIS_BUFFER_MODE=shared
export GENESIS_PREALLOC_TOKEN_BUDGET=4096

/opt/ai/vllm-env/bin/python3 -m vllm._genesis.patches.apply_all

exec /opt/ai/vllm-env/bin/vllm serve \
  /home/dino/models/Qwen3.6-27B-int4-AutoRound \
  --quantization gptq_marlin \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.87 \
  --max-model-len 65536 \
  --kv-cache-dtype fp8 \
  --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --enable-chunked-prefill \
  --enable-prefix-caching \
  --dtype bfloat16 \
  --disable-custom-all-reduce \
  --trust-remote-code \
  --language-model-only \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml \
  --reasoning-parser qwen3 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":3}' \
  --prefix-caching-hash-algo xxhash \
  --api-key genesis-local \
  --served-model-name qwen3627b \
  --host 0.0.0.0 \
  --port 8022 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --disable-log-stats