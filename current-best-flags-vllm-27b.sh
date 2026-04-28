#!/bin/bash
# Best vLLM config — pass 2 — 2026-04-27 11:53
# Best t/s: 80.59

# gpu_memory_utilization = 0.82
# max_model_len = 32768
# max_num_seqs = 2
# max_num_batched_tokens = 4096
# kv_cache_dtype = auto
# mtp_n = 3
# NCCL_P2P_DISABLE = 1
# VLLM_USE_FLASHINFER_SAMPLER = 1
# OMP_NUM_THREADS = 1
# CUDA_DEVICE_MAX_CONNECTIONS = 8
# GENESIS_BUFFER_MODE = shared
# GENESIS_PREALLOC_TOKEN_BUDGET = 4096
# VLLM_MARLIN_USE_ATOMIC_ADD = 1
# VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE = 413138944
# NCCL_BUFFSIZE = 4194304
# PYTORCH_MAX_SPLIT_MB = 512

# Full launch script: ~/vllm-genesis-start.sh
# Source: autoresearch-vllm-27b-pass2.py
