I'll search X since 2026-10-21 for new local MoEs and small dense models, plus llama.cpp Vulkan changes and Ryzen AI 300 reports, then check the claims against Hugging Face and GitHub.Several names fit the size window. I'll verify Flint, Air-26B-A4B, Clover, Xing, Groot, MiMo-V2.6, and the llama.cpp Vulkan changes against primary pages.Groot, Flint, and Clover are the size fits with agent claims. Next I’ll check their cards, the Vulkan llama.cpp notes, and Strix Point reports, and drop anything that is only fast on a discrete GPU.Two models are worth a harness run. Nothing in this window has a measured decode above 34 tok/s on an 860M-class iGPU, and your 34 tok/s already includes multi-token prediction (MTP).

The box is Krackan Point: Radeon 860M, 8 compute units, DDR5-5600 at about 90 GB/s. Strix Point (890M, 16 compute units) is the same memory class, so only prefill should differ. Strix Halo (Ryzen AI Max+ 395, Radeon 8060S, ~200–256 GB/s) is a different machine. Halo tok/s do not transfer.

## Worth benchmarking

### 1. Groot-19B-A3B-261023 — GrootTeam

| | |
|---|---|
| Released | 27 Oct 2026 (card updated that day; Hugging Face page 29 Oct) |
| Size | 19B total, ~3B active, plus a 0.4B MTP layer. 40 layers: 10 full attention, 30 linear attention. 128 routed experts, 8 active, plus 1 shared. 262,144 context, YaRN toward ~1M |
| GGUF | Yes. The card lists a Q4_K_M edition at 11.7 GB. Architecture tag is `qwen3_5_moe`, the same family as your current model |
| Licence | Apache 2.0. Text and image. Native tool calls (`qwen3_coder` parser) |

**Claim (org, primary).** It starts from Qwen3.6-35B-A3B, was post-trained on fewer than 0.1B tokens, and the card says it beats both Qwen3.6-35B-A3B and Gemma-4-26B-A4B on 12 of 16 benchmarks. Examples they publish: Terminal-Bench 2.1 **52.10 vs 43.82 / 26.52**, NL2Repo-Bench **35.65 vs 28.77 / 16.55**, LongBench v2 **62.03 vs 48.12 / 47.99**. Average across the 16 is **41.44 vs 38.08 vs 30.05**. They also say 23.1% fewer output tokens than Qwen3.6-35B-A3B. Thinking mode, temp 1.0, top_p 0.95, top_k 20. Confirmed on the model card: https://huggingface.co/GrootTeam/Groot-19B-A3B-261023

**X.** Hugging Face staff post, not the lab: https://x.com/AdinaYakup/status/2115073334018768954 (27 Oct). User report, not versus Qwen and not on an iGPU: https://x.com/PaulGug/status/2117210360302211491 (2 Nov). On a 10 GB RTX 3080, GooGZ AI scored Groot with reasoning on at 269/300 against MiniCPM-V 4.7 at 273/300 with reasoning off, and 208/300 with reasoning off. Decode there was 52 tok/s at 51k context versus 20 for MiniCPM, with different quants and CPU offload. That speed is a discrete-GPU offload result.

**On your box.** Active width matches Qwen, so short-context decode should land near your current number, not clearly above it. The practical upside is the 11.7 GB file, the smaller long-context KV (only 10 full-attention layers), and fewer output tokens if the card holds. The MTP head is documented for vLLM and SGLang (`qwen3_next_mtp`). Nobody has shown that head working in llama.cpp Vulkan. If it does not, you lose the MTP boost that produces your 34 tok/s.

### 2. Recursive Flint — Recursive Superintelligence

| | |
|---|---|
| Released | Blog 18 Oct 2026; weights and launch posts 21 Oct 2026 |
| Size | 39.8B total, ~2.5B active including the output head (~2.2B for the body). 49 layers: 2 dense, then 47 MoE. 256 experts, top-6, plus 1 shared. 35 layers are a 513-token sliding window; 14 are full attention. 262,144 context (blog says up to 512k, recommends staying inside 256k) |
| GGUF | Yes, community. `bartowski/RecursiveSI_flint-GGUF`, quantized with llama.cpp **b11804** (31 Oct). The org card itself ships BF16, plus separate NVIDIA and Apple quants. Apache 2.0. Text only |
| Tool use | OpenAI-compatible tool calls. Preserve `reasoning_content` |

**Claim (org, primary).** https://x.com/RichardSocher/status/2112944388829544864 (21 Oct) says it is best-in-class for fast local coding and up to 2× comparable models: 125+ tok/s on an M4 Pro MacBook Pro and 150+ on a 64 GB RTX Spark. Those speeds are Recursive’s own engine (`rec` on Apple, specialized kernels on RTX Spark), not llama.cpp Vulkan. The Hugging Face card states their own scores: Terminal-Bench 2.1 **54.9**, SWE-bench Pro v2 **89.7**, SWE-bench Verified **74.2**, at temp 1.0 / top_p 0.95 / top_k 20. Terminal-Bench uses Terminus 2 and counts web-retrieved solutions as failures. https://huggingface.co/RecursiveSI/flint and https://recursive.com/updates/introducing-recursive-flint

A write-up of Recursive’s comparison chart puts Qwen3.6-35B-A3B at 44.9 / 73.8 / 73.4 on those three. I did not read the chart image directly. The card says the other columns are developer-reported and the setups differ. SWE-bench Verified is essentially a tie (74.2 vs 73.4). The gap they are selling is Terminal-Bench and SWE-bench Pro.

**Architecture note that matters at 31k.** Only 14 layers grow a KV cache. Tom Turney measured that at about 28 KB/token in BF16, so a 262k cache is about 7.5 GB, with the sliding layers fixed at ~37 MB: https://x.com/no_stp_on_snek/status/2113058466579284215 (22 Oct, primary-source engineer, not Recursive).

**On your box.** 2.5B active versus 3B is about 17% less weight traffic, so a small decode gain is plausible and a jump past 34 is not demonstrated. No MTP head is documented, and your 34 already includes MTP. One community Mac mini comparison (122.6 tok/s INT4 vs 91.5 for Qwen3.6 at 4-bit) is Apple bandwidth, not this APU. A separate reviewer reported Flint spending 45,082 tokens against Qwen3.6’s 2,732 on the same 14 tasks on a 64 GB Strix Halo under llama.cpp Vulkan. That is one anecdote, and if it repeats, wall-clock gets worse even when tok/s is fine. The NVFP4 checkpoint is what Recursive says stays within 0.7 points of BF16. A bartowski GGUF can sit further off the card.

### 3. Clover-35B-A3B-Preview — DiffuSpace

| | |
|---|---|
| Released | 24 Oct 2026 on Hugging Face. llama.cpp AR-mode support merged in v0.9.0 on 4 Nov (PR #31306) |
| Size | 35B / ~3B, diffusion MoE, thinking mode. Official Q4_K_M GGUF is 21.42 GiB |
| GGUF | Yes, official and several community quants |

**Claim (org).** The announcement says it beats Qwen3.6-35B-A3B on all six agent benchmarks they ran, including SWE-bench Verified **73.6**, Terminal-Bench 2.1 **51.7**, and τ³ **65.3**, and that it generates much faster. Confirmed on https://huggingface.blog/blog/diffuspace-clover-35b-a3b-preview (1 Nov) and the DiffuSpace post. The speed figure attached to that claim is **680 tok/s on one GB300 in BF16**, and **515 tok/s on one H200** versus 365 for a Qwen setup with DFlash2. That is block diffusion on datacenter GPUs.

**Why it is not a speed candidate.** v0.9.0 runs Clover in autoregressive mode only. Self-speculative decoding is a separate path, and one GB10 test in PR #31306 got **13.5 tok/s normal vs 8.1 tok/s with draft-self** despite an ~83% accept rate. The agent scores were not measured on that AR path. A load test is reasonable. A full harness run is not, until someone shows the AR checkpoint still holds those scores.

## llama.cpp since b11776 (21 Oct)

v0.8.0 is 28 Oct. **v0.9.0 is 4 Nov** (nightly b12110). Later nightlies are in the b121xx range. https://github.com/ggml-org/llama.cpp/releases/tag/v0.9.0 and https://x.com/victormustar/status/2118038226589925427

What touches this GPU:

* **Vulkan small-n split-K for RDNA3 and RDNA4** (#30146), inside the v0.9.0 changelog. Small-n is the decode shape. The note does not name RDNA 3.5 or gfx1152, and there is no 860M measurement.
* **MTP checkpoint save/restore** (#30141) and the server fix for drafts longer than `n_rs_seq` (#31350). This is the change that matters for your current Qwen MTP sessions. It is not a new kernel.
* **`flash_attn_ext_rows`** (#29510) makes the unified KV cache cheaper for multi-sequence serving. It does not raise single-stream decode. The release does not say the Vulkan kernel of that op is done for gfx1152.
* **Gemma 4 E2B/E4B prefill** (#31356) is a large prefill cut for those two small models only.
* **New architectures:** Clover AR, Metis-1.6, Limite 1B, Mistral Large 4. Xing4.0 support is PR #31589, reported on 6 Nov as CPU and CUDA: https://x.com/ai_hakase_/status/2118540130084426192. Ripple-65B support is cited as b12167. OCP FP8 E4M3 is not a win on RDNA 3.5.

The RDNA 3.5 flash-attention and fused MoE/GDN kernels that actually move Qwen3.6 numbers are in a HIP fork, `halo-box/strix-llama.cpp` PR #172 (12 Oct, before this window), measured on **gfx1151 Strix Halo**. Against master Vulkan on that 40 CU part, decode was about **+3% to +6%**. Prefill was much faster under ROCm. An 8 CU 860M will not see the Halo prefill numbers, and that work is not upstream Vulkan.

No Krackan, 860M, 880M, or 890M owner posted a new “best model” result in this window. The Ryzen AI posts that look relevant are Strix Halo: DeepSeek-V4.1-Flash at ~19–38 tok/s in 1-bit with SSD expert streaming (https://x.com/superalesha/status/2118663182852231446), and Qwen3.6 at 52 tok/s on a GEEKOM A9 Mega, which is a Max+ 388 with an 8060S (https://x.com/Davidariasfin/status/2116846488579940508). Both are the wide LPDDR machine.

## Checked and dropped

* **Nemotron 3.5 Bolt E4B** (NVIDIA, 23 Oct). 8B dense, ~4B effective, Gemma 4 E4B post-train, official Q4_K_M GGUF plus a DFlash drafter. NVIDIA’s own table loses to Qwen3.5-4B on Tau2-Bench (55.1 vs 75.1) and BFCL-v3 (68.5 vs 70.9). Not a 35B-A3B peer. The 74B Bolt and 120B Super are over the size cap. Lightning stays excluded as already tested.
* **MiMo-V2.6-Distill-Qwen-9B** (Xiaomi). Dense 9B, GGUF, Ollama tag on 3 Nov, but the model is from September. Terminal-Bench 2.1 **37.1** versus the mid-40s published for Qwen3.6-35B-A3B. A dense 9B at Q4 is more weight traffic than a 3B-active MoE, so it should be slower here.
* **Air-26B-A4B** (6 Nov, https://x.com/aiaicreate/status/2118509213521682765). A 4-bit GGUF of Gemma 4 26B-A4B, not a new model. Groot’s card already has that Gemma well behind Qwen on the agent set (Terminal-Bench 26.52).
* **Xing4.0-29B-A4B** (China Telecom). 29B / 4B, MLA + MTP, GGUF, Apache 2.0, but the weights are **16 Sep**. A September write-up has it ahead of Qwen3.6 on Terminal-Bench 2.1 (57.5 vs 51.5) and behind on SWE-bench Verified and Tau3. The November llama.cpp port is described as CPU and CUDA. Four billion active is the wrong direction for this bandwidth.
* **Metis-1.6 Logos** (Lernex, paper 27 Oct, llama.cpp 3 Nov). 10.2B looped, ~2.4B per token, GGUF. The author puts the average next to Qwen3-4B and says code, instruction following, and long context trail.
* **Over the size cap:** Qwen3.8-27B dense, Qwen3.8-Flash-Next (125B / ~6B), BTL-3 (27B dense LoRA on Qwen3.6-27B, even the 8.39 GB “compact” file), Ripple-65B dense, Nemotron 3.5 Bolt 74B, DeepSeek-V4.1-Flash, Kimi K3.1 Pro.

## Shortlist

1. **Groot-19B-A3B-261023**, Q4_K_M, with and without the MTP head if llama.cpp accepts it. Same runtime you already trust, half the file, the only quality claim aimed straight at Qwen3.6-35B-A3B on agent benches.
2. **Flint**, bartowski Q4 or IQ4, knowing the card numbers are BF16 and the 125/150 tok/s figures are not llama.cpp. Judge tokens per task, not tok/s.
3. **Clover**, only as a load-and-spot-check in AR mode. Do not expect the published speed or, until measured, the published scores.

**Verdict.** Yes, benchmark Groot and then Flint. The bet is agent score and tokens per task. Neither has a shown decode above 34 tok/s on this class of iGPU, and a llama.cpp Vulkan build without a working MTP head can lose to the model you already run.
