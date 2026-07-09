# Genesis + Qwen3.6-27B — Replication Guide

How to run **cha0tiktower production inference** exactly as deployed: **Qwen3.6-27B INT4 AutoRound** on **Genesis-patched vLLM 0.21.0**, dual **RTX 5060 Ti**, served through **local-proxy** on port **8010**.

**Last verified:** 2026-06-22 — live ~98 tok/s, ~98 ms TTFT (512-token completion benchmark).

---

## Architecture

```
Clients (harness, Mike, Hermes, bench scripts)
    │
    ▼
:8010  local-proxy          model alias: "local"
    │   /home/dino/local-proxy/proxy.py
    ▼
:8022  vllm-backend         model ID: "qwen3627b"
    │   Genesis-patched vLLM 0.21.0
    │   TP=2 across 2× RTX 5060 Ti 16GB
    ▼
/home/dino/models/Qwen3.6-27B-int4-AutoRound
```

**Rule:** Fleet clients never hit `:8022` directly. Always use `:8010/v1` with `model: "local"`.

---

## Hardware requirements

| Component | Production value |
|---|---|
| GPUs | 2× NVIDIA GeForce RTX 5060 Ti **16 GB** (Blackwell SM_120) |
| Effective VRAM | 32 GB across TP=2 |
| Interconnect | PCIe (no NVLink) — `NCCL_P2P_DISABLE=1` required |
| Driver | 580.126.09+ |
| CUDA toolkit | 13.0 at `/usr/local/cuda-13.0` |
| OS | Ubuntu 24.04 LTS |
| CPU | Intel Core Ultra 7 265F (not critical; any modern x86 works) |
| Disk | ~18 GB model + ~30 GB Python env |

Single-GPU replication is possible but requires retuning `tensor-parallel-size`, `gpu-memory-utilization`, and `max-model-len`. This guide documents the **verified dual-GPU** config.

---

## Model

| Field | Value |
|---|---|
| HuggingFace | [`Lorbus/Qwen3.6-27B-int4-AutoRound`](https://huggingface.co/Lorbus/Qwen3.6-27B-int4-AutoRound) |
| Local path | `/home/dino/models/Qwen3.6-27B-int4-AutoRound` |
| Base | `Qwen/Qwen3.6-27B` |
| Quant | AutoRound INT4 W4A16, group_size 128 |
| vLLM quant flag | `gptq_marlin` |
| Served name | `qwen3627b` |
| MTP head | Preserved in BF16 — enables self-speculative decoding |

```bash
huggingface-cli download Lorbus/Qwen3.6-27B-int4-AutoRound \
  --local-dir /home/dino/models/Qwen3.6-27B-int4-AutoRound
```

`--language-model-only` skips the vision tower. The weights are multimodal-capable but production serves text only.

---

## Software stack

| Layer | Path / version |
|---|---|
| Python venv | `/opt/ai/vllm-env` (Python 3.12.3) |
| vLLM | **0.21.0** |
| Genesis patches | [`Sandermage/genesis-vllm-patches`](https://github.com/Sandermage/genesis-vllm-patches) at `/opt/ai/vendor/genesis-vllm-patches` |
| Genesis package | `/opt/ai/vllm-env/lib/python3.12/site-packages/vllm/_genesis` (copied from vendor repo) |
| Start script | `/home/dino/bin/vllm-genesis-start.sh` — canonical copy in [vllm-genesis-start.sh](vllm-genesis-start.sh) |
| Proxy | `/home/dino/local-proxy/proxy.py` + [config.toml.example](config.toml.example) |

Genesis is **not** stock vLLM. It applies ~35+ runtime patches via `python3 -m vllm._genesis.patches.apply_all` before every serve. Upstream docs: vendor repo `INSTALL.md`, `CONFIGURATION.md`, `PATCHES.md`.

---

## Install from scratch (bare metal)

Matches the live cha0tiktower layout. For Docker, see the Genesis repo's `docker-compose.example.yml`.

### 1. Prerequisites

```bash
nvidia-smi                    # driver ≥ 580.126.09, both GPUs visible
nvcc --version                # CUDA 13.0
python3.12 --version          # 3.12.x

sudo apt install -y build-essential pkg-config libssl-dev libffi-dev \
  python3.12-venv python3.12-dev
```

### 2. Create vLLM environment

```bash
sudo mkdir -p /opt/ai
sudo chown "$USER:$USER" /opt/ai
python3.12 -m venv /opt/ai/vllm-env
source /opt/ai/vllm-env/bin/activate
pip install --upgrade pip wheel setuptools
```

Install the **same vLLM version** as production:

```bash
pip install vllm==0.21.0
# If the exact wheel is unavailable, try:
# pip install --pre vllm==0.21.0 --extra-index-url https://wheels.vllm.ai/nightly
```

Verify: `python3 -c "import vllm; print(vllm.__version__)"` → `0.21.0`

### 3. Install Genesis patches

```bash
git clone https://github.com/Sandermage/genesis-vllm-patches.git /opt/ai/vendor/genesis-vllm-patches
cd /opt/ai/vendor/genesis-vllm-patches

VLLM_DIR=$(python3 -c "import vllm, os; print(os.path.dirname(vllm.__file__))")
cp -r vllm/_genesis "$VLLM_DIR/_genesis"

python3 -c "from vllm import _genesis; print(_genesis.__file__)"
```

Use `cp` (not symlink) for a frozen production install. After `git pull` in the vendor repo, re-sync:

```bash
rsync -a /opt/ai/vendor/genesis-vllm-patches/vllm/_genesis/ "$VLLM_DIR/_genesis/"
```

### 4. Apply patches once (smoke test)

```bash
source /opt/ai/vllm-env/bin/activate
export GENESIS_ENABLE_P64_QWEN3CODER_MTP_STREAMING=1
export GENESIS_ENABLE_P67_TQ_MULTI_QUERY_KERNEL=1
export GENESIS_ENABLE_P82=1
python3 -m vllm._genesis.patches.apply_all
```

Exit code 0 = success. Check output for `applied` vs `skipped` per patch. Some skips are normal on SM_120 vs the upstream A5000 baseline.

**Warning:** `pip install --upgrade vllm` silently removes Genesis text-patches. Re-run `apply_all` after any vLLM upgrade.

### 5. Install start script and proxy

```bash
mkdir -p /home/dino/bin /home/dino/local-proxy /home/dino/models
cp inference-research/tower/genesis/vllm-genesis-start.sh /home/dino/bin/
chmod +x /home/dino/bin/vllm-genesis-start.sh

# Proxy: copy proxy.py from an existing tower, or deploy from your harness repo.
# Minimum config:
cp inference-research/tower/genesis/config.toml.example /home/dino/local-proxy/config.toml

/opt/ai/vllm-env/bin/pip install httpx uvicorn fastapi
```

### 6. systemd user services

Create `~/.config/systemd/user/vllm-backend.service`:

```ini
[Unit]
Description=Genesis production backend (Qwen3.6-27B INT4, port 8022)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=/home/dino/bin/vllm-genesis-start.sh
Restart=on-failure
RestartSec=15
LimitMEMLOCK=infinity
LimitSTACK=67108864
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vllm-backend

[Install]
WantedBy=default.target
```

Create `~/.config/systemd/user/local-proxy.service`:

```ini
[Unit]
Description=Local proxy — stable OpenAI-compatible inference endpoint
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
WorkingDirectory=/home/dino/local-proxy
ExecStart=/opt/ai/vllm-env/bin/python3 /home/dino/local-proxy/proxy.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=local-proxy

[Install]
WantedBy=default.target
```

Enable:

```bash
systemctl --user daemon-reload
systemctl --user enable --now vllm-backend.service local-proxy.service
loginctl enable-linger "$USER"   # survive logout/reboot
```

**Cold start timeline:** Genesis patch apply (~10s) → weight load (~30–60s) → torch.compile (~2–4 min first boot, ~30s warm) → CUDA graphs (~30–60s) → ready.

---

## Exact production flags

Full script: [vllm-genesis-start.sh](vllm-genesis-start.sh)

### Environment variables

| Category | Variables |
|---|---|
| CUDA | `PATH`, `LD_LIBRARY_PATH`, `CUDA_HOME` → CUDA 13.0 |
| vLLM core | `VLLM_NO_USAGE_STATS`, `VLLM_USE_FLASHINFER_SAMPLER`, `VLLM_ALLOW_LONG_MAX_MODEL_LEN`, `VLLM_WORKER_MULTIPROC_METHOD=spawn`, `VLLM_MARLIN_USE_ATOMIC_ADD`, `VLLM_FLASHINFER_WORKSPACE_BUFFER_SIZE=268435456` |
| Allocator | `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512` |
| Dual-GPU PCIe | `NCCL_P2P_DISABLE=1`, `NCCL_BUFFSIZE=4194304`, `NCCL_DMABUF_ENABLE=1`, `OMP_NUM_THREADS=1`, `CUDA_DEVICE_MAX_CONNECTIONS=8` |
| SM_120 FlashInfer | `FLASHINFER_CUDA_ARCH_LIST=12.0f`, `FLASHINFER_FORCE_SM=120f`, `FLASHINFER_DISABLE_VERSION_CHECK=1` |
| Genesis patches | `GENESIS_ENABLE_P60` through `P82` (see start script), `GENESIS_BUFFER_MODE=shared`, `GENESIS_PREALLOC_TOKEN_BUDGET=4096`, `GENESIS_P82_THRESHOLD_SINGLE=0.3` |

### vLLM serve arguments

```
vllm serve /home/dino/models/Qwen3.6-27B-int4-AutoRound
  --quantization gptq_marlin
  --tensor-parallel-size 2
  --gpu-memory-utilization 0.87
  --max-model-len 65536
  --kv-cache-dtype fp8
  --max-num-seqs 2
  --max-num-batched-tokens 4096
  --enable-chunked-prefill
  --enable-prefix-caching
  --dtype bfloat16
  --disable-custom-all-reduce
  --trust-remote-code
  --language-model-only
  --enable-auto-tool-choice
  --tool-call-parser qwen3_xml
  --reasoning-parser qwen3
  --speculative-config {"method":"mtp","num_speculative_tokens":3}
  --prefix-caching-hash-algo xxhash
  --api-key genesis-local
  --served-model-name qwen3627b
  --host 0.0.0.0
  --port 8022
  --default-chat-template-kwargs {"enable_thinking": false}
  --disable-log-stats
```

### Config rationale (do not change casually)

| Flag | Value | Why |
|---|---|---|
| `mtp num_speculative_tokens=3` | 3 | A/B test: removing MTP cut throughput ~50%. Qwen3.6 uses self-MTP, not a separate draft model. |
| `max-num-seqs` | 2 | Matches solo-operator + few concurrent agents. |
| `max-model-len` | 65536 | Current prod tradeoff (was 160K earlier). |
| `gpu-memory-utilization` | 0.87 | 0.90 caused OOM races on service restart before VRAM cleared. |
| `disable-custom-all-reduce` | on | Required for PCIe dual-GPU without NVLink. |
| `language-model-only` | on | Skips unused vision weights. |
| `enable_thinking: false` | default | Tool-calling agents; thinking mode adds latency. |

---

## Client usage

### Endpoints

| URL | Purpose |
|---|---|
| `http://<tower-ip>:8010/v1` | **Always use this** |
| `http://<tower-ip>:8010/health` | `{"status":"ok",...}` |
| `http://<tower-ip>:8010/active` | Current backend name + model |
| `http://<tower-ip>:8022/v1` | Backend direct — requires `Authorization: Bearer genesis-local` |

Production Tailscale IP: `tower`

### OpenAI-compatible request

```bash
curl -s http://tower:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "max_tokens": 50,
    "temperature": 0
  }'
```

No API key needed at the proxy layer — it injects `genesis-local` to the backend.

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://tower:8010/v1",
    api_key="unused",  # proxy does not require a key
)

r = client.chat.completions.create(
    model="local",
    messages=[{"role": "user", "content": "Write quicksort in Python."}],
    max_tokens=512,
    temperature=0,
)
print(r.choices[0].message.content)
```

---

## Verification

### Health

```bash
curl -s http://tower:8010/health
curl -s http://tower:8010/active
```

Expected: `active=genesis`, `model_effective=qwen3627b`, `backend_healthy=true`

### Throughput benchmark (canonical)

```bash
python3 /home/dino/scripts/bench-inference.py \
  --server-url http://tower:8010 \
  --model local \
  --prompt "Count from 1 to 200, one number per line, no commentary." \
  --max-tokens 512
```

Expected output fields: `gen_tps` ~95–100, `ttft_ms` ~90–110.

### GPU load check

```bash
ssh dino@tower 'nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv'
```

Both GPUs should show ~14–16 GB used when loaded.

### Daily perf log

```bash
/home/dino/scripts/perf-log.sh
# Writes ~/logs/perf/YYYY-MM-DD-<host>.json
```

---

## Operations

### Restart production

```bash
ssh dino@tower 'systemctl --user restart vllm-backend.service'
```

Wait for VRAM to clear before restarting if you killed vLLM manually — both GPUs should be <500 MiB used. Otherwise `gpu-memory-utilization` math fails on boot.

### Switch backends

```bash
ssh dino@tower 'proxy-switch genesis'      # production
ssh dino@tower 'proxy-switch openrouter'   # fleet safety during experiments
ssh dino@tower '/home/dino/bin/tower-return-prod'
```

### Experiment mode (benchmarks)

Before any tower benchmark that might touch production:

```bash
python3 /home/dino/scripts/tower-experiment-lock.py lock --minutes 180 --reason "my benchmark"
# ... run candidate on :8030 ...
python3 /home/dino/scripts/tower-experiment-lock.py unlock
```

See [../experiment-mode.md](../experiment-mode.md).

### Recovery

```bash
python3 /home/dino/scripts/tower-recover.py status
python3 /home/dino/scripts/tower-recover.py recover
```

Runbook: lab-internal (private ops repo); the recovery flow above is the complete public version.

---

## Stock vLLM fallback (no Genesis)

If Genesis is unavailable, a close approximation on the same hardware:

```bash
vllm serve Lorbus/Qwen3.6-27B-int4-AutoRound \
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
  --served-model-name qwen3627b \
  --host 0.0.0.0 --port 8022
```

Expect lower or unstable throughput on SM_120 without Genesis FlashInfer routing and MTP streaming patches. May need `--compilation-config '{"cudagraph_mode":"none"}'` on some vLLM builds.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Free memory on device ... less than desired GPU memory utilization` | Old vLLM process still holding VRAM | `pkill vllm`; wait until `nvidia-smi` shows <500 MiB per GPU; restart |
| `ImportError: No module named vllm._genesis` | Genesis not installed into venv | Re-run install step 3 |
| Many patches `failed` in apply_all log | vLLM version drifted from 0.21.0 | Pin vLLM; re-run apply_all; read per-patch skip reasons |
| Garbage output after vLLM upgrade | Patches wiped by pip | Re-run `apply_all` |
| Clients get 502 from proxy | Backend down or wrong `active` backend | `curl :8010/health`; `systemctl --user status vllm-backend` |
| Throughput dropped ~50% | MTP disabled | Restore `num_speculative_tokens=3` |
| SGLang migration temptation | SM_120 INT4 garbage-output bug #21132 | Stay on vLLM — see [../gdn-blackwell/sglang-vs-vllm-sm120.md](../gdn-blackwell/sglang-vs-vllm-sm120.md) |

---

## Related docs

- [../experiment-mode.md](../experiment-mode.md) — hard lock before benchmarks
- [../gdn-blackwell/sglang-vs-vllm-sm120.md](../gdn-blackwell/sglang-vs-vllm-sm120.md) — why vLLM over SGLang on SM_120
- [../benchmarks/mtp-batched-tokens-test-2026-05-09.md](../benchmarks/mtp-batched-tokens-test-2026-05-09.md) — MTP A/B receipt
- [`Sandermage/genesis-vllm-patches`](https://github.com/Sandermage/genesis-vllm-patches) — upstream patch docs

---

## Quick copy checklist

- [ ] 2× RTX 5060 Ti 16GB, driver 580+, CUDA 13.0
- [ ] `/opt/ai/vllm-env` with vLLM **0.21.0**
- [ ] Genesis `_genesis` package installed + `apply_all` succeeds
- [ ] Model at `/home/dino/models/Qwen3.6-27B-int4-AutoRound`
- [ ] Start script at `/home/dino/bin/vllm-genesis-start.sh`
- [ ] `vllm-backend.service` + `local-proxy.service` running
- [ ] `curl :8010/health` returns ok
- [ ] `bench-inference.py` reports ~95+ tok/s