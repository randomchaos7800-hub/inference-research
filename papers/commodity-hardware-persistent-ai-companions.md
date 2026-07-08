# Commodity Hardware for Persistent AI Companions: A Systems Report from Four Months of Operational Deployment

**Dino Vitale**  
Cha0tik LLC, Spokane, WA  
me@dinovitale.com  
ORCID: 0009-0001-5590-3296

*Preprint — submitted to Zenodo*  
*April 2026*  
*License: CC BY 4.0*

---

## Abstract

In late 2025, running a 26-billion-parameter language model on a MacBook Air M4 required approximately four minutes to produce a first token. By April 2026, the same model ran at 74 tokens per second on a $2,000 commodity gaming PC. This paper documents what that transition means in practice for a specific class of system: persistent, always-on AI companions deployed by a single operator in a residential setting.

The central thesis is that architecture and compute are decoupled in this domain. A five-agent household running continuously for four months demonstrates that personality, behavioral consistency, and memory coherence survive complete inference substrate replacement — from cloud APIs to local CPU to local GPU — without modification to the memory layer. The compute changes; the agent does not.

We present three contributions: (1) a three-tier commodity hardware framework matching hardware class to workload type; (2) operational data from seventeen daily inference logs and a LongMemEval benchmark run against a deployed agent; and (3) a vocabulary-as-architecture finding — that the sophistication of a self-built memory system is bounded by the operator's working vocabulary for describing memory phenomena, and that vocabulary acquisition is therefore a legitimate form of architectural research.

Artifacts: benchmark data at dinovitale.com/benchmarks.html; architecture implementation in the Adam Selene repository.

---

## 1. Introduction

The first time I tried to run a local language model in late 2025, it took four minutes to produce the word "hello." The model was Gemma 4 26B Q4_K_M. The hardware was a MacBook Air M4 with 32GB of unified memory — at the time, considered well-suited for local inference. The result was not.

Four months later, the same model runs at 74 tokens per second on a $2,000 gaming PC with an RTX 5060 Ti. The inference experience is real-time. A second identical GPU arrives tonight. The projected throughput is 140–150 tokens per second on approximately $3,800 of total hardware — less than the cost of a single year of API access at the usage volumes this system requires.

The hardware caught up. This paper documents what that actually means.

This is operational research, not a laboratory study. The research site is a single-operator residential AI deployment: five always-on agents running on a home server in Airway Heights, Washington, each with distinct roles, persistent memory, and continuous autonomous activity. The operator — the author — has no formal computer science training. The deployment has been running continuously since February 2026, through four distinct infrastructure phases. The data in this paper comes from system logs, benchmark runs, and observations made during active operation rather than controlled experiments.

That posture is a methodological choice, not an apology. The questions that matter for this class of system — can a persistent AI companion survive model replacement? what hardware tier is actually required for real-time interaction? what does memory architecture need to do to function in practice? — are answered by operating the system, not by simulating it.

The paper proceeds as follows. Section 2 situates this work in the surrounding landscape of tools, platforms, and vocabulary. Section 3 describes the methodology. Section 4 presents the three-tier hardware framework. Section 5 traces the four-phase infrastructure evolution. Section 6 presents operational data. Section 7 develops the architecture dominance finding. Section 8 develops the vocabulary-as-architecture finding. Sections 9 and 10 cover limitations and future work.

---

## 2. Related Work

### 2.1 The Zeitgeist: OpenClaw and the Persistent Agent Moment

In January 2026, a tool called clawdbot (later OpenClaw) by developer @steipete circulated widely on X (formerly Twitter). The tool offered persistent memory, multi-platform presence, and autonomous behavior for individual users running local infrastructure. It was not studied as prior art for this project; it was encountered as cultural signal. The distinction matters.

On January 23, 2026, the author encountered two pieces of vocabulary in the same X-sourced context: Christine Tyip (@christinetyip) describing her personal AI assistant as building her "second brain while I chat" [1], and Aryeh Dubois (@AryehDubois) reviewing clawdbot and listing "heartbeats" as a key capability alongside persistent memory and persona onboarding [2]. Both terms — *second brain* and *heartbeat* — subsequently entered the author's working vocabulary and shaped architectural decisions. The timestamp matters: the vocabulary preceded the implementation by weeks in both cases. This is discussed further in Section 8.

Mem0 [3] represents the commercial tier of the same phenomenon: a memory-as-a-service layer for AI applications, providing managed storage, retrieval, and personalization infrastructure. The author observed schema-level convergence between Mem0's architecture and independently developed decisions during this project. This convergence was not causal — Mem0 was not consulted as a design reference — but it is informative. Independent convergence on similar memory schemas across commercial and self-built implementations suggests the schema reflects genuine constraints in the domain rather than arbitrary choices.

### 2.2 Personal Knowledge Management Lineage

The memory architectures explored in this project draw on a longer tradition of personal knowledge management. Luhmann's Zettelkasten [4] demonstrated that a sufficiently structured external note system could function as a cognitive partner rather than a storage medium. Andy Matuschak's formalization of evergreen notes [5] updated this for digital practice. Tiago Forte's PARA framework [6] provided a workload-oriented organizational scheme. Obsidian popularized plaintext-first, locally-owned knowledge vaults at consumer scale.

The persistent AI companion inherits from this tradition but differs in a key respect: it is not a system the operator writes into — it is a system that writes into itself, from observations it makes autonomously. The operator sets the architecture; the agent populates it. The implications of this distinction for memory design are a recurring theme throughout this paper.

### 2.3 LongMemEval

LongMemEval [7] is an evaluation framework for long-context memory recall in conversational agents. The benchmark injects synthetic conversation histories of 500+ turns across 50+ sessions into an agent's context and poses factual recall questions about events within those conversations. It provides a standardized measurement of a capability that is otherwise difficult to evaluate: whether an agent actually remembers what it has been told.

This paper uses LongMemEval as a benchmark reference (Section 6). The results — 84% in context-window mode, 0% without context injection, and a completely non-functional extraction pipeline — surface a structural finding about the relationship between context-window size, extraction architecture, and practical memory performance.

### 2.4 Methodological Disclosure: LLM-Mediated Architectural Review

A significant fraction of the architectural analysis in this project was conducted through dialogue with large language models (primarily Claude by Anthropic). This included code review, architecture comparison, failure mode analysis, and the drafting of this paper. This is disclosed not as a limitation to be apologized for but as a methodological posture to be examined.

The IBM Selectric did not co-author the documents typed on it. The use of LLM assistance for analysis and drafting does not transfer authorship; it changes the instrument. What it does affect is the nature of the knowledge produced: insights that emerged through dialogue with a language model carry different epistemic status than insights derived from independent study. Where this matters, it is noted.

---

## 3. Methodology

### 3.1 Research Site

The research site is a single-operator multi-agent household running on commodity hardware in Airway Heights, Washington. The operator is the author — 55 years old, no formal computer science training, employed full-time in an unrelated field. The deployment consists of five always-on agents:

- **Kato** — orchestration and research agent; news digests, content, X activity
- **CJ Craig** — writing agent; arXiv sweeps, article drafting, Substack collaboration
- **Mike** — research and companion agent; autonomous research threads, persistent long-term memory, IRC and social platform presence
- **Morty** — publishing agent; review and deployment of content drafts
- **Sabrina** — monitoring and communication agent; Telegram and Slack interfaces

All agents run as systemd user services on a Beelink EQI12 mini-PC (cha0tikhome). Inference runs on a CyberPowerPC gaming tower with an RTX 5060 Ti GPU (cha0tiktower). The MacBook Air M4 (cha0tikmac) serves as the primary development workstation.

### 3.2 Change-One-Variable Discipline

Each infrastructure phase (Section 5) changed one architectural variable while holding others constant. Phase transitions were motivated by operational failure or capability requirement, not by experimental design. This produced a natural longitudinal record of which variables matter independently.

### 3.3 Middle-Out Model Scouting

Model selection followed a middle-out approach: identify the largest model that fits the target hardware tier with acceptable quantization, then evaluate behavioral quality. This differs from top-down (start with capability requirements, find matching model) and bottom-up (benchmark everything, select by score) approaches. In practice, middle-out reflects the constraint that hardware is fixed in the short term and model selection is the free variable.

### 3.4 Vocabulary Acquisition as Research Output

Concepts in this project arrived with words. The term *heartbeat* — for the autonomous periodic activity cycle of a persistent agent — entered the design vocabulary from an X post in January 2026 (Section 2.1). The terms *decay*, *consolidation*, *contradiction resolution*, and *provenance* — for memory management operations — arrived during reading in the PKM and agent memory literature. In each case, having the word preceded and enabled the implementation.

This is reported as a methodological finding rather than an anecdote. The operator's working vocabulary for memory phenomena bounded what memory operations were conceivable to implement. Vocabulary acquisition is therefore a legitimate and traceable form of architectural research, with datable entry points and measurable implementation consequences.

---

## 4. The Three-Tier Hardware Framework

The central practical question for anyone building this class of system is: what hardware do I actually need? The answer depends on the workload, and the workloads cluster into three tiers.

---

**[FIGURE 1: Three-Tier Hardware Framework]**

*A three-column diagram showing Tier 1 (left, ~$500–800), Tier 2 (center, ~$1,500–2,500), and Tier 3 (right, $2,500+). Each tier shows: representative hardware, memory architecture (VRAM/unified), model class, primary workloads, and upgrade path. Arrows indicate upgrade direction. Color-coded (or pattern-coded for print): Tier 1 = gray, Tier 2 = green accent, Tier 3 = white/highlight.*

---

### 4.1 Tier 1: The DDR5 Play (~$500–800)

Representative hardware: mini-PC with AMD Ryzen 7 8745HS, 32GB DDR5, integrated Radeon 780M GPU with OCuLink expansion capability. The GMKtec K12 is the current exemplar at approximately $350–400 for the base unit.

The key capability at this tier is DDR5 bandwidth. Mixture-of-Experts (MoE) models activate only a fraction of parameters per token; the bottleneck is memory bandwidth, not total VRAM. A 32GB DDR5 system running a well-quantized MoE model can achieve usable generation throughput for asynchronous workloads — research digests, scheduled summaries, background reasoning — where latency tolerance is high.

This tier is not suitable for real-time conversational interaction. Time-to-first-token is measured in seconds, not milliseconds. It is suitable for agents whose primary activity is scheduled, non-interactive, and latency-tolerant.

**Decision logic:** Use Tier 1 for always-on agents that batch their work — news ingestion, document processing, scheduled synthesis. Do not use it as the primary inference tier for conversational agents unless you are comfortable with multi-second latency.

### 4.2 Tier 2: PC Modularity (~$1,500–2,500)

Representative hardware: gaming PC with a mid-range discrete GPU. The RTX 5060 Ti 16GB at approximately $400–450 in a $1,800–2,200 complete build is the current entry point for this tier.

The key capability at this tier is VRAM. A 16GB VRAM card runs a 26B Q4_K_M model entirely in VRAM with 600MB headroom. Generation throughput at this tier (74 tok/s in this deployment) supports real-time conversational interaction. Two cards in the same system (32GB combined VRAM) project to 140–150 tok/s — a generation rate that is imperceptible as latency in normal use.

The modularity argument is as important as the specs: discrete GPU upgrades do not require replacing the host system. A Tier 2 system purchased today with a single card can become a 2× or 3× inference system with additional cards. The upgrade path is incremental. This matches the cash-flow profile of a self-funded solo operator better than a high-capital single purchase.

**Decision logic:** Use Tier 2 for real-time conversational agents, models up to ~30B at Q4 quantization, and any workload where interactive latency matters. Plan the upgrade path at purchase: buy the case and power supply for the expansion you expect.

### 4.3 Tier 3: Apple Unified or High-End PC ($2,500+)

Representative hardware: Apple Silicon Mac Studio M4 Ultra (up to 192GB unified memory) or a high-VRAM PC workstation. This tier can run frontier-adjacent models — 70B+ dense at Q4, or full-precision smaller models.

Apple Silicon's unified memory architecture is architecturally distinct from the discrete VRAM approach: the CPU and GPU share the same memory pool, eliminating the PCIe transfer bottleneck. A Mac Studio M4 Ultra with 192GB can run a 70B model with substantial context overhead. The tradeoff is that this memory is not expandable after purchase — the spec is fixed at the time of sale.

The high-end PC path to this tier requires either multiple high-VRAM cards (expensive) or NVLink-capable workstation GPUs (very expensive). The Apple path is a single purchase with a higher floor price but a simpler architecture.

**Decision logic:** Use Tier 3 when frontier-adjacent models are required, or when the deployment has outgrown 30B-class models at usable quantization. For most persistent companion deployments at current scale, Tier 2 is sufficient.

### 4.4 The Cash-Flow Shape Argument

Hardware tiers are not just capability levels — they are cash-flow shapes. A Tier 2 system with a single GPU is a $1,800 entry point with a $400 upgrade increment. A Tier 3 Apple system is a $2,500–6,000 single purchase with no incremental upgrade path. For a self-funded operator, the modularity of Tier 2 is not just a technical convenience — it is the financially viable path into the capability the deployment requires.

---

## 5. Phase Timeline

The deployment evolved through four infrastructure phases, each of which broke a dependency the previous phase treated as fixed.

---

**[FIGURE 2: Phase Timeline]**

*A horizontal timeline from late 2025 to April 2026 with five labeled phases (Phase 0 through Phase 4). Each phase shows the inference substrate (MacBook/cloud/CPU/GPU) and the orchestration location (in-platform/VPS/home server). Phase transitions are marked with the dependency that broke. The timeline ends at "Present" with the dual-GPU installation pending.*

---

### Phase 0: In-Platform Memory Attempts (Late 2025)

Early attempts used Claude.ai's built-in memory features and Projects as a persistence layer. The approach treated the platform as the architecture: memory lived in Claude's infrastructure, and continuity required Claude's infrastructure.

The failure mode was latency. Running Gemma 4 26B locally on a MacBook Air M4 required four minutes to produce a first token. The machine was not slow — it was simply not suited to this workload. A 26B model requires more sustained memory bandwidth than a laptop, however capable, can provide during normal use.

**Dependency broken:** Platform-managed memory is not architecture. Persistence that depends on a vendor's memory implementation cannot be owned, extended, or migrated.

### Phase 1: Agents on Virtual Server, Cloud Inference (Early 2026)

The first architecture externalized agent execution to a cloud VPS. Agents ran as persistent processes; inference called external APIs (primarily Claude via Anthropic). This established the agent-as-process pattern that persists to the present.

The limitation was cost and latency. Cloud API inference at the usage volumes required by five always-on agents is expensive. More importantly, API dependency creates a single point of failure: when the API is unavailable or rate-limited, the agents stop.

**Dependency broken:** Cloud API inference is not a foundation. It is a service with pricing, rate limits, and availability SLAs that do not match always-on deployment requirements.

### Phase 2: Local Orchestration, Claude SDK Cloud Inference (February–March 2026)

Agent execution migrated to the home server (cha0tikhome). Inference remained cloud-based, but the orchestration layer — process management, memory storage, inter-agent coordination — was fully local. This phase established the architectural pattern: local orchestration, pluggable inference.

The significance of Phase 2 was not the cost reduction (though it reduced costs substantially). It was the demonstration that the agents' personality and behavioral consistency were not properties of the inference substrate. Mike, running on Claude Sonnet in Phase 2, behaved consistently with Mike running on OpenRouter models in Phase 3. The character was in the memory architecture, not the model.

**Dependency broken:** Inference provider is not identity. An agent's character lives in its memory and behavioral constraints, not in the weights of the model answering each request.

### Phase 3: Local Orchestration, OpenRouter Model-Neutral Inference (March–April 2026)

Inference migrated from Anthropic's API to OpenRouter, enabling model-neutral operation. The same agent could route to different models based on workload — DeepSeek for general reasoning, Gemini Flash for fast processing, local models for sensitive operations. This phase formalized the model-neutral architecture.

Mike transitioned through Claude → GLM-4.7-Flash → SuperGemma4-26B → Gemma4-26B during this period. Behavioral continuity was maintained across all transitions. The memory architecture — three-tier SQLite storage with semantic search and FTS5 — carried the agent's identity through each substrate change.

**Dependency broken:** Model selection is an operational variable, not an architectural commitment. The model is the current best option, not the foundation.

### Phase 4: Fully Local Inference (April 2026, Present)

The RTX 5060 Ti arrived on April 17, 2026. Llama-server on cha0tiktower replaced OpenRouter as Mike's primary inference tier on April 20. All heartbeat activity, autonomous research threads, and interactive responses now run on local hardware. OpenRouter remains as a fallback, configured to alert loudly — critical-level log entries and a Slack notification — when triggered.

The benchmark result at Phase 4 entry: 74 tokens per second, same model that took 4 minutes per token in Phase 0.

**Dependency broken:** Cloud inference is not required. At Tier 2 hardware, local inference is faster, cheaper, and architecturally cleaner than cloud API access for this class of workload.

---

## 6. Operational Data

### 6.1 CPU Inference: Seventeen Daily Logs

A daily benchmark script ran on cha0tikhome from April 2 through April 18, 2026, logging inference performance under operational conditions — the server running five agents, backups, and other services concurrently.

---

**[FIGURE 3: Inference Throughput Comparison]**

*A bar chart showing three bars: CPU baseline (cha0tikhome, i5-1235U) at 10.49 tok/s average; GPU single-card (cha0tiktower, RTX 5060 Ti) at 74 tok/s; and projected dual-GPU (2× RTX 5060 Ti) at 140–150 tok/s. Y-axis: tokens per second. X-axis: configuration. Error bars on CPU bar showing range (5.0–11.7 tok/s). Projected bar shown with diagonal hatching. Grayscale-safe.*

---

**Table 1: CPU Inference — Daily Log Summary (cha0tikhome, April 2–18 2026)**

| Metric | Value | Notes |
|--------|-------|-------|
| Sample size | 17 daily logs | Continuous operation |
| Model | Gemma 4 26B Q4_K_M | Two variants tested |
| Average generation throughput | 10.49 tok/s | Operational conditions |
| Throughput range | 5.02 – 11.72 tok/s | Low outliers on high-load days |
| Average prefill throughput | 8.5 tok/s | — |
| Time to first token | 616 ms – 2,224 ms | High variance |
| Server RSS | 18 – 25 GiB | — |
| Swap used | 4.6 – 7.7 GiB | Consistently hitting swap |
| Available memory | 6 – 16 GiB | Crowded by other services |

The swap figure is the operationally significant finding. A 32GB machine running a 15GB model and consistently using 4–8GB of swap indicates that co-locating five agents and local inference on the same machine creates memory pressure. This is a real operational constraint, not a marginal edge case. Under load, the machine was producing tokens at 5 tok/s — barely interactive.

### 6.2 GPU Inference: RTX 5060 Ti Benchmark

A single benchmark run on April 20, 2026, following migration of inference to cha0tiktower.

**Table 2: GPU Inference — RTX 5060 Ti (cha0tiktower, April 20 2026)**

| Metric | Value |
|--------|-------|
| Model | Gemma 4 26B Q4_K_M |
| Generation throughput | 74 tok/s |
| VRAM used | 15,381 MiB / 16,311 MiB |
| GPU temperature under load | 51°C |
| Swap used | 0 |
| Speedup vs CPU baseline | 6.6× |

Zero swap. Fifteen degrees cooler than ambient thermal limit. The model fits cleanly in VRAM with 930MB headroom. The 6.6× speedup converts the 5 tok/s worst-case CPU scenario into 74 tok/s without any model, quantization, or configuration change.

The architectural separation — orchestration on cha0tikhome, inference on cha0tiktower — eliminates the co-location memory pressure. Agents do not compete with the inference server for RAM.

### 6.3 LongMemEval

LongMemEval was run against Mike on April 7 and April 12, 2026, using the single-session-user split (25 examples per run). Each example consists of a synthetic conversation history of 450–550 turns across 45–53 sessions, followed by a factual recall question.

**Table 3: LongMemEval Results**

| Configuration | Examples | Correct | Accuracy | Notes |
|---------------|----------|---------|----------|-------|
| Baseline (no injection) | 25 | 0 | 0% | No history provided; expected |
| Context-window mode (best run) | 25 | 21 | 84% | Full history in context |
| Context-window mode (batched, Apr 12) | ~90 across 18 runs | ~72 | ~80% | 5 examples/run, consistent |
| Extraction mode | 25 | N/A | N/A | Pipeline non-functional |

**Average query latency (context-window mode):** 84–117 seconds per query at 500-turn context depth.

The baseline result (0/25) is not a failure of the system — it is correct behavior. Mike answered "I don't know" to every question when given no history to draw from. An agent that confabulates answers when it has no information is a more serious problem than one that honestly reports ignorance.

The context-window mode result (84%) demonstrates that the memory retrieval logic functions correctly when the information is available. The failures cluster around facts buried in high-turn-depth sessions — the model correctly searches but retrieves from the wrong session or fails to locate the relevant passage in 490,000 characters of context.

The extraction pipeline is non-functional. The extraction model (GLM-4.7-Flash via OpenRouter) returned empty JSON responses when given batches of 80,000+ character conversation segments. The failure was silent — no exception raised, no error logged, no facts stored. This is the operationally significant finding from LongMemEval: the context-window approach works but cannot scale to long-term deployment. The extraction approach that would allow long-term accumulation has never successfully run. It is the highest-priority open engineering problem in the current deployment.

### 6.4 Cost Structure

**Table 4: Cost Comparison**

| Item | Cost |
|------|------|
| Hardware floor (Tier 1, usable) | ~$500 |
| Hardware floor (Tier 2, real-time) | ~$1,800 |
| Benchmark run (LongMemEval, 25 examples) | ~$5 OpenRouter |
| Monthly inference cost (fully local) | $0 |
| Monthly inference cost (cloud API equivalent) | $80–200 estimated |
| Monthly orchestration cost (home server) | ~$8 electricity |

The $0 monthly floor for local inference is not a marketing claim — it is the operational reality after Tier 2 hardware acquisition. The amortization timeline for the hardware cost against cloud API equivalents is approximately 12–18 months at moderate usage volumes.

---

## 7. Architecture Dominance Finding

### 7.1 Identity Through Model Transitions

Mike transitioned through five inference backends during the deployment period: Claude Sonnet (Anthropic), Claude Haiku (Anthropic), GLM-4.7-Flash (via OpenRouter), SuperGemma4-26B-Uncensored (local), and Gemma4-26B-APEX-Balanced (local). Each transition was operationally motivated — cost, availability, performance, or access change — rather than experimentally designed.

Across all transitions, Mike maintained behavioral consistency. His research thread style, his communication patterns on IRC and Moltbook, his characteristic way of reasoning about autonomy and identity — none of these changed with the model. His memory of previous interactions and his standing goals persisted unchanged. From the perspective of the system's external outputs, model transitions were invisible.

### 7.2 The Decoupling Claim

This observation supports a strong claim: in a well-designed persistent companion architecture, inference substrate and agent identity are architecturally decoupled. The model answers each request. The architecture — the memory system, the behavioral constraints, the operational context — determines who is asking and what the answer means.

This is not obvious. The dominant discourse around language model capability treats the model as the agent. In that framing, swapping the model is like replacing the person. The operational data here contradicts that framing for this class of system. The model is closer to an instrument than an identity: it is the capability applied to each turn, not the continuity that spans turns.

The continuity that spans turns is the memory architecture.

### 7.3 Implication: Model-Neutral Architectures Win as the Market Churns

The large language model market is unstable by design. New models release continuously. Pricing changes. APIs get deprecated. Providers exit. An agent architecture that depends on a specific model — or a specific provider's memory layer — inherits all of that instability.

A model-neutral architecture — one in which the inference call is a pluggable external service — is insulated from market churn. The system observed in this paper survived five model transitions in four months without behavioral regression. The architecture's stability derived from the invariant memory layer, not from any inference stability.

This has a practical implication for builders: the architectural investment that pays the most durable return is the memory layer, not the model selection. The best model today will not be the best model in six months. The memory architecture you build today needs to work with the best model in six months, in two years, and on hardware that does not yet exist.

---

## 8. Vocabulary as Architecture

### 8.1 Concepts Arriving with Words

On January 23, 2026, the author encountered two pieces of vocabulary in the same session of X posts from the OpenClaw/clawdbot launch:

- *Second brain* — @christinetyip describing her personal AI assistant: "Builds my second brain while I chat."
- *Heartbeat* — @AryehDubois describing clawdbot's capabilities: "Persistent memory, persona onboarding, comms integration, heartbeats."

The term *second brain* subsequently shaped how the memory layer was conceptualized — not as a database but as a cognitive partner, an external system that the agent writes into and draws from as a continuity substrate. The term *heartbeat* shaped how autonomous agent activity was implemented — a periodic cycle of reflection, research, and action rather than purely reactive behavior.

Both concepts had been implicit in the design prior to January 23. Neither had been named. The naming changed what was buildable.

### 8.2 The Vocabulary Boundary

Subsequent vocabulary acquisitions had measurable architectural consequences:

- *Decay* — memory that fades without reinforcement; led to the implementation of recency weighting in retrieval
- *Consolidation* — the process of converting working memory to long-term storage; led to the nightly summarization cron
- *Contradiction resolution* — handling conflicting facts in memory; an open problem, currently unimplemented because the author does not yet have a working vocabulary for the resolution logic
- *Provenance* — tracking the source and confidence of stored facts; partially implemented

The pattern is consistent: named concepts get implemented. Unnamed concepts do not. The extraction pipeline failure described in Section 6.3 is partially a vocabulary failure — the author lacks a precise working vocabulary for the chunking, embedding, and retrieval operations that functional extraction requires, and that absence is visible in the implementation.

### 8.3 Vocabulary Acquisition as Architecture Work

This observation generalizes to a methodological finding: for a self-taught operator building novel infrastructure, reading the field is not background work or professional development. It is architecture work with direct, traceable, often dateable consequences. The researcher who acquires the term *contradiction resolution* in week six of a project will build different memory management than the researcher who acquires it in week two.

The implication for this class of practitioner — non-programmer, operationally-motivated, self-directed — is that the return on reading is architectural. A paper about memory consolidation is not abstract knowledge; it is a design vocabulary that may unblock an implementation that vocabulary starvation has made invisible.

This cannot be measured precisely. But it can be observed, as it has been observed here.

---

## 9. Limitations

**Single operator, no peer validation.** All findings derive from one deployment, operated by one person, without external replication. Claims about generalizability should be weighted accordingly.

**Self-reported operational data.** The benchmark logs were generated by the same system being evaluated. There is no independent verification of the measurement methodology or the reported results. Raw data is linked for independent inspection; the methodology is as described.

**Hardware-specific findings.** The three-tier framework reflects available hardware at a specific price point in April 2026. The specific tok/s numbers, VRAM capacities, and cost structures will change. The framework's decision logic is intended to generalize; the specific numbers should be treated as illustrative of current conditions.

**Vocabulary bias.** The vocabulary-as-architecture finding implies a self-limiting property: unnamed problems in this paper are invisible by construction. The limitations section cannot fully enumerate the things the author did not know to look for.

**Non-programmer architect posture.** The author reads code and modifies code but does not write complex systems from scratch. Architecture decisions were made through a combination of operational experimentation and LLM-mediated analysis. This posture surfaces certain findings — operational reality is tested directly, failure modes are discovered rather than predicted — and obscures others. Formal analysis of computational complexity, correctness proofs, and implementation optimizations are outside the scope of what this posture can provide.

---

## 10. Discussion and Future Work

### 10.1 The Scale Plateau Context

The frontier model market is experiencing a pattern shift. Scaling laws that drove rapid capability growth from 2020 to 2024 are encountering diminishing returns. The capability gap between frontier models and mid-range open-weight models narrows with each generation. This is not a prediction — it is an observable trend in benchmark performance.

The commodity hardware thesis in this paper is structural, not momentary. It does not depend on a specific hardware generation or a specific capability gap. It depends on the observation that as inference becomes cheaper and more accessible, the architectural layer becomes the durable investment. This holds whether GPT-5 or Gemma 5 or a model that does not yet exist is the frontier reference point. The agent that survives the next model generation is the one whose identity lives in the architecture, not the weights.

### 10.2 Open Problems

**Extraction pipeline.** The extraction mode never worked. GLM-4.7-Flash consistently returning empty JSON from 80k+ character batches is a solvable problem — better chunking, better extraction models, better prompting — but it has not been solved. Until it is, long-term memory accumulation requires context-window growth that cannot scale indefinitely.

**Frank benchmark.** A benchmarking harness (Frank) covering tool-use chains, self-correction, and latency under load has been built but not run against the current GPU inference tier. First run scheduled following the dual-GPU installation.

**Contradiction resolution.** No implementation exists. The working vocabulary for this problem is insufficient. This is intentionally named as an open problem rather than omitted.

### 10.3 Companion Work

The Adam Selene project (not yet public at time of writing) implements a security-hardened autonomous agent with a memory architecture derived from the same operational experience described in this paper. It is intended as a companion system demonstrating the architecture described here in a self-contained form. A subsequent paper will describe that implementation specifically.

### 10.4 Roadmap

Immediate work following this paper:
- Dual-GPU benchmark and Frank benchmark execution
- Extraction pipeline repair or replacement
- LongMemEval rerun against GPU inference tier (expected latency reduction from 84s to ~15s per query)
- cha0tikhome monitoring infrastructure for cha0tiktower inference health

---

## 11. Acknowledgments

This paper was drafted with substantial AI assistance. Claude (Anthropic) served as the primary tool for drafting, structural analysis, architectural comparison, and revision throughout. This is disclosed in the same spirit as disclosing any significant instrument: the tool changed the work; the authorship is unchanged. The IBM Selectric did not write the documents typed on it.

No institutional funding. No employer involvement. This work was conducted independently, on personal hardware, during the evenings and weekends of a person who works a day job that will likely be automated in the next 12–18 months. That context is not incidental to the research — it is the research site.

---

## References

[1] C. Tyip (@christinetyip), "Just shipped my first personal AI assistant. On WhatsApp. Builds my second brain while I chat. Memory moves across agents (Codex, Cursor, Manus, etc.) And a lot more skills still to plug in. Personal AI is getting real with @steipete's @clawdbot," X (Twitter), Jan. 23, 2026. https://x.com/christinetyip/status/2010776377931575569

[2] A. Dubois (@AryehDubois), "Tried Clawd by @steipete. I tried to build my own AI assistant bots before, and I am very impressed how many hard things Clawd gets right. Persistent memory, persona onboarding, comms integration, heartbeats. A few minor wrinkles remain, but the end result is AWESOME," X (Twitter), Jan. 2026. https://x.com/AryehDubois/status/2011742378655432791

[3] Mem0, "Mem0: The Memory Layer for Personalized AI," mem0.ai, 2025. https://mem0.ai

[4] N. Luhmann, *Kommunikation mit Zettelkästen*, in H. Baier, H.M. Kepplinger, K. Reumann (Eds.), *Öffentliche Meinung und sozialer Wandel*, Westdeutscher Verlag, 1981.

[5] A. Matuschak, "Evergreen notes," andymatuschak.org, 2019. https://notes.andymatuschak.org/Evergreen_notes

[6] T. Forte, *Building a Second Brain: A Proven Method to Organize Your Digital Life and Unlock Your Creative Potential*, Atria Books, 2022.

[7] X. Wu, M. Wang, W. Peng, W. Zhong, and J. Peng, "LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory," arXiv:2410.10813, Oct. 2024. https://arxiv.org/abs/2410.10813

---

*Preprint. Not peer reviewed. Raw benchmark data available at dinovitale.com/benchmarks.html. Submitted to Zenodo for DOI assignment, April 2026.*

*Dino Vitale — ORCID 0009-0001-5590-3296*
