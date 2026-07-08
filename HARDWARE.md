# Hardware

Everything in this repo ran on one of two machines. No datacenter GPUs, no cloud
instances, no dev kits — parts anyone can buy.

## The tower — primary inference rig (2026-04 →)

| Component | Spec |
|---|---|
| CPU | Intel Core Ultra 7 265F — 20c/20t, 5.3 GHz boost |
| GPUs | **2× RTX 5060 Ti 16 GB GDDR7** (Blackwell, SM_120) — 32 GB total VRAM |
| RAM | 32 GB DDR5 |
| Storage | 2 TB PCIe 4.0 NVMe |
| Base | CyberPowerPC GXi3400BSTV17 (off-the-shelf prebuilt) |

The second GPU landed 2026-04-20: baseline went 74 → 107+ tok/s and opened
tensor-parallel (TP=2) work. Much of the interesting research here is about what
SM_120 does and doesn't support in each serving stack — see
[gdn-blackwell](tower/gdn-blackwell/) and the [genesis replication
guide](tower/genesis/README.md).

## The mini-PC — where it started (CPU era)

| Component | Spec |
|---|---|
| Machine | Beelink EQI12 |
| CPU | Intel i5-1235U (10c/12t, laptop-class) |
| RAM | 32 GB |
| GPU | none — pure CPU inference |

10.4 tok/s on Gemma-4 26B with chronic swap thrashing. The point wasn't the number;
it was learning the whole stack before spending a dollar on GPUs.

## Serving stacks used across the repo

- **llama.cpp** — multiple builds tracked per experiment (CUDA 12.x variants noted in logs)
- **vLLM** — 0.20–0.23, including Genesis-patched builds for GDN/MTP on SM_120
- **SGLang** — SM_120 shootout, see [sglang-vs-vllm-sm120](tower/gdn-blackwell/sglang-vs-vllm-sm120.md)
- **TensorRT-LLM** — NVFP4 experiments, see [benchmarks](tower/benchmarks/)

Exact flags, versions, and environment for the production deployment are in the
[genesis replication guide](tower/genesis/README.md).
