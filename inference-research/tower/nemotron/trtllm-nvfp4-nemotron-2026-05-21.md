# TRT-LLM NVFP4 Benchmark — Nemotron 3 Nano 30B A3B
**Date:** 2026-05-21  
**Hardware:** 2× RTX 5060 Ti 16GB (15.47 GiB usable), CUDA 13.0  
**Baseline:** llama.cpp Q4_K_M = 123.6 t/s  

---

## Goal

Benchmark Nemotron-3-Nano-30B-A3B-NVFP4 via TensorRT-LLM 1.2.1 to see if NVFP4 quantization + TRT-LLM outperforms llama.cpp Q4_K_M on the same hardware.

## Model

- **Path:** `/home/dino/models/Nemotron-3-Nano-30B-A3B-NVFP4` (~19 GB, 5 safetensors)
- **Architecture:** nemotron_h — hybrid Mamba/SSM + Attention (MoE)
- **Config:** 52 layers, 6 attention layers, 46 Mamba layers, hidden_size=2688, num_key_value_heads=2, max_position_embeddings=262144
- **Quantization:** NVFP4 (4-bit float, CUDA ≥ 12.9 required)

## Approach 1: Python LLM() API, tensor_parallel_size=2

**Script:** `bench-trtllm-nemotron.py` / initial `bench-trtllm-nvfp4.py`  
**Result:** OOM — "Tried to allocate 23.00 GiB"

**Root cause:** Standard TP=2 splits attention heads but cannot split Mamba/SSM layers. Mamba layers are replicated on each GPU, so GPU 0 carries nearly all model weights (~14.47 GB). CUDA graph pre-allocation then tries 23 GiB (based on max_position_embeddings=262144 × all layers × full MHA).

Attempts to fix via `KvCacheConfig(max_tokens=4096, free_gpu_memory_fraction=0.25)` and `max_num_tokens=512` did not help — the allocation probe fires before KV cache config is applied.

## Approach 2: trtllm-serve --backend _autodeploy, ep/bmm sharding

**Script:** `bench-trtllm-nvfp4.py` (rewritten)  
**Config:** Official NVIDIA `nano_v3.yaml` sharding strategy (`ep`/`bmm` instead of TP)

This is the correct approach per NVIDIA's official guide. ep/bmm sharding distributes MoE experts across GPUs and batch-splits Mamba operations.

**Result:** Hardware-limited OOM — 3 MB short.

```
GPU 0 capacity:    15.47 GB
Model weights:     14.47 GB  (Mamba layers replicated, not sharded)
CUDA runtime:       0.72 GB
Free after load:    0.017 GB (17 MB)
Allocation needed:  0.020 GB (20 MB)
Gap:               -3 MB
```

**Bugs fixed along the way:**
- `cuda_graph_config` → `cuda_graph_batch_sizes` (field renamed in 1.2.1)
- `mamba_ssm_cache_dtype` not valid in `KvCacheConfig` for 1.2.1 (removed)
- `compile_backend: torch` not valid → must be `torch-simple|torch-compile|torch-cudagraph|torch-opt`
- `PYTORCH_ALLOC_CONF` (wrong) → `PYTORCH_CUDA_ALLOC_CONF` (correct env var name)

Even with all fixes, ep/bmm sharding replicates Mamba weights on both GPUs. With 52 layers being ~89% Mamba, each GPU carries essentially the full model.

## Verdict

**TRT-LLM NVFP4 cannot run on 2× RTX 5060 Ti 16GB.**

The model requires ≥20 GB VRAM per GPU to initialize, regardless of sharding strategy. The Mamba-heavy architecture (89% Mamba layers) means weights cannot be meaningfully distributed across GPUs — both cards need the full weight set.

**NVIDIA's stated minimum for this model: ≥20 GB VRAM** (per HF model card).

## Winner

**llama.cpp Q4_K_M = 123.6 t/s**  
Running on `/home/dino/bin/nemotron-start.sh` → port 8022 → proxy :8010  
Config: `--n-gpu-layers 999 --ctx-size 65536 --threads 8 --cache-ram 0`

TRT-LLM is not a viable path for this model on this hardware. Revisit if/when 24GB+ GPUs are available.
