# Model Queue

## Active
- **Qwen3.6-27B INT4 AutoRound** (dense, GDN hybrid) — `~/vllm-genesis-start.sh` — alias `qwen3627b` — **systemd default (vllm-genesis.service, port 8022)**
  - vLLM 0.19.2rc1.dev228 + Genesis v7.53, gptq_marlin, MTP n=3, fp8 KV, ctx 32768
  - **83 t/s** (3.8x over llama.cpp), TP=2, 82% GMU (~26.8GB / 32GB)
  - Frank substrate: home-server frank.toml → `:8022/v1`, model alias `qwen3627b` (promoted 2026-04-27)
  - AIME 94.1, SWE-bench 77.2 — competitive with 2024 frontier closed models
  - Remaining blockers: FlashInfer CUDA graph PIECEWISE (not FULL) with spec-decode; ctx limited to 32K (OOM above)

## Revert
- **Qwen3.6-35B-A3B 65K** (MoE, 3B active) — `~/llama-server-qwen36-moe.sh` — alias `qwen36moe`
  - ctx 65536, f16 KV, 28.6GB VRAM, ~3.6GB headroom, ~100 t/s short ctx
  - Autoresearch confirmed optimal (0 improvements in 39 experiments across 2 passes)
  - 131K variant at `~/llama-server-qwen36-moe-131k.sh`
  - **To revert:** copy content of `~/llama-server-qwen36-moe.sh` into `~/llama-server-start.sh`, then `systemctl --user restart llama-server`

### vLLM bench results (2026-04-27)

**Best config found:** gptq_marlin + MTP n=3 + fp8 KV + 32K ctx → **83 t/s steady** (after Marlin warm-up)

| Config | t/s |
|---|---|
| llama.cpp baseline | 22 |
| vLLM gptq, MTP n=3 | ~65 |
| vLLM gptq_marlin, MTP n=3 | **83** ← best |
| vLLM gptq_marlin, MTP n=1 | 58 |

**Gate verdict: borderline fail** — 83 vs 85 t/s gate, 32K vs 100K ctx gate.
- t/s gap: FlashInfer forces CUDA graph downgrade to PIECEWISE mode with spec-decode (full mode would be faster)
- ctx gap: OOMs above 32K max-model-len at 82% GMU — activation workspace ~394 MiB short at higher lengths
- vLLM still 3.8x faster than llama.cpp, and quality higher than MoE (full 27B vs 3B active)

**Infra deployed** (2026-04-27):
- venv: `/opt/ai/vllm-env` (vLLM 0.19.2rc1.dev228, Genesis v7.53, gptq_marlin)
- Launch: `~/vllm-genesis-start.sh` → `vllm-genesis.service` on port 8022
- Revert model (llama.cpp): `systemctl --user start llama-server` (kills GPU sharing with vLLM)
- P8 stub fix: `token_capacity_kv_cache_groups` appended to kv_cache_utils.py

**Remaining blockers:**
1. CUDA graph PIECEWISE mode with FlashInfer+spec-decode — may need to disable FlashInfer sampler or use upstream fix
2. Context OOM above 32K — profile activation vs KV cache memory split at higher lengths

### vLLM path research (2026-04-23)

**Why 22 t/s isn't fixable in llama.cpp:** The GDN/DeltaNet hybrid layers have no optimized kernel path in llama.cpp. SSM state updates are the per-token bottleneck regardless of VRAM or tensor split config. This is architectural, not a tuning problem.

**Why vLLM can fix it:** Wasif Basharat (Medium, 2026-04-23) documented 85 t/s sustained / 106 t/s peak on Qwen3.6-27B dense using this exact architecture on a single RTX 3090. The unlocks stack:
1. **Lorbus AutoRound INT4 quant** — BF16 mtp.fc preserved (280 MiB, not 2.37 GB). Without this, vLLM's Qwen3_5MTP loader finds no mtp.fc.weight → 0% MTP acceptance.
2. **Genesis patches** (github.com/Sandermage/genesis-vllm-patches) — Monkey-patches TurboQuant hybrid gate + 19 downstream fixes. Without this, vLLM refuses to boot on DeltaNet/Mamba hybrid models with TurboQuant KV.
3. **tolist CUDA graph fix** — patch_tolist_cudagraph.py guards query_start_loc.tolist() calls during CUDA graph capture. Without this: crash at warmup OR 55% TPS penalty disabling cudagraphs. Article author has draft filed against vLLM #40069; patch not yet upstreamed.
4. **MTP n=3** — 97/95/91% per-position acceptance on this model. ~35% TPS multiplier essentially free.
5. **turboquant_3bit_nc KV** — 3-bit K+V with norm correction. Doubles usable context vs fp8.

**Target numbers on our hardware (dual 5060 Ti, TP=2):**
- Article baseline: 85 t/s / 125K ctx on single 3090 (24 GB)
- We have 32GB total across two cards — more VRAM, TP=2 bandwidth
- Expected: 85-100 t/s / 150K+ ctx (TP=2 TurboQuant untested per article author)
- Blackwell note: Lorbus's card says cudagraphs-off "needed on Blackwell" — same tolist bug, same fix applies

**Step-by-step:**
1. Check if Lorbus quant exists for 27B: `hf search Lorbus/Qwen3.6-27B` — if not, need to run AutoRound ourselves (few hours GPU time, requires keeping mtp.fc in BF16)
2. Clone Genesis: `git clone --depth 1 https://github.com/Sandermage/genesis-vllm-patches.git /opt/ai/vendor/genesis-vllm-patches/`
3. Get patch_tolist_cudagraph.py — contact article author or wait for upstream vLLM PR
4. Spin vLLM in Docker on port 8022 (leave llama.cpp running on 8081 untouched)
5. TP=2, turboquant_3bit_nc, MTP n=3, max-model-len 131000, gpu-memory-utilization 0.97
6. Bench tg512 vs current 100 t/s baseline; report context ceiling

**Decision gate:** If tg512 ≥ 85 t/s and ctx ≥ 100K, worth making this the Mike substrate. Dense 27B should have qualitatively better reasoning than MoE 3B-active even at same speed. If tg512 < 80 t/s, stay on current MoE.

**Blocker:** tolist patch availability. Article author hasn't upstreamed it yet. Watch vLLM issue #40069.
