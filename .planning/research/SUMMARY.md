# Project Research Summary

**Project:** Odoo Module Automation — Agent Lightning + Cognee Integration (v3.0)
**Domain:** RL-based agent optimization + knowledge graph pipeline for existing Odoo module generation system
**Researched:** 2026-03-04
**Confidence:** MEDIUM

## Executive Summary

This research covers adding two intelligence layers to the existing Odoo Module Automation v2.1 system: Agent Lightning (Microsoft, MIT) for prompt optimization via APO (Automatic Prompt Optimization), and Cognee (Topoteretes, Apache-2.0) for knowledge graph-enhanced retrieval. The central finding is that **both tools have a fundamental architectural mismatch with our system**: our agents are markdown files consumed by external AI coding assistants (Claude Code, Gemini), not Python agent runtimes with interceptable LLM call loops. Neither Agent Lightning nor Cognee was designed for this deployment model. What is valuable are the underlying concepts — APO's collect-critique-rewrite loop and Cognee's entity-relationship extraction — implemented as lightweight custom modules rather than full framework integrations.

The recommended approach is concept extraction over framework adoption. For knowledge enrichment: skip full Cognee installation (30+ transitive deps, FastAPI/Uvicorn bloat, dual vector store problem, mandatory LLM API keys for routine operation) and instead build a lightweight graph layer using NetworkX alongside existing ChromaDB. For prompt optimization: skip Agent Lightning's full infrastructure (Lightning Server, Client, LightningStore) and implement only the APO feedback loop as a standalone Python module: `validation_outcome -> LLM_critique -> improved_agent_markdown`. Both paths should be pursued in sequence — knowledge graph first (lower risk, immediate value, independent of Agent Lightning), prompt optimization second (requires training data that accumulates during normal usage).

The most critical risks are: (1) over-engineering a working system — the current KB of 13 files and 80+ WRONG/CORRECT pairs may already be sufficient, and no baseline metrics exist to prove otherwise; (2) cold start for prompt optimization — APO needs 50+ diverse module generation outcomes before it produces meaningful improvements; and (3) dual vector store anti-pattern — ChromaDB and Cognee's LanceDB must not coexist. All three risks are preventable if the roadmap enforces a Feasibility and Baseline phase before any integration work begins.

## Key Findings

### Recommended Stack

The existing stack (Python 3.12, Jinja2, Click, pylint-odoo, ChromaDB, Docker, uv) remains unchanged and correct. For new additions, research strongly recommends the minimal path: `networkx` for knowledge graph modeling (already a Cognee transitive dependency, lightweight, no server, JSON-serializable), `agentlightning[apo]>=0.3.0` only if building the full APO loop (the `[apo]` extra adds only `poml` beyond the core package), and `litellm>=1.76` as the shared LLM proxy. PyTorch, vLLM, Neo4j, LanceDB, FastAPI, Uvicorn, Mistral, and sentence-transformers should all be avoided — they serve VERL/full-framework modes not applicable to our architecture.

**Core technologies:**
- `networkx` — knowledge graph for KB relationship modeling — zero-config, JSON-serializable, no server required, already in Cognee's transitive dep tree
- `agentlightning[apo]>=0.3.0` (conditional) — APO concept extraction only; CPU-only, no PyTorch, MIT license; only if building full feedback loop
- `litellm>=1.76` — unified LLM proxy for APO critique calls and optional KB entity extraction; shared across both tools with compatible version floors
- ChromaDB (existing) — keep as SOLE vector store for both module search AND KB embeddings; do NOT add LanceDB as a second vector database
- Python 3.12 — confirmed compatible with all new packages: `agentlightning` (>=3.10), `cognee` (>=3.10, <3.14), `kuzu==0.11.3`, `fastembed` (<3.13)

**Do NOT add:**
- `cognee` as a direct dependency — 30+ transitive deps including FastAPI, Uvicorn, SQLAlchemy, Alembic, LanceDB, OpenAI, LiteLLM, Mistral
- `torch` / PyTorch — VERL mode only; APO is CPU-only via LLM API; adding PyTorch alone adds ~2GB
- `sentence-transformers` — ChromaDB uses built-in ONNX embeddings; `fastembed` (ONNX) handles remaining use cases
- `neo4j` / `lancedb` — server-based infrastructure not needed at current scale (13 KB files, ~200 graph nodes)

**Total new dependency footprint:** ~100-150MB (networkx + agentlightning core + litellm) vs ~280-350MB if full Cognee is installed. PyTorch alternative would be 2GB+.

### Expected Features

The features research identified a critical architectural constraint: our agents are markdown prompt files, not Python agent runtimes. This shapes every feature decision and priority.

**Must have (table stakes):**
- Reward signal from validation outcomes — pylint score (0-10 normalized), Docker install success (binary), test pass rate (0-1 continuous), combined weighted 0-1 score; this is the foundation for everything else
- Knowledge graph from 13 KB markdown files — entity extraction, relationship modeling (e.g., "Many2one" requires comodel_name, requires depends), graph plus vector hybrid search
- Incremental KB updates without full rebuild — only re-process changed files; supported by both Cognee and custom NetworkX approaches
- Per-agent outcome attribution — when a module fails, identify WHICH agent prompt contributed, not just that "it failed"

**Should have (competitive differentiators):**
- APO feedback loop for `odoo-model-gen` as proof of concept before expanding to all eight agents
- MCP tool `search_knowledge` exposing knowledge graph search to AI coding assistant during generation
- Outcome collector (`outcome_collector.py`) logging `(module_spec, agent_prompt_version, generated_code, validation_outcome)` as JSONL — addresses cold start proactively
- Version-aware KB rules (Odoo 17 vs 18) via temporal tagging or separate KB sections

**Defer to v2+ (not essential for v3.0 launch):**
- APO for all 8 agents simultaneously — prove it on one first, then expand
- Code graph pipeline for OCA repositories — high value but high LLM cost per repo; start with 5 most-referenced modules only after KB integration proves the pipeline
- Memify self-improvement loop — only meaningful after graph has significant usage history
- RL fine-tuning (VERL/PPO/GRPO) — not applicable; we do not control the LLM
- Neo4j migration — Kuzu/NetworkX sufficient at current scale (~200 nodes)
- Custom RL algorithms — zero training data exists today

**Priority order:** Cognee KB integration concept first (lower risk, immediate value), Agent Lightning APO second (requires execution harness and training data), code graph pipeline third (highest value, highest cost).

### Architecture Approach

The proposed architecture adds a Layer 5 "Intelligence Layer" above the existing 4-layer stack. Two components form this layer: an APO Trainer (offline, batch, spawns AI coding assistant subprocess via `claude --print`, captures output, runs validation, generates prompt critiques) and a Knowledge Engine (ingests KB markdown, builds entity graph, serves hybrid graph plus vector search). The critical design principle is disaggregation: optimization happens offline, not in the generation hot path. APO runs periodically as a standalone command `/odoo-gen:optimize`; knowledge enrichment is pre-computed at the start of each generation session and cached per module domain.

**Major components:**
1. `cognee_bridge.py` (Layer 3, new) — wraps knowledge engine: `ingest_kb()`, `enrich_context(query)`, `rebuild_graph()`; keeps KB markdown as source of truth; Cognee is derived index, not source
2. `outcome_collector.py` (Layer 3, new) — extends validation pipeline to emit structured JSONL; foundation for APO training data; provides observability value independently
3. `grader.py` (Layer 3, new) — converts `PylintResult + DockerResult` to `OutcomeReward(pylint_score, install_score, test_score, overall)` on 0.0-1.0 scale with weighted combination
4. `rollout_runner.py` (Layer 5, new) — spawns AI coding assistant as subprocess for each training task; captures generated module files; most novel and unproven component
5. `apo_trainer.py` (Layer 5, new) — implements APO collect-critique-rewrite loop; loads agent markdown, runs rollouts, generates LLM critiques, rewrites prompt, validates on held-out set
6. MCP tool `search_knowledge` (Layer 3, new) — exposes knowledge graph search to AI coding assistant; pre-computes context at generation start, not per-invocation
7. ChromaDB (Layer 3, existing, UNCHANGED) — module similarity search continues unchanged; do NOT merge with knowledge graph collections

**Critical anti-patterns confirmed by architecture research:**
- Replacing ChromaDB with Cognee for module search — different data, different purpose
- Running APO in the generation pipeline — 30-120 sec per Docker validation per rollout, prohibitively slow in hot path
- Cognifying every OCA repository — prohibitive LLM cost at 200+ repos
- Abandoning markdown KB files as source of truth — Cognee/graph is derived index

### Critical Pitfalls

All top pitfalls rated HIGH confidence by the pitfalls researcher. The honest assessment: the CONCEPT of both tools is valuable; the FRAMEWORKS are wrong for our architecture.

1. **Fundamental abstraction mismatch** — Agent Lightning expects a Python agent runtime to instrument; our agents are markdown files in external AI coding assistants. Do NOT install Agent Lightning's full framework. Implement only the APO algorithm's core loop as lightweight standalone Python. Effort for concept extraction: 2-3 days. Effort for full framework integration: 2-3 weeks (and it will not work because there is no execution surface for LightningStore/tracer).

2. **Cognee dependency explosion** — Full `cognee` install pulls 30+ mandatory dependencies including FastAPI, Uvicorn, SQLAlchemy, Alembic, LanceDB, OpenAI, LiteLLM, Mistral — transforming a 3-dependency CLI tool into a full-stack web application. Use `networkx` (already a Cognee transitive dep) for graph modeling, existing ChromaDB for vector search, rule-based entity extraction for structured markdown parsing without LLM API calls. Effort for NetworkX graph: 3-5 days. Effort for full Cognee: 2-3 weeks (dependency conflicts, dual vector store).

3. **No reward signal — RL without a grading function is random walking** — APO requires a continuous multi-signal reward function designed and validated before any optimization attempt. Reward must be granular (not binary), multi-dimensional (pylint + Docker + test + pattern match), and per-agent attributable. Design and validate against 10+ diverse module specs before any APO run.

4. **Over-engineering a working system** — No baseline metrics exist for current system performance. Before adding any technology: measure first-pass validation rate, top 5 failure categories, ChromaDB search relevance, and frequency of KB-documented WRONG patterns appearing in agent output. Without baselines, success criteria cannot be defined and improvement cannot be proven. The knowledge graph adds zero value for 13 files if ChromaDB already finds the right patterns.

5. **Cold start — APO needs data you do not have yet** — APO needs 50+ diverse `(module_spec, prompt_version, output, validation_outcome)` records before optimization is meaningful. At 30-120 seconds per Docker validation, this dataset takes hours of unattended compute to build. Build the outcome collector first, let data accumulate during normal usage, enforce a hard data readiness gate (50+ examples across 5+ module categories with both passing and failing examples) before triggering any optimization.

## Implications for Roadmap

Based on combined research, the recommended phase structure prioritizes: (1) establishing baselines before changing anything, (2) knowledge enrichment before prompt optimization, (3) offline and batch over real-time integration.

### Phase 1: Baseline Measurement and Feasibility

**Rationale:** The pitfalls research ranks this as the highest priority gate. Adding intelligence to a system with no performance metrics is "solving a problem that does not exist yet." This phase gates everything else — if the current system already achieves a high first-pass validation rate, the entire v3.0 intelligence layer may be unnecessary or should target a different bottleneck.

**Delivers:** Baseline metrics document (first-pass validation rate, top failure categories, ChromaDB search precision@5 on representative queries), architecture decision record (concept extraction vs framework adoption for both tools), dependency compatibility spike (verify networkx + agentlightning[apo] resolve cleanly on Python >=3.12,<3.13 with existing deps).

**Addresses:** Over-engineering pitfall (Pitfall 4), abstraction mismatch validation (Pitfall 1), dependency explosion prevention (Pitfall 2).

**Avoids:** Committing to integration scope before knowing whether integration is warranted or solving the right problem.

**Research flag:** This phase IS the research materialized as measurement. No `/gsd:research-phase` needed — upstream research is complete. Execution is pure measurement and decision-making.

### Phase 2: Knowledge Graph Foundation (NetworkX + ChromaDB)

**Rationale:** Knowledge graph integration is independent of Agent Lightning, has fewer dependencies, delivers immediate value (enriched context for existing agents), and creates better training data for prompt optimization. Build it first. Use NetworkX (lightweight, no server, JSON-serializable) not full Cognee. Keep ChromaDB as sole vector store — add a separate collection `odoo_knowledge` for KB embeddings rather than introducing LanceDB.

**Delivers:** `cognee_bridge.py` with `ingest_kb()`, `enrich_context(query)`, and `rebuild_graph()`, `kb_sync.py` for incremental re-ingestion on KB file changes, MCP tool `search_knowledge` exposed to AI coding assistant, rule-based entity extraction from structured KB markdown (no LLM API calls for routine operation — one-time LLM-assisted bootstrap acceptable for initial graph construction).

**Uses:** `networkx`, existing ChromaDB (new `odoo_knowledge` collection), existing KB markdown files (unchanged as source of truth).

**Implements:** Knowledge Engine component from proposed 5-layer architecture.

**Avoids:** Cognee dependency explosion (Pitfall 2), dual vector store anti-pattern (Pitfall 5), LLM API key requirement for basic functionality (Pitfall 7).

**Research flag:** Standard patterns. NetworkX graph modeling, ChromaDB multiple-collections, and structured markdown parsing are all well-documented. No additional research phase needed.

### Phase 3: Outcome Collection Infrastructure

**Rationale:** This is a prerequisite for prompt optimization and is independently valuable for observability. The outcome collector instruments the existing validation pipeline with small, low-risk changes: extend result dataclasses with `to_reward_signal()` methods, add JSONL logging, and build the grader function. Records accumulate during normal usage, solving the cold start problem before any optimization is attempted.

**Delivers:** `outcome_collector.py` emitting `(module_spec, agent_name, prompt_version, generated_files, validation_outcome)` JSONL, `grader.py` with `OutcomeReward` dataclass (pylint_score, install_score, test_score, overall) and weighted 0-1 scoring, validation pipeline extended with structured outcome reporting, count dashboard toward the 50-example data readiness threshold.

**Uses:** Existing validation pipeline (pylint_runner, docker_runner), existing result dataclasses.

**Implements:** Outcome Collector and Grader components from proposed architecture.

**Avoids:** No reward signal problem (Pitfall 3 — grader designed before optimization), cold start problem (Pitfall 6 — data collection starts well before optimization is attempted).

**Research flag:** Standard patterns. Extending dataclasses and writing JSONL are straightforward Python instrumentation. No additional research needed.

### Phase 4: APO Prompt Optimization (Single Agent, Proof of Concept)

**Rationale:** By this phase, the knowledge graph delivers enriched context, outcome data has been accumulating through Phases 2-3, and the grader function is validated against diverse module types. APO can now be attempted with sufficient data. Start with `odoo-model-gen` only — model generation is responsible for the most foundational artifacts, and model failures are directly attributable via per-agent pylint scoring on models.py. Validate that optimization on one agent measurably improves its held-out validation rate before expanding to all eight.

**Delivers:** `rollout_runner.py` spawning AI coding assistant subprocess (`claude --print --system-prompt agents/odoo-model-gen.md`) for training tasks, `apo_trainer.py` implementing the APO collect-critique-rewrite loop, CLI command `/odoo-gen:optimize [agent-name]` for offline batch optimization runs, A/B test protocol comparing optimized vs original prompt on held-out validation set (not training set), version-controlled agent markdown with optimization history headers.

**Uses:** `agentlightning[apo]>=0.3.0` OR custom APO implementation (decision depends on feasibility findings from Phase 1 spike), `litellm>=1.76` for LLM critique and rewrite calls, training dataset accumulated from Phase 3 outcome collector.

**Implements:** APO Trainer and Rollout Runner from proposed 5-layer architecture.

**Avoids:** Abstraction mismatch (Pitfall 1 — rollout runner uses subprocess, not Agent Lightning's native tracer), binary reward (Pitfall 3 — grader is multi-signal continuous), cold start (Pitfall 6 — 50+ examples required as hard gate before this phase begins), prompt overfitting (held-out validation set required before deploying any optimized prompt).

**Research flag:** This phase needs a 2-3 day technical spike before full planning. The subprocess-based rollout runner is novel and unproven. Key question: can `claude --print --system-prompt agents/odoo-model-gen.md` reliably generate graded training data? If the subprocess approach fails, fall back to manual data labeling (generate modules manually, record outcomes, run APO offline on collected JSONL) rather than blocking the entire phase.

### Phase 5: Expanded Optimization and Selective Code Graph

**Rationale:** After Phase 4 proves the optimization loop works on one agent with measurable improvement on held-out data, expand to the remaining seven agents in priority order (based on failure rate data from the outcome collector). Also adds a code graph pipeline for the top 5-10 most-referenced OCA modules — enabling queries like "how does OCA implement approval workflows?" beyond what text similarity provides. Limit to the most commonly forked modules; do NOT run cognify on all 200+ OCA repos (prohibitive LLM cost).

**Delivers:** APO optimization applied to remaining 7 agents in failure-rate priority order, code graph pipeline for top 5-10 OCA modules via `run_code_graph_pipeline()` equivalent, `SearchType.CODE` equivalent for querying code structure patterns, feedback loop extracting APO-discovered rules as new WRONG/CORRECT pairs back into the KB markdown.

**Avoids:** Co-optimizing all agents simultaneously (credit assignment impossible without per-agent attribution), cognifying all 200+ OCA repos (must be scoped to high-value subset).

**Research flag:** Code graph pipeline needs a cost spike before planning. Run the pipeline on ONE popular OCA module, measure LLM token usage and API cost, extrapolate to the planned 5-10 module set. If total cost exceeds $10 for the batch, reconsider approach (e.g., reduce scope to top 3 modules or use rule-based code parsing).

### Phase Ordering Rationale

- Baseline first prevents investing weeks in integrations that solve non-existent problems. If the current system already achieves 90%+ first-pass validation rates, the intelligence layer targets a non-bottleneck.
- Knowledge graph before optimization because enriched context improves APO training data quality (agents trained with better context learn more specific rules) and delivers independent value.
- Outcome collection before optimization because APO without training data is random walking. These must run in sequence with a hard 50-example threshold gate enforced before any optimization run.
- One agent before all agents because the subprocess-based rollout runner is novel and unproven. Scope must be limited until feasibility is confirmed by a measurable improvement on held-out data.
- Selective code graph last because it is highest cost (LLM API per repo) and can be indefinitely deferred if the KB knowledge graph provides sufficient improvement at lower cost.

### Research Flags

Phases likely needing deeper research or spikes during planning:

- **Phase 4 (APO Proof of Concept):** The subprocess-based rollout runner (`claude --print --system-prompt`) is novel and undocumented in Agent Lightning's official materials. A 2-3 day technical spike is mandatory before phase planning. If subprocess approach fails, redesign around manual data labeling rather than blocking.
- **Phase 5 (Code Graph):** OCA repository cognify cost is unknown. A cost spike (run one repo, measure LLM usage) is required before committing to the full code graph plan. Scope to top 3 modules if cost exceeds $10 total.

Phases with standard patterns where additional research can be skipped:

- **Phase 1 (Baseline Measurement):** Running existing validation pipeline on representative module specs; measuring ChromaDB search precision — pure execution, no research needed.
- **Phase 2 (Knowledge Graph Foundation):** NetworkX graph modeling, ChromaDB multiple collections, structured markdown parsing — all well-documented with ample prior art.
- **Phase 3 (Outcome Collection):** Extending dataclasses with reward signal methods and JSONL logging — standard Python instrumentation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions verified via PyPI and official docs. Python 3.12 compatibility confirmed for all new packages. No dependency conflicts between Agent Lightning (litellm>=1.74) and Cognee (litellm>=1.76) — resolver picks >=1.76 satisfying both. The key recommendation (avoid full Cognee install, use NetworkX + ChromaDB) is conservative and independently verifiable against Cognee's pyproject.toml. |
| Features | MEDIUM | Feature landscape well-documented for both tools. Mapping to our specific architecture (markdown agents in AI coding assistants, not Python agent runtimes) required significant inference. The priority order (knowledge graph first, APO second, code graph third) is based on complexity and risk analysis, not empirical testing against our system. |
| Architecture | MEDIUM | The 5-layer proposed architecture is coherent and addresses all known pitfalls. The subprocess-based rollout runner (key innovation for APO) is novel and unproven — LOW confidence on that specific component alone. Everything else (cognee_bridge, outcome_collector, grader) follows standard patterns with HIGH confidence. |
| Pitfalls | HIGH | Pitfalls research is thorough with verified sources for each major pitfall. Abstraction mismatch (Pitfall 1), dependency explosion (Pitfall 2), and cold start (Pitfall 6) are independently verifiable against official documentation. The "over-engineering" pitfall (Pitfall 4) is a judgment call but is supported by multiple independent sources and the absence of any baseline metrics in the current system. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Subprocess rollout runner feasibility (LOW confidence):** Can `claude --print --system-prompt agents/odoo-model-gen.md` reliably generate module code in a way that is capturable and gradeable? This is the critical technical unknown for the entire APO integration. Must be spiked in Phase 4 planning before committing full implementation scope. Fallback: manual data labeling rather than automated rollouts.

- **Baseline metrics do not yet exist:** No current measurement of first-pass validation rate, top failure categories, or ChromaDB search precision. These must be collected in Phase 1. If baseline metrics show the current system's failures are due to infrastructure issues (Docker stability, spec ambiguity) rather than prompt quality or knowledge retrieval, the intelligence layer targets the wrong bottleneck.

- **Training data diversity threshold:** Research suggests 50+ diverse examples as minimum for APO, extrapolated from Agent Lightning's published benchmarks on simpler classification tasks. The actual threshold for Odoo module generation (multi-file, multi-stage, 8-agent pipeline) is unknown. Be prepared to raise to 100+ if early APO results show random walking rather than convergence.

- **Rule-based entity extraction quality:** KB ingestion relies on parsing structured markdown (headings, code blocks, WRONG/CORRECT pairs) without LLM calls. This is feasible for the current 13 files which follow consistent format, but relationship quality depends on how well the markdown structure encodes relationships. A one-time LLM-assisted extraction pass to bootstrap the graph (acceptable as a build-time dependency) followed by rule-based incremental updates is the recommended hybrid approach.

- **Cognee Python 3.12 strict constraint:** Odoo 17 requires `>=3.12,<3.13`. If any Cognee transitive dependency requires Python 3.13+ features (e.g., future versions of `fastembed`, `onnxruntime` moving beyond the <3.13 ceiling), Cognee cannot be installed at all. This risk is why the concept-extraction approach (NetworkX only) is strongly preferred over full Cognee installation — it eliminates this version risk entirely.

- **LLM API cost for KB entity extraction:** Each `cognify()` call (or equivalent custom LLM extraction call) uses LLM API tokens for entity and relationship identification. With 13 KB files, this is manageable as a one-time build cost. But if KB rebuilds become frequent or the KB grows significantly, costs accumulate. Design the ingestion pipeline to minimize LLM calls: parse structure with rules, use LLM only for ambiguous relationship inference.

## Sources

### Primary (HIGH confidence)
- [Agent Lightning Official Documentation](https://microsoft.github.io/agent-lightning/latest/) — architecture, APO algorithm, Python requirements, training guide
- [Agent Lightning GitHub Repository](https://github.com/microsoft/agent-lightning) — pyproject.toml, source code, releases page
- [Agent Lightning PyPI](https://pypi.org/project/agentlightning/) — verified version 0.3.0, wheel size 612KB, Python >=3.10 classifiers
- [Agent Lightning arXiv Paper](https://arxiv.org/abs/2508.03680) — APO algorithm validation, performance benchmarks, architecture deep-dive
- [Microsoft Research Blog on Agent Lightning](https://www.microsoft.com/en-us/research/blog/agent-lightning-adding-reinforcement-learning-to-ai-agents-without-code-rewrites/) — architecture philosophy and design intent
- [Cognee GitHub Repository](https://github.com/topoteretes/cognee) — pyproject.toml with 30+ mandatory dependencies verified
- [Cognee PyPI](https://pypi.org/project/cognee/) — verified version 0.5.3, Python 3.10-3.13, 1.7MB wheel
- [Cognee Official Documentation](https://docs.cognee.ai/) — vector stores, graph stores, embedding providers, search types, add/cognify/search API
- [APO Algorithm Documentation](https://microsoft.github.io/agent-lightning/latest/algorithm-zoo/apo/) — beam search parameters, reward function requirements, textual gradient concept

### Secondary (MEDIUM confidence)
- [Agent Lightning Training Tutorial](https://microsoft.github.io/agent-lightning/latest/how-to/train-first-agent/) — 29 samples sufficient for simple tasks; code generation complexity extrapolation required
- [Cognee + LanceDB Case Study](https://lancedb.com/blog/case-study-cognee/) — storage backend behavior and integration patterns
- [Cognee + Kuzu Blog Post](https://blog.kuzudb.com/post/cognee-kuzu-relational-data-to-knowledge-graph/) — graph construction pipeline stages
- [LiteLLM + Agent Lightning Integration](https://docs.litellm.ai/docs/projects/Agent%20Lightning) — shared dependency compatibility confirmation
- [Cognee Memory Architecture Blog](https://www.cognee.ai/blog/fundamentals/how-cognee-builds-ai-memory) — cognify pipeline 6 stages
- [Cognee Memify Pipeline](https://www.cognee.ai/blog/cognee-news/product-update-memify) — edge strengthening, derived facts, usage-based graph evolution
- [Cognee Repo-to-Knowledge-Graph Guide](https://www.cognee.ai/blog/deep-dives/repo-to-knowledge-graph) — code graph pipeline for OCA repos

### Tertiary (LOW confidence — needs validation during implementation)
- [State of RL for LLM Reasoning (Sebastian Raschka)](https://sebastianraschka.com/blog/2025/the-state-of-reinforcement-learning-for-llm-reasoning.html) — training data requirements; extrapolated to code generation complexity
- [Prompt Overfitting in RL (NAACL 2025)](https://aclanthology.org/2025.findings-naacl.390.pdf) — 30% performance drop on reformulated inputs; APO-specific risk
- [Production-ready Knowledge Graphs 2025](https://medium.com/@claudiubranzan/from-llms-to-knowledge-graphs-building-production-ready-graph-systems-in-2025-2b4aff1ec99a) — when KGs are worth building vs simpler alternatives
- [KG-based repository-level code generation](https://arxiv.org/html/2505.14394v1) — +25% improvement benchmark; caveat: measured against systems without existing structured KB

---
*Research completed: 2026-03-04*
*Ready for roadmap: yes*
