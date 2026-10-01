# What Took the Clock: Toolchain, Power and Backend Attribution on an AMD APU

**Dino Vitale**  
Boundary Labs, Airway Heights, WA  
research@boundarylabs.org  
ORCID: 0009-0001-5590-3296

*Preprint*  
*October 2026*  
*License: CC BY 4.0*


> **RETRACTED IN PART, 2026-10-01.** Adversarial review before upstream filing showed the
> binaries compared as "GCC vs Clang" also differ in OpenMP linkage (present vs absent) and
> CPU backend strategy (runtime dispatch vs `GGML_NATIVE=ON`). The compiler attribution in
> this draft — including the §5 decomposition and the §12 conclusion — is therefore not
> supported by the evidence presented. The measurements stand; the cause does not. This was
> never published to Zenodo and holds no DOI. Retained as a record of the error.

---

## Abstract

We benchmarked llama.cpp's ROCm/HIP backend against its Vulkan backend on an AMD Krackan Point integrated GPU — the low-tier Ryzen AI 300 part that ships in ordinary work laptops and that hardware reviewers skip in favour of its 128 GB halo sibling. The production stack won by a factor of 2.13 on loaded-context decode. That number is correct and it is not the finding.

Holding the backend fixed and varying only the compiler, the same Vulkan source built with `hipcc`/Clang 22 runs 34.6% slower than the same source built with GCC 11.4. Holding the compiler fixed and varying only the backend accounts for 6.4%. The gap we would have attributed to ROCm is mostly a toolchain effect, and we would have attributed it wrongly without building a control nobody normally builds.

The mechanism is power. The package sustains roughly 36 W. Binaries built with `hipcc` draw 47–48 W during the boost window, trip the ceiling, and the hardware responds by cutting the GPU clock from ~2750 MHz to ~900–1050 MHz. The GCC-built binary performs the same work at ~39 W, never reaches the ceiling, and holds its clock indefinitely. This is not thermal: the package plateaus at 68–72 °C under the throttled binaries while the unthrottled control runs hotter, at 80 °C.

Normalising throughput by the clock the hardware actually granted inverts the result. ROCm delivers 0.288 prefill tokens per second per MHz against Vulkan's 0.107, and 0.0133 decode against 0.0073 — 2.7× and 1.8× respectively. ROCm produces *more* prefill than Vulkan while pinned at 1044 MHz against Vulkan's 2718. Its kernels are not slower. It loses because the toolchain it is obliged to use spends the power budget that would otherwise have become clock.

We also report two platform limits that are invisible in specifications: ROCm cannot load a model larger than the BIOS UMA carve-out, because HIP treats the carve-out as a hard VRAM ceiling while the Vulkan driver spills transparently into GTT; and speculative decoding would not initialise under ROCm at any offload depth we could reach. On an APU, ROCm's availability is a firmware setting rather than a driver question.

We publish four corrections made during the run, including a mechanism we proposed and then disproved with the compiler control, and the protocol the corrections produced. All raw data, telemetry traces and scripts are public.

---

## 1. Introduction

A backend comparison reports tokens per second. Two implementations run the same model on the same hardware, and the faster number identifies the better implementation. The inference is so natural that the measurement is usually taken as self-interpreting.

It is not self-interpreting on a part whose clock is a dependent variable. A laptop APU shares one power budget between CPU and GPU and enforces it by changing frequency. Throughput measured on such a part is a joint function of the software's arithmetic efficiency and its power draw, and those two can point in opposite directions. Software that computes more per clock can measure slower than software that computes less, if it spends more watts getting there and the hardware answers by taking the clock away.

This is not a subtle effect. In the measurements below it is the dominant one, and it is attributable to the compiler rather than to the backend under test.

We ran this on a chip that is poorly covered precisely because it is ordinary. Reviewers benchmark Strix Halo, the Ryzen AI Max+ part with 128 GB of unified memory, because it is the halo product and the headline. Krackan Point is the cheap sibling in a mid-range mobile workstation. It is the configuration most people who run a local model on an AMD laptop actually have, and we could find no published ROCm-versus-Vulkan numbers for it.

## 2. Setup

**Hardware.** Lenovo ThinkPad P14s Gen 6 AMD (21QL0013US): AMD Ryzen AI 7 PRO 350, Radeon 860M integrated GPU, reported by `rocminfo` as **gfx1152** and by Mesa as `RADV KRACKAN1`. 32 GB DDR5-5600 in two SODIMM slots, dual channel, giving a theoretical 89.6 GB/s. BIOS UMA framebuffer 16 GiB, leaving ~15 GiB to the operating system. openSUSE Tumbleweed, Linux 7.2.6, Mesa RADV, ROCm 7.2.0 from openSUSE's `science:GPU:ROCm` repository. All runs on AC power with the CPU governor at `performance`.

The firmware exposes the carve-out as a writable attribute at `/sys/class/firmware-attributes/thinklmi/attributes/UMAFramebufferSize`, with permitted values `Auto;1GB;2GB;4GB;8GB;16GB;32GB;48GB`. There is no 24 GB step. This matters later.

**Model.** Qwen3.6-35B-A3B, UD-IQ4_NL quantisation, 17.26 GB on disk. From the GGUF header: 41 blocks (40 transformer layers plus one multi-token-prediction layer), embedding dimension 2048, 16 attention heads, **2 key-value heads**, 256 experts with 8 active, and a trained context length of 262144. The two KV heads at head dimension 128 give roughly 40 KB of KV cache per token across 40 layers, so the model's full 256k context is about 10.7 GB of cache.

**Binaries.** Three, all built from llama.cpp at commit `07fc586e3` (build 11168):

| label | backend | compiler |
|---|---|---|
| `rocm` | HIP, `-DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1152` | Clang 22.0.0 (`hipcc`) |
| `vk-clang` | Vulkan, `-DGGML_VULKAN=ON` | Clang 22.0.0 (`hipcc`) |
| `vk-gcc` | Vulkan | GNU 11.4.0 |

`vk-gcc` is the production binary already deployed on the machine. `vk-clang` exists only as a control: it shares a backend with `vk-gcc` and a toolchain with `rocm`, which is what makes the two effects separable.

**Workload.** `llama-server` with `-c 65536 -t 8 -fa on --jinja --no-warmup`. Decode measured over 128 generated tokens with `ignore_eos` set; prefill measured on a 5201-token prompt. Every run asserts the token counts it was supposed to produce.

## 3. ROCm cannot load the model, and that is a finding

The first ROCm run did not produce a slow number. It produced no number:

```
ggml_backend_cuda_buffer_type_alloc_buffer: allocating 17151.70 MiB on device 0:
  cudaMalloc failed: out of memory
alloc_tensor_range: failed to allocate ROCm0 buffer of size 17984856576
```

The model is 17.1 GiB and the carve-out is 16 GiB. The kernel's view of the device explains why only one backend cares:

```
VRAM total: 16384 MiB
GTT  total:  7810 MiB
```

HIP treats the BIOS carve-out as a hard VRAM ceiling. The Vulkan driver addresses both regions, roughly 24 GiB, and spills into GTT transparently — which is why the identical model loads and runs under Vulkan on the identical machine. Setting `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1`, the usual recourse on unified-memory parts, does not rescue it.

Two consequences follow. First, on an integrated GPU **ROCm's availability is a firmware setting, not a driver question** — a fact absent from any specification sheet, and one that inverts the usual intuition that a unified-memory device is more forgiving than a discrete one. Second, the comparison in this paper is necessarily run at **partial offload**: we determined the largest depth ROCm could accept, `-ngl 36` of 40 layers, and ran every binary at that depth. Four layers remain on the CPU in all cells. Full-offload numbers are not in this dataset and cannot be until the carve-out exceeds the weights.

Speculative decoding under ROCm never initialised at this carve-out, in any configuration we could construct, confirmed twice under the final protocol. The multi-token-prediction draft context requires memory beyond an already-exhausted budget.

## 4. The first comparison, and why it was wrong

Our first matched comparison ran five decode measurements per cell, ROCm first and Vulkan immediately after, and reported Vulkan ahead by 23.2% on clean decode.

Within the ROCm cell the five runs were 19.95, 19.64, 17.37, 15.18, 15.16 — a monotonic 24% decline. The corresponding Vulkan sequence was 21.60, 21.46, 21.54, 21.48, 21.50, flat to half a percent. A decaying cell and a stable one were being summarised by their means and compared.

The decay was not thermal and not software. We established this with a restart test: five runs on a fresh process, then a server restart changing nothing else, then five more. Had the cause been allocator fragmentation, a leak, or any per-process state, the second batch would have begun where the first began. It did not. Batch B opened at 16.44 and settled immediately to ~15.2, while resident set size grew identically in both batches, 3481→3970 MB and 3489→3978 MB.

The telemetry identified the mechanism. GPU clock tracked throughput one-for-one, and package power showed a boost window:

| t | clock | busy | temp | power |
|---|---|---|---|---|
| 0 s | 662 MHz | 1% | 41 °C | 6.7 W |
| 24 s | **2213 MHz** | 80% | 69 °C | **50.2 W** |
| 37 s | 1089 MHz | 85% | 72 °C | 37.8 W |
| 97 s | 1060 MHz | 85% | 68 °C | 36.0 W |

The package boosts to ~50 W for roughly 25 seconds, then settles to a sustained ~36 W, holding the GPU at about half its boost frequency. Temperature plateaus in the high sixties and never approaches a thermal limit.

The ordering therefore decided the result. ROCm ran first with a full boost budget; Vulkan ran immediately afterwards with the package already in its sustained regime. We had compared one backend boosting against another sustained. Measured sustained against sustained, the gap was **41%**, not 23%.

## 5. The compiler control

We attributed the throttling, initially, to the memory path. The evidence looked strong: at partial offload four layers live on the CPU, and HIP must copy their activations across the host–device boundary every token, whereas the Vulkan driver maps system memory directly. The resident-set and GTT figures supported it — ROCm held ~3.5 GB of explicit host buffers and used no GTT at all, while Vulkan held 333–1177 MB with weights memory-mapped and 3551 MB of GTT in use. Copy traffic burning the shared power budget was a coherent story.

It was wrong, and the control that disproved it is one a backend comparison does not normally include.

Building the Vulkan backend from the same tree with the same toolchain produced a binary that **throttles identically to ROCm** — sustained 16.40 t/s at 877 MHz, against the GCC build's 21.23 t/s at 2762 MHz on the same source and the same commit. A Vulkan binary performs no host–device copies for CPU-resident layers regardless of compiler. The copy hypothesis cannot survive it.

With both controls in hand the effect decomposes. On short-prompt decode, sustained:

```
backend   (ROCm → Vulkan, compiler fixed at Clang):   +8.8%
compiler  (Clang → GCC,  backend fixed at Vulkan):   +29.4%
                                     1.088 × 1.294 = +40.8%
```

which reproduces the 41% measured end-to-end to within 0.2%. The earlier figure was never wrong as a number. It was two effects, and we had credited both to the backend.

## 6. Results

The final pass measures prefill and loaded-context decode on a 5201-token prompt, four cells, two interleaved repetitions, eight runs each, on a quiescent machine with page cache dropped and two unscored warm-ups per cell. Sustained values, boost window excluded:

| binary | prefill t/s | decode t/s | clock | power |
|---|---|---|---|---|
| ROCm (Clang) | **301.1** | 13.88 | 1044 MHz | 33.1 W |
| Vulkan (Clang) | 278.6 | 14.77 | 877 MHz | 33.5 W |
| Vulkan (GCC) | 290.5 | 19.88 | 2718 MHz | 34.5 W |
| Vulkan (GCC) + MTP | 194.3 | **29.50** | 2552 MHz | 36.3 W |

Decode decomposes as backend +6.4%, compiler +34.6%, speculative decoding +48.4%; the production configuration is **2.13×** ROCm end to end.

All 64 runs are valid against their asserted token counts. The worst disagreement between repetitions is 2.8%, on the speculative-decoding cell whose throughput depends on content-sensitive draft acceptance; every other cell agrees within 1.2%.

**Prefill and decode do not move together.** ROCm has the best prefill of any binary measured and the worst decode. A single combined tokens-per-second figure would have reported neither, and the two metrics stress different limits: decode on this part is bound by memory bandwidth, prefill by compute.

## 7. Normalising by the clock

The hardware did not grant the four binaries the same frequency. Dividing throughput by the clock each was actually running at asks a different question: not which binary is fastest, but which does more arithmetic per cycle it was given.

| | prefill per MHz | decode per MHz |
|---|---|---|
| ROCm | **0.288** | **0.0133** |
| Vulkan (GCC) | 0.107 | 0.0073 |

**ROCm is 2.7× more clock-efficient on prefill and 1.8× on decode.** It produces more prefill in absolute terms than the Vulkan binary while running at 1044 MHz against 2718 — the Vulkan build needs 2.6× the frequency to lose narrowly on that axis.

The ROCm kernels are not slower. They are better, on both metrics, per unit of clock. ROCm loses the wall-clock comparison because the toolchain it must use spends in watts what would otherwise have been frequency.

We can state this as a bounded claim only. The toolchain effect is demonstrated **on Vulkan**, where we built the same source both ways. The counterfactual for ROCm — a HIP binary built without `hipcc` — is not constructible, because llama.cpp's HIP backend requires that compiler. So the finding is: *ROCm on this part is defeated by its required build chain*. It is not: *ROCm would win*. Which of those two it becomes is an open question we flag in §10.

## 8. What speculative decoding costs

Multi-token prediction is the largest single lever available on this machine, and it is not free in the direction usually assumed.

Against the same binary with the same prompt, MTP delivers **+48.4% decode** and costs **−33.1% prefill** (290.5 → 194.3 t/s). It also converts a deterministic workload into a variable one: standard deviation across runs rises from 0.12 to 2.09 tokens per second, because throughput tracks draft acceptance and acceptance tracks content. This is the only cell in the study with a repetition-to-repetition disagreement above 1.2%.

For agentic workloads, which generate far more than they ingest, the trade is strongly favourable. For a prefill-dominated workload it is not, and the configuration should differ. The methodological consequence is sharper: **a single-run A/B against a speculative-decoding build can be wrong by 17%**, which is larger than most of the effects such comparisons are run to detect.

## 9. What we got wrong

Four corrections were made during this study. We publish them because the protocol in §11 exists as a consequence, and presenting the protocol without them would misrepresent it as foresight.

1. **A backend gap of 23% that was really 41%, and then really two effects.** Caused by run order interacting with the boost window (§4), resolved by sustained-to-sustained measurement, then decomposed by the compiler control (§5).
2. **A mechanism proposed and disproved.** Host–device copy traffic was a plausible, evidence-supported explanation for the throttling. The Vulkan/Clang control falsified it (§5). We had already written it down as the finding.
3. **A speculative-decoding prefill cost reported as −2.2%, actually −33%.** The original figure came from a full-offload configuration with boost contamination, wrong by an order of magnitude (§8).
4. **A cell reporting ~20.8 t/s computed from two generated tokens**, after the model emitted an end-of-sequence token on a repetitive prompt. The arithmetic was sound and the measurement meaningless. `ignore_eos` and an assertion on the token count are now mandatory; the void cell is retained in the published data rather than deleted, so that the hole in the method remains visible.

Three of the four would have survived into a published result had the study stopped at a plausible point. The first stopping point available was a clean-looking +23%.

## 10. Limitations

**Partial offload.** Every cell runs at `-ngl 36` of 40 layers, because that is the most ROCm can accept at a 16 GiB carve-out. These are not full-offload numbers. Whether the toolchain's power behaviour persists when no layers remain on the CPU is untested.

**The ROCm counterfactual is not constructible.** We cannot build llama.cpp's HIP backend without `hipcc`, so we cannot separate "ROCm draws more power" from "binaries built with this compiler draw more power" for the ROCm case specifically. A mixed-toolchain build — CPU-side objects under GCC, kernels under `hipcc` — would test it, and we have not attempted one.

**Compiler versions are not matched.** GCC 11.4.0 against Clang 22.0.0 confounds vendor with version. A GCC-16 and a Clang-15 build would separate them.

**One machine, one model, one quantisation.** Nothing here establishes that the effect generalises to other APUs, discrete GPUs, dense models, or other quantisation schemes. Discrete cards with their own power domains and their own memory are the obvious place to expect it not to hold.

**Driver and runtime versions are a single point.** Mesa RADV and ROCm 7.2.0 as packaged by openSUSE in October 2026. Both move quickly.

**A background application consumed roughly 19% of CPU during the early runs**, including the matched comparison in §4. It was eliminated before the final passes. It affected both backends, but on a part with a shared power budget it is not merely noise, and the §4 figures should be read accordingly.

## 11. What a benchmark on a power-limited part must control

The protocol we now run under is published alongside the data. Its load-bearing provisions:

- **Report the clock.** A throughput figure without the frequency that produced it is not comparable to anything, and on this hardware the frequency is a dependent variable.
- **Discard the boost window.** The first ~25–30 seconds of GPU load is not a rate the machine can hold. Report the sustained tail; never report a mean spanning both regimes, which describes a state the hardware never occupied.
- **Cold-start every cell with an equal idle interval**, so no cell inherits a budget its predecessor spent.
- **Interleave and repeat.** Residual drift then appears as disagreement between repetitions rather than as silent bias toward whichever condition ran first.
- **Build the control that isolates the toolchain.** A backend comparison whose binaries differ in compiler is measuring both. This is the provision that produced the finding.
- **Separate prefill from decode**, and clean from loaded context. They move independently and sometimes oppositely.
- **Assert the sample.** A rate computed over a token count you did not request is void regardless of how reasonable it looks.
- **Quiet the machine and verify it stayed quiet**, recording the top process alongside each measurement. Background load on a shared power budget is throughput you are measuring away.
- **Treat a failure as a result.** An out-of-memory error and a backend that will not initialise are findings about the platform, not gaps in a table.

## 12. Conclusion

On an AMD Krackan Point APU running a 35B mixture-of-experts model, the deployed Vulkan configuration outperforms ROCm by a factor of 2.13 on loaded-context decode. Most of that margin is not the backend. Holding the backend fixed, compiler choice accounts for 34.6%; holding the compiler fixed, the backend accounts for 6.4%.

The mechanism is a power ceiling. Binaries built with `hipcc` draw 47–48 W against GCC's ~39 W, exceed a sustained budget of roughly 36 W, and have their GPU clock reduced from ~2750 MHz to ~900–1050 MHz. Normalised by the clock the hardware granted, ROCm performs 2.7× more prefill and 1.8× more decode per MHz than Vulkan. Its arithmetic is more efficient on both axes. It loses anyway, and it loses to a compiler.

Two platform constraints bound the result and are worth more than the ratio. ROCm cannot load a model larger than the BIOS UMA carve-out, where the Vulkan driver spills transparently into GTT — so on an integrated GPU, ROCm's availability is decided in firmware. And speculative decoding, the single largest performance lever available here, would not initialise under ROCm at any depth this carve-out permits.

The general claim is narrow and, we think, portable: **on hardware that enforces a power budget by changing frequency, tokens per second is not a property of the software under test.** It is a joint measurement of that software's arithmetic and its power draw, and those can rank in opposite orders. Any comparison on such a part that does not report the clock has not reported its result.

## Artifacts

All raw data, 2-second telemetry traces, build scripts and benchmark scripts:
`inference-research/p14-krackan/2026-10-01/`. The measurement protocol:
`inference-research/BENCHMARK-PROTOCOL.md`. Superseded and void cells are
retained in the published data, marked, because the corrections in §9 cite them.
