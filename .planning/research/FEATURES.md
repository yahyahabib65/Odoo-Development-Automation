# Feature Landscape: Agent Lightning + Cognee Integration

**Domain:** RL-based agent optimization + knowledge graph pipeline for existing Odoo module automation system
**Researched:** 2026-03-04
**Confidence:** MEDIUM (both tools are real and actively maintained, but mapping them to our specific architecture -- markdown-based agents inside AI coding assistants -- requires careful feasibility analysis)

## Critical Context: How Our Agents Actually Work

Before mapping features, it is essential to understand the architectural mismatch that shapes every recommendation below.

**Our agents are NOT standalone LLM API callers.** They are markdown instruction files (system prompts, skills, workflows) that get loaded into an AI coding assistant (Claude Code, Gemini, Codex). The AI coding assistant handles the LLM calls. We never directly call GPT-4, Claude, or any model API ourselves. Our "agents" are:

- `odoo-model-gen` -- a markdown file with instructions for generating Odoo models
- `odoo-view-gen` -- a markdown file with instructions for generating views
- `odoo-validator` -- a markdown file with instructions for running validation
- ...and 5 more similar agents

This means Agent Lightning's RL fine-tuning mode (training model weights) is **not directly applicable**. Its APO mode (optimizing prompt templates) is the relevant capability, but even that assumes you control the LLM inference loop, which we do not.

**Our knowledge base is 13 static markdown files** with WRONG/CORRECT pairs, loaded as context by GSD's orchestration layer. ChromaDB provides semantic search over 200+ OCA repositories for module discovery, not knowledge retrieval.

---

## Part 1: Agent Lightning Features

### What Agent Lightning Actually Offers

Agent Lightning (Microsoft, v0.3.0, MIT license, 15.3K GitHub stars) is a framework for training LLMs via reinforcement learning. It has two modes:

1. **RL Fine-tuning (LightningRL)** -- Trains open-weight model weights (Qwen, Llama, etc.) using PPO/GRPO algorithms. Requires GPU, vLLM, and access to model weights. Produces a fine-tuned model checkpoint.

2. **APO (Automatic Prompt Optimization)** -- Uses LLM-generated "textual gradients" (critiques) to iteratively improve prompt templates via beam search. No GPU required. Uses OpenAI API for critique/rewrite. Produces an optimized text prompt.

### Confidence: HIGH (verified via official docs, arXiv paper, GitHub repo, Microsoft Research blog)

---

### Table Stakes: What Agent Lightning MUST Provide to Be Worth Integrating

| Feature | Why Expected | Complexity | Dependencies on Existing System | Notes |
|---------|--------------|------------|--------------------------------|-------|
| **Reward signal from validation outcomes** | The entire point of RL-based optimization is learning from outcomes. Our validation pipeline already produces pass/fail signals (pylint-odoo score, Docker install success, test pass rate). These MUST be capturable as reward signals. | LOW | Depends on: validation pipeline, artifact state tracking | Our validation pipeline already returns structured results. Wrapping these as 0-1 reward scores is straightforward. The question is whether Agent Lightning can consume them in our architecture. |
| **Prompt template improvement loop** | APO's core value: take an agent's system prompt, run it on tasks, grade results, critique the prompt, produce a better prompt. Our 8 agents each have markdown prompts that could theoretically be improved this way. | HIGH | Depends on: all 8 agent markdown files, validation pipeline | This is the primary applicable feature. But requires building: (a) a task dataset of module generation requests, (b) a grading function that scores outputs, (c) an execution harness that simulates agent runs outside the coding assistant. |
| **Execution trace capture** | Agent Lightning needs to see what happened during agent execution (prompts sent, responses received, tools used) to assign credit. Our system must emit structured traces. | HIGH | Depends on: GSD orchestration layer (which manages agent execution) | GSD controls agent spawning. We would need GSD to emit trace data in Agent Lightning's span format, or build a translation layer. This is a significant integration point. |
| **Credit assignment across multi-agent pipeline** | With 8 agents in a pipeline, when the final module fails validation, which agent caused the failure? Credit assignment is essential for meaningful optimization. | HIGH | Depends on: artifact state tracking, validation pipeline error messages | Agent Lightning's credit assignment uses "simple identical distribution" (equal credit/blame to all steps). This is crude for our use case where a view-gen failure is clearly not model-gen's fault. We would need custom credit assignment. |

### Differentiators: What Would Set Our Integration Apart

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **APO for agent prompt evolution** | Automatically improve our 8 agent prompts based on accumulated validation outcomes. Instead of manually tuning "always use _inherit for mail.thread" rules, let APO discover these patterns. Demonstrated 84% to 88% accuracy improvement on SQL generation in 2 rounds. | HIGH | Requires: task dataset (50+ module specs), grading function, execution harness that can run agents outside AI coding assistant | This is the most viable Agent Lightning feature for our architecture. APO does not require GPU or model weights. It calls OpenAI API to critique/rewrite prompts. But it requires us to build an execution harness that simulates what the AI coding assistant does -- which is substantial work. |
| **Per-agent selective optimization** | Agent Lightning supports optimizing individual agents in a multi-agent system. We could optimize just `odoo-model-gen` while leaving others unchanged, reducing blast radius. | MEDIUM | Requires: isolation of individual agent execution, per-agent reward signals | Our validation pipeline already identifies whether failures are in models, views, security, or tests. This maps naturally to per-agent optimization. |
| **Automatic knowledge base rule discovery** | When APO improves a prompt, the diff between old and new prompt reveals what the optimization learned. These diffs could be extracted as new WRONG/CORRECT pairs for our static knowledge base. | MEDIUM | Requires: working APO loop, diff extraction pipeline | This is a compelling secondary benefit. Instead of manually writing KB rules, extract them from successful prompt improvements. |
| **Validation-driven continuous improvement** | Every module generation run becomes training data. Over time, agents get better at common patterns (HR modules, inventory extensions, CRM customizations). | LOW (conceptual), HIGH (implementation) | Requires: persistent trace storage, periodic reoptimization runs, versioned prompt management | The vision is powerful but requires significant infrastructure: trace database, scheduled optimization runs, A/B testing of old vs new prompts. |

### Anti-Features: What NOT to Build with Agent Lightning

| Anti-Feature | Why Tempting | Why Problematic | What to Do Instead |
|--------------|-------------|-----------------|-------------------|
| **RL fine-tuning of open-weight models** | Agent Lightning's flagship capability. Sounds impressive: "train a custom Odoo-specialized LLM." | Our agents run inside Claude Code/Gemini/Codex. We do not control the LLM. Fine-tuning Qwen-2.5 and self-hosting it replaces the entire AI coding assistant paradigm, which is out of scope. Requires GPU infrastructure (1+ NVIDIA GPU per training node). Requires building an entirely new inference pipeline. | Use APO mode only. Optimize the prompts our agents use, not the underlying model. If model quality is the bottleneck, switch to a better AI coding assistant. |
| **Real-time RL training during generation** | Train agents while they generate modules, updating prompts on-the-fly. | Agent execution happens inside the user's AI coding assistant. We cannot intercept LLM calls in real-time. Even if we could, modifying prompts mid-generation would cause inconsistency between early and late artifacts. | Batch optimization: collect traces from completed runs, optimize offline, deploy improved prompts for next run. |
| **Multi-agent RL co-optimization** | Optimize all 8 agents simultaneously so they learn to work together. | Agent Lightning's multi-agent RL is designed for agents that call each other via API. Our agents are orchestrated by GSD, which loads them sequentially into the AI coding assistant. There is no direct agent-to-agent communication to optimize. Credit assignment across 8 sequential agents is also poorly supported (simple equal distribution). | Optimize agents independently. Use validation feedback to identify which agent needs improvement, then run APO on that agent's prompt only. |
| **Building a custom RL algorithm** | Agent Lightning's Algorithm Zoo supports custom algorithms. We could build Odoo-specific RL. | Premature optimization. We have zero training data (no recorded traces of agent execution). Building a custom RL algorithm before having data is backwards. | Start with APO (requires no training data beyond task/reward pairs). Collect traces. Evaluate whether custom algorithms are needed after seeing APO results. |

---

## Part 2: Cognee Features

### What Cognee Actually Offers

Cognee (Topoteretes, v0.5.3, Python 3.10-3.13, 5,881 commits, 118 contributors) is a knowledge engine that builds knowledge graphs from unstructured data. Core pipeline:

1. **Add** -- Ingest text, files (38+ formats), URLs, S3 URIs
2. **Cognify** -- Extract entities and relationships via LLM, build knowledge graph (6-stage pipeline: classify, permissions, chunk, extract, summarize, embed)
3. **Memify** -- Post-processing: prune nodes, strengthen connections, reweight edges based on usage, add derived facts
4. **Search** -- 12 search modes including GRAPH_COMPLETION (default), RAG_COMPLETION, CODE, TEMPORAL, INSIGHTS

Storage backends: Graph (Kuzu default, Neo4j, FalkorDB, Neptune), Vector (LanceDB default, ChromaDB, Qdrant, pgvector, Redis), Relational (SQLite default, PostgreSQL).

### Confidence: HIGH (verified via official docs, GitHub, blog posts, API reference)

---

### Table Stakes: What Cognee MUST Provide to Be Worth Integrating

| Feature | Why Expected | Complexity | Dependencies on Existing System | Notes |
|---------|--------------|------------|--------------------------------|-------|
| **Knowledge graph from our 13 markdown KB files** | The minimum viable integration: ingest our existing WRONG/CORRECT pairs and OCA standards into a knowledge graph so agents can query relationships between rules, not just retrieve individual rules by similarity. | LOW | Depends on: 13 existing KB markdown files | Cognee's `add()` accepts text and files directly. Our markdown files are small (a few KB each). Ingestion is trivial. The value depends on whether `cognify()` extracts meaningful entities from our rule-based format. |
| **Semantic search that returns connected knowledge** | Our current ChromaDB search finds similar OCA modules by text similarity. Cognee's GRAPH_COMPLETION should find related rules, patterns, and examples by traversing entity relationships. "What rules apply to mail.thread inheritance?" should return not just the mail.thread rule but also related dependency rules, import patterns, and test requirements. | MEDIUM | Depends on: knowledge graph populated from KB files | This is the core value proposition for Cognee. If GRAPH_COMPLETION returns better, more connected results than our current flat KB lookup, the integration is justified. If it just returns the same chunks ChromaDB would, it adds complexity without value. |
| **Incremental updates without full rebuild** | Our KB evolves (new WRONG/CORRECT pairs discovered). Cognee must support adding new knowledge without rebuilding the entire graph. | LOW | Depends on: KB update workflow | Cognee explicitly supports this: "Only new or updated files are processed on re-runs." Verified in official docs. |
| **ChromaDB as vector backend** | We already use ChromaDB for OCA module search. Cognee must work with our existing ChromaDB instance to avoid running two separate vector stores. | MEDIUM | Depends on: existing ChromaDB setup (200+ OCA repos indexed) | Cognee supports ChromaDB as a vector backend (`pip install "cognee[chromadb]"`, set `VECTOR_DB_PROVIDER="chromadb"`). However, Cognee creates its own collections -- it will NOT read our existing OCA index. We would run ChromaDB with two sets of collections: ours (OCA search) and Cognee's (KB graph). |

### Differentiators: What Would Set Our Integration Apart

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Code graph from OCA repositories** | Cognee can parse Python repositories into knowledge graphs mapping files, functions, classes, imports, and dependencies. We could build a code graph of popular OCA modules, enabling queries like "how does OCA implement approval workflows?" instead of just "find modules about approval." | HIGH | Requires: cloned OCA repos, Cognee code graph pipeline, LLM API for entity extraction | `run_code_graph_pipeline(repo_path)` extracts code structure. Combined with `SearchType.CODE`, agents could query actual implementation patterns. This goes beyond our current text-similarity search to structural understanding. Very compelling but expensive (LLM calls per repo). |
| **OCA pattern knowledge graph** | Build a graph of Odoo patterns: "mail.thread inheritance" connects to "depends on mail" connects to "requires _inherit" connects to "test with mail.followers." Agents query this graph to get complete, connected guidance instead of individual rules. | MEDIUM | Requires: curated entity/relationship extraction from KB files, possibly custom Cognee DataPoints | Our 80+ WRONG/CORRECT pairs contain implicit relationships that are lost in flat markdown. A knowledge graph could surface "if you're doing X, you also need Y and Z" chains that agents currently miss. |
| **Memify for self-improving knowledge** | Cognee's memify pipeline strengthens connections based on usage patterns and adds derived facts. As agents query the KB, frequently co-accessed rules get stronger connections. Over time, the KB learns which patterns go together. | MEDIUM | Requires: search usage tracking, periodic memify runs | This is genuinely novel for our system. Currently, our KB is static -- every rule has equal weight regardless of how often it prevents real failures. Memify could promote high-value rules and surface rule combinations that consistently appear together. |
| **Multi-hop reasoning for complex Odoo patterns** | GRAPH_COMPLETION with chain-of-thought (GRAPH_COMPLETION_COT) can do multi-hop reasoning: "This module inherits res.partner -> res.partner uses mail.thread -> mail.thread requires mail dependency -> mail dependency needs specific test patterns." Flat retrieval cannot do this. | MEDIUM | Requires: well-structured knowledge graph with entity relationships | Cognee benchmarks show "+25% with chain-of-thought reasoning" over flat RAG. For Odoo where patterns have deep dependency chains, this could significantly reduce the "missing dependency" class of errors. |
| **CODING_RULES search type** | Cognee has a dedicated `CODING_RULES` search type and supports a `developer_rules` nodeset for organizing coding standards. Our WRONG/CORRECT pairs map directly to this concept. | LOW | Requires: rules ingested into developer_rules nodeset | This is a natural fit. Our KB rules ARE coding rules. Using Cognee's purpose-built search type for them should provide better retrieval than generic similarity search. |
| **Temporal search for version-aware rules** | Cognee's TEMPORAL search mode extracts time/version constraints. Rules that apply only to Odoo 17.0 vs 18.0 could be automatically filtered based on the target version context. | LOW | Requires: version metadata in KB entries | We already have version-aware templates (17.0 vs 18.0 directories). Temporal search could extend this to the KB layer, ensuring agents get version-appropriate guidance. |

### Anti-Features: What NOT to Build with Cognee

| Anti-Feature | Why Tempting | Why Problematic | What to Do Instead |
|--------------|-------------|-----------------|-------------------|
| **Replace ChromaDB entirely with Cognee** | "Cognee handles vectors too, why maintain two systems?" | Our ChromaDB index of 200+ OCA repos is purpose-built for module discovery (text similarity over README/manifest data). Cognee is designed for knowledge graphs, not simple vector similarity search. Replacing ChromaDB would force all OCA search through Cognee's cognify pipeline, which is LLM-intensive and overkill for "find modules about inventory management." | Run them side-by-side: ChromaDB for OCA module discovery (fast, no LLM needed), Cognee for KB knowledge graph (LLM-enriched, relationship-aware). Different tools for different jobs. |
| **Cognify every OCA repository** | "Build a knowledge graph of ALL 200+ OCA repos for maximum coverage." | Each `cognify()` call uses LLM API calls for entity extraction. At 200+ repos with multiple files each, the LLM costs would be substantial (hundreds of dollars). Most repos would rarely be queried. The graph would be enormous and slow to traverse. | Cognify selectively: top 20-30 most commonly referenced OCA modules, our 13 KB files, and any modules that agents frequently fork-and-extend. Add more on demand. |
| **Real-time cognify during module generation** | "Cognify the generated module as it's being built to check for consistency." | Cognify is a batch process (classify, chunk, extract, summarize, embed) that takes seconds to minutes per document. Inserting it into the generation pipeline would add significant latency at each stage. Also, the generated code is ephemeral until validated -- cognifying invalid code pollutes the graph. | Cognify validated, approved modules post-generation. Add them to the knowledge graph so future generations benefit from past successes. |
| **Build custom Cognee pipelines from scratch** | "Cognee supports custom DataPoints and pipelines, we should build an Odoo-specific pipeline." | Custom pipelines require deep understanding of Cognee internals (Pydantic DataPoints, task functions, pipeline orchestration). This is premature before proving the default pipeline works for our data. | Use default cognify pipeline first. Evaluate results. Only build custom pipelines if default entity extraction misses Odoo-specific concepts that matter. |
| **Neo4j as graph backend** | "Neo4j is the industry standard for graph databases." | Neo4j requires running a separate server (Docker or managed service). Our system already runs Docker for Odoo validation. Adding Neo4j increases infrastructure complexity. For our scale (13 KB files + 20-30 module graphs), Kuzu (file-based, zero-config, Cognee's default) is more than sufficient. | Use Kuzu (default). It requires no server, stores data in local files, and supports Cypher queries. Migrate to Neo4j only if graph size exceeds Kuzu's capabilities (unlikely at our scale). |

---

## Part 3: Feature Dependencies and Integration Map

### Cross-Feature Dependencies

```
Agent Lightning APO
  |-- Requires: Task dataset (module generation requests with expected outcomes)
  |-- Requires: Grading function (wraps our validation pipeline)
  |-- Requires: Execution harness (simulates agent runs outside AI coding assistant)
  |-- Produces: Improved agent prompt templates
  |-- Produces: Discovered rules (diff between old/new prompts)
  |     |
  |     v
  |   Cognee knowledge base (new rules feed into KB graph)
  |
Cognee Knowledge Graph
  |-- Requires: Our 13 KB markdown files (initial data)
  |-- Requires: LLM API key (for cognify entity extraction)
  |-- Optional: ChromaDB backend (reuse existing infra)
  |-- Produces: Connected knowledge graph
  |-- Produces: GRAPH_COMPLETION search results for agents
  |     |
  |     v
  |   Agent prompts reference KB via search (agents query Cognee instead of flat KB)
  |
Existing System (unchanged)
  |-- ChromaDB OCA module search (kept separate from Cognee)
  |-- Validation pipeline (provides reward signals to Agent Lightning)
  |-- Artifact state tracking (provides generation history)
  |-- 8 agent markdown files (optimization targets for APO)
```

### Integration Priority Order

1. **Cognee KB integration FIRST** -- Lower risk, more immediate value, no GPU, works with our architecture without an execution harness. Ingest 13 KB files, enable GRAPH_COMPLETION search, measure if retrieval quality improves.

2. **Agent Lightning APO SECOND** -- Higher risk, requires building an execution harness to simulate agent runs. But the execution harness is also valuable for testing agent changes. Start with optimizing one agent (e.g., `odoo-model-gen`) as a proof of concept.

3. **Cognee code graph THIRD** -- Highest value but highest cost. Only pursue after KB integration proves the pipeline works. Start with 5 popular OCA modules, not all 200+.

4. **APO-to-KB feedback loop LAST** -- Connects the two systems. Only valuable after both are individually working.

---

## Part 4: Complexity and Effort Estimates

### Agent Lightning Integration

| Component | Effort | Risk | Notes |
|-----------|--------|------|-------|
| Install agentlightning[apo] | 1 hour | LOW | pip install, verify Python 3.10-3.12 compatibility |
| Build task dataset (50+ module specs) | 2-3 days | MEDIUM | Need diverse Odoo module specs with known-good outputs |
| Build grading function | 1 day | LOW | Wrapper around existing validation pipeline (pylint score + Docker pass/fail + test pass rate -> 0-1 reward) |
| Build execution harness | 3-5 days | HIGH | Must simulate what AI coding assistant does: load agent prompt, provide context (KB, spec), call LLM API, capture output. This is the hardest part and the biggest unknown. |
| First APO run on one agent | 1 day | MEDIUM | Configure beam search parameters, run optimization, evaluate results |
| Integrate improved prompts back into system | 1 day | LOW | Replace agent markdown with APO-optimized version, validate |
| **Total estimated effort** | **8-11 days** | **HIGH** | Execution harness is the critical path and risk |

### Cognee Integration

| Component | Effort | Risk | Notes |
|-----------|--------|------|-------|
| Install cognee + configure | 2-4 hours | LOW | pip install cognee, set LLM_API_KEY, use defaults (Kuzu + LanceDB) |
| Ingest 13 KB files | 1 day | LOW | cognee.add() for each file, cognee.cognify(), verify graph |
| Evaluate GRAPH_COMPLETION quality | 1-2 days | MEDIUM | Test queries that agents actually make, compare to current flat lookup |
| Build search integration for agents | 2-3 days | MEDIUM | Replace/augment current KB lookup with Cognee search calls |
| Set up ChromaDB backend (optional) | 1 day | LOW | Configure VECTOR_DB_PROVIDER="chromadb", verify collections are separate |
| Code graph for 5 OCA modules | 2-3 days | MEDIUM | run_code_graph_pipeline(), evaluate CODE search quality |
| Memify configuration and testing | 1-2 days | LOW | Run memify after initial cognify, verify edge strengthening |
| **Total estimated effort** | **8-12 days** | **MEDIUM** | Graph quality evaluation is the risk -- if entities extracted poorly, may need custom DataPoints |

---

## Part 5: MVP Recommendation

### What to Build First

**Priority 1: Cognee KB Integration (Table Stakes)**
1. Ingest 13 KB markdown files into Cognee
2. Enable GRAPH_COMPLETION search
3. Build thin wrapper: `search_kb(query) -> connected rules`
4. Compare results to current flat lookup on 10 real queries
5. If better: wire into agent context loading

**Priority 2: Agent Lightning APO Proof-of-Concept (Differentiator)**
1. Build grading function wrapping validation pipeline
2. Build minimal execution harness for `odoo-model-gen` only
3. Create 20-30 task dataset (module specs + expected outcomes)
4. Run APO with conservative settings (beam_width=2, beam_rounds=2)
5. Evaluate: is the optimized prompt measurably better?

**Defer:**
- Code graph pipeline: High value but high cost. Pursue after KB integration proves Cognee works for our data.
- APO for all 8 agents: Prove it works on one agent first.
- Memify self-improvement: Only meaningful after graph has usage data.
- RL fine-tuning: Not applicable to our architecture (we don't control the LLM).
- Custom RL algorithms: Zero training data exists today.

### Success Criteria

| Integration | Minimum Success | Stretch Goal |
|-------------|-----------------|--------------|
| Cognee KB | GRAPH_COMPLETION returns more relevant, connected results than flat KB lookup on 7/10 test queries | Code graph for top 5 OCA modules enables "how does OCA implement X?" queries |
| Agent Lightning APO | Optimized `odoo-model-gen` prompt produces modules that pass validation at higher rate than original prompt (measured on held-out test set) | APO discovers 3+ new rules not in current KB |

---

## Sources

### Agent Lightning
- [Official Documentation](https://microsoft.github.io/agent-lightning/latest/) -- HIGH confidence
- [Microsoft Research Blog](https://www.microsoft.com/en-us/research/blog/agent-lightning-adding-reinforcement-learning-to-ai-agents-without-code-rewrites/) -- HIGH confidence
- [GitHub Repository](https://github.com/microsoft/agent-lightning) -- HIGH confidence
- [arXiv Paper](https://arxiv.org/abs/2508.03680) -- HIGH confidence
- [APO Algorithm Docs](https://microsoft.github.io/agent-lightning/latest/algorithm-zoo/apo/) -- HIGH confidence
- [Training Tutorial](https://microsoft.github.io/agent-lightning/latest/how-to/train-first-agent/) -- HIGH confidence
- [vLLM Integration Blog](https://blog.vllm.ai/2025/10/22/agent-lightning.html) -- MEDIUM confidence

### Cognee
- [GitHub Repository](https://github.com/topoteretes/cognee) -- HIGH confidence
- [Official Docs - API Reference](https://docs.cognee.ai/api-reference/introduction) -- HIGH confidence
- [Official Docs - Vector Stores](https://docs.cognee.ai/setup-configuration/vector-stores) -- HIGH confidence
- [Official Docs - Code Graph](https://docs.cognee.ai/guides/code-graph) -- HIGH confidence
- [Architecture Blog](https://www.cognee.ai/blog/fundamentals/how-cognee-builds-ai-memory) -- HIGH confidence
- [Memify Pipeline Blog](https://www.cognee.ai/blog/cognee-news/product-update-memify) -- HIGH confidence
- [Search Types Guide](https://dev.to/chinmay_bhosale_9ceed796b/search-types-in-cognee-1jo7) -- MEDIUM confidence
- [Repo-to-Knowledge-Graph Guide](https://www.cognee.ai/blog/deep-dives/repo-to-knowledge-graph) -- HIGH confidence
- [Retrieval Deep Dive](https://www.cognee.ai/blog/deep-dives/the-art-of-intelligent-retrieval-unlocking-the-power-of-search) -- HIGH confidence
