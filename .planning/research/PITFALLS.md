# Pitfalls Research

**Domain:** Adding RL-based agent optimization (Agent Lightning) and knowledge graph pipeline (Cognee) to an existing LLM-based Odoo module code generation system
**Researched:** 2026-03-04
**Confidence:** MEDIUM-HIGH (Agent Lightning docs verified via official site; Cognee deps verified via PyPI/GitHub pyproject.toml; RL prompt optimization limitations verified across multiple academic and practitioner sources)

---

## Critical Pitfalls

### Pitfall 1: Fundamental Abstraction Mismatch -- Agent Lightning Expects an Agent Runtime, Our Agents Are Markdown Files

**What goes wrong:**
Agent Lightning is designed to optimize agents that *execute as code* -- agents built with LangChain, AutoGen, CrewAI, OpenAI Agent SDK, etc. Its tracing system intercepts LLM calls, tool invocations, and execution spans to collect `(prompt, response, reward)` triplets. Our agents are markdown files (`.claude/odoo-gen/agents/*.md`) that define system prompts consumed by the AI coding assistant (Claude Code, Gemini, etc.). There is no Python agent runtime to instrument. Agent Lightning's `agl.emit_xxx()` helpers and tracer have nothing to attach to. The entire optimization loop has no execution surface.

**Why it happens:**
The project description says "RL-based agent optimization" which sounds applicable, but Agent Lightning's architecture assumes it controls (or at least observes) the LLM inference loop. In our system, the LLM inference happens inside the user's AI coding assistant -- a black box we cannot instrument. We write the prompts, but we do not execute the LLM calls. This is a category error: we are prompt authors, not agent operators.

**How to avoid:**
- **Do not adopt Agent Lightning's full framework.** It requires a Lightning Server, Lightning Client, LightningStore, and a tracer that intercepts LLM calls. None of this maps to our architecture.
- **Instead, adopt only the APO (Automatic Prompt Optimization) concept** as a standalone pattern: collect validation outcomes (pass/fail, pylint scores, Docker test results), pair them with the agent prompt that produced the code, and use an LLM to generate prompt critiques and improvements. This is what APO does internally, but we can implement it without Agent Lightning's infrastructure.
- **Alternative approach:** Build a lightweight prompt feedback loop: `agent_prompt + module_spec -> generated_code -> validation_outcome -> prompt_critique -> improved_agent_prompt`. This captures the value of APO without the framework overhead.

**Warning signs:**
- Planning documents describe "installing Agent Lightning" or "setting up a Lightning Server" -- these require an agent runtime we do not have
- Architecture diagrams show Agent Lightning intercepting LLM calls -- impossible when calls happen inside Claude Code/Gemini
- Estimated effort for "Agent Lightning integration" exceeds 2 weeks -- the concept is simple, the framework is designed for a different architecture

**Phase to address:**
Phase 1 (Research/Feasibility) -- must validate that the chosen optimization approach matches our actual architecture before any implementation begins. A wrong architectural choice here wastes the entire milestone.

**Confidence:** HIGH (verified via [Agent Lightning official docs](https://microsoft.github.io/agent-lightning/latest/) and [architecture deep-dive](https://microsoft.github.io/agent-lightning/latest/deep-dive/birds-eye-view/))

---

### Pitfall 2: Cognee's Dependency Explosion Conflicts with the Lean Python 3.12 Constraint

**What goes wrong:**
Cognee's `pyproject.toml` declares 30+ mandatory dependencies including: `openai`, `litellm`, `mistralai`, `instructor`, `tiktoken`, `pydantic`, `numpy`, `sqlalchemy`, `aiosqlite`, `lancedb`, `alembic`, `fastapi`, `uvicorn`, `aiohttp`, `websockets`, `networkx`, `rdflib`, `kuzu`, `jinja2`, `pypdf`, `tenacity`, `langdetect`, and more. Our current project has exactly 3 core dependencies: `jinja2`, `click`, `pylint-odoo`. Adding Cognee would 10x our dependency footprint and introduce:
- **FastAPI + Uvicorn** (a web server we do not need -- we are a CLI tool/GSD extension)
- **LanceDB** as the default vector store (we already use ChromaDB)
- **SQLAlchemy + Alembic** (database migrations for a tool with no database)
- **OpenAI + LiteLLM + Mistral** (LLM API clients when our LLM calls happen through the AI coding assistant, not our Python code)
- **Kuzu** embedded graph database (mandatory, not optional)

The Python 3.12 constraint (Odoo 17 compatibility, `>=3.12,<3.13`) further constrains which versions of these dependencies will resolve. Any dependency that requires 3.13+ features breaks the build.

**Why it happens:**
Cognee is designed as a full-stack knowledge engine with its own API server, database layer, and LLM integration. It assumes it IS the application's backend. We are a utility library that generates code and validates it -- Cognee's architecture fundamentally mismatches our use case. The "6 lines of code" marketing obscures the 30+ transitive dependencies.

**How to avoid:**
- **Do not pip install cognee as a dependency.** The dependency weight is unacceptable for our use case.
- **Extract only the concepts we need:** Cognee's value proposition is turning documents into a knowledge graph for richer retrieval. We can achieve this by:
  1. Using `networkx` (already a Cognee dep, lightweight) to build a graph of our KB relationships
  2. Using our existing ChromaDB for vector search (no LanceDB duplication)
  3. Using the AI coding assistant's LLM for entity extraction (no separate OpenAI client)
  4. Implementing a simple `cognify` pipeline: parse KB markdown -> extract entities (Odoo models, patterns, rules) -> build relationship edges -> store in graph + ChromaDB
- **If Cognee is truly wanted**, install it in a separate virtual environment and communicate via subprocess or a thin REST API, keeping the main project's dependencies clean.

**Warning signs:**
- `pip install cognee` takes more than 60 seconds or downloads >500MB
- Import errors on Python 3.12 due to dependency version conflicts
- FastAPI/Uvicorn processes appearing when running CLI commands
- Test suite slowdown from dependency loading

**Phase to address:**
Phase 1 (Research/Feasibility) -- must decide build-vs-buy for knowledge graph before any implementation. If buying Cognee, the isolation strategy must be designed first.

**Confidence:** HIGH (verified via [Cognee PyPI](https://pypi.org/project/cognee/) and [Cognee pyproject.toml on GitHub](https://github.com/topoteretes/cognee/blob/main/pyproject.toml))

---

### Pitfall 3: No Reward Signal -- RL Without a Grading Function Is Random Walking

**What goes wrong:**
Agent Lightning's APO and VERL algorithms both require a reward function that scores agent performance on a 0-1 scale after each execution. For our system, the "agent execution" is: agent prompt + module spec -> AI coding assistant generates code -> validation. But:
1. **Validation is slow** -- Docker-based validation takes 30-120 seconds per module. Generating enough training data for APO (which needs rollouts across training AND validation datasets) means running hundreds of validation cycles.
2. **Reward is binary and sparse** -- module either installs or it does not. Pylint either passes or it does not. There is no gradient between "almost correct" and "completely wrong."
3. **Attribution is impossible** -- when a module fails validation, was it the model-gen agent's fault? The view-gen agent? The security-gen agent? With 8 agents contributing to one module, a single pass/fail reward cannot tell you which agent prompt needs improvement.

**Why it happens:**
RL works well when: rewards are fast (game frames), rewards are granular (continuous scores), and actions are attributable to outcomes. Code generation has none of these properties. The research confirms this: "GRPO, and other RL-style optimizers, tend to require thousands of rollouts to converge on useful prompts" and "current training does not elicit fundamentally new reasoning patterns."

**How to avoid:**
- **Design a multi-signal reward function before attempting any optimization:**
  - Pylint score (0-10, normalized to 0-1) -- fast, granular
  - Docker install success (binary 0 or 1) -- slow but definitive
  - Test pass rate (0-1 continuous) -- slow but granular
  - Code pattern matches against KB CORRECT examples (fast, granular, custom)
  - Field/model naming convention adherence (fast, checkable)
- **Per-agent attribution:** Run reward assessment per artifact type. Model generation gets model-specific pylint scores. View generation gets view-specific XML validation. Security gets ACL cross-reference checks.
- **Batch optimization:** Do not try to optimize in real-time. Collect validation outcomes across multiple module generations, then run APO in batch. This is more practical given the 30-120 second validation cycle.
- **Set a minimum data threshold:** Do not attempt prompt optimization until you have at least 50 validation runs with diverse module specs. APO reportedly works with "5-10 examples" but that is for simple classification tasks, not multi-file code generation.

**Warning signs:**
- Prompt optimization is attempted with fewer than 20 validation examples
- Reward function returns only 0 or 1 with no intermediate values
- "Optimized" prompts produce different but equally buggy code (random walking)
- Optimization takes hours due to Docker validation in the loop

**Phase to address:**
Phase 2 (Reward Signal Design) -- must be designed and validated before any prompt optimization is attempted. Without a good reward function, the entire RL/APO integration is theater.

**Confidence:** HIGH (validated against [APO docs](https://microsoft.github.io/agent-lightning/latest/algorithm-zoo/apo/), [RL for LLM reasoning survey](https://sebastianraschka.com/blog/2025/the-state-of-reinforcement-learning-for-llm-reasoning.html), and [Agent Lightning paper](https://arxiv.org/abs/2508.03680))

---

### Pitfall 4: The "Just Add AI" Trap -- Over-Engineering a Working System

**What goes wrong:**
The current system works end-to-end: 444 tests, 15,700+ LOC, 8 specialized agents, auto-fix pipeline, Docker validation, ChromaDB semantic search. The knowledge base has 80+ WRONG/CORRECT example pairs in 13 markdown files. Adding Agent Lightning + Cognee risks:
1. **Breaking what works** -- integration changes touch the core generation pipeline, validation loop, and knowledge base
2. **Solving a problem that does not exist yet** -- has anyone measured whether the current static KB is a bottleneck? Are the agent prompts actually the weak link?
3. **Complexity without corresponding value** -- a knowledge graph of 13 markdown files is a graph of ~50 nodes. ChromaDB vector search on 80 WRONG/CORRECT pairs already finds relevant patterns. What does Cognee add?

**Why it happens:**
"Intelligent Agent & Knowledge Layer" sounds like progress. The project description references Agent Lightning and Cognee by name, creating commitment before feasibility analysis. The research literature shows up to 20% improvement from knowledge graph-augmented code generation -- but those benchmarks are against systems that have NO structured knowledge base, not systems that already have a curated, domain-specific KB with explicit examples.

**How to avoid:**
- **Measure first:** Before adding any new technology, quantify the current system's failure modes:
  - What % of generated modules pass validation on first attempt?
  - What are the top 5 failure reasons? Are they addressable by better prompts or by more knowledge?
  - How often does ChromaDB search return irrelevant results?
  - How often do agents produce code with patterns that exist in the KB's WRONG examples?
- **Set success criteria before starting:** "Cognee integration is worth it if: first-pass validation rate improves from X% to Y%." Without this, you will build it, not know if it helped, and keep it because sunk cost.
- **Incremental approach:** Start with the cheapest improvements first:
  1. Better ChromaDB embeddings (switch to a code-specific embedding model)
  2. More KB examples (add examples for top failure patterns)
  3. Cross-referencing within existing KB (add explicit links between related rules)
  4. Only then: knowledge graph if cross-referencing shows value

**Warning signs:**
- No baseline metrics exist for current system performance
- "Improvement" is defined as "we added Cognee" rather than "validation pass rate increased by X%"
- The knowledge graph has fewer than 100 nodes (current KB is ~50 rules) -- a JSON file with cross-references would be simpler
- More time is spent on Cognee/Agent Lightning infrastructure than on Odoo-specific improvements

**Phase to address:**
Phase 1 (Research/Feasibility) -- establish baselines and success criteria before committing to any integration scope.

**Confidence:** HIGH (based on project history, current architecture, and research on [when knowledge graphs are worth it](https://medium.com/@claudiubranzan/from-llms-to-knowledge-graphs-building-production-ready-graph-systems-in-2025-2b4aff1ec99a))

---

### Pitfall 5: Dual Vector Store Anti-Pattern -- ChromaDB + Cognee's LanceDB

**What goes wrong:**
The system already uses ChromaDB for semantic search of Odoo modules (OCA index with cosine similarity, HNSW). Cognee defaults to LanceDB as its vector store. If both are installed:
1. **Two embedding models** -- ChromaDB uses its built-in ONNX embedding (22MB, no PyTorch), Cognee uses whatever LLM provider's embeddings
2. **Two vector databases** -- different storage, different query interfaces, different consistency guarantees
3. **Stale data divergence** -- module index updates ChromaDB but not LanceDB, KB updates go to LanceDB but not ChromaDB
4. **Double the storage** -- embeddings stored twice for overlapping content

**Why it happens:**
Cognee is designed as a complete system. It does not expect to share infrastructure with an existing vector store. ChromaDB is the project's incumbent. Nobody explicitly designs the "which vector store stores what" boundary.

**How to avoid:**
- **Single vector store policy:** Choose one. ChromaDB is already integrated, tested, and lightweight (uses built-in ONNX embeddings, no PyTorch). If using Cognee, configure it to use ChromaDB (`VECTOR_DB_PROVIDER="chromadb"` in `.env`).
- **If building custom:** Keep ChromaDB as the sole vector store. Add a graph layer (NetworkX or similar) alongside it, not instead of it. The graph provides relationships; the vector store provides similarity search. They complement, not compete.
- **Clear data boundary:** Module metadata lives in ChromaDB collection `odoo_modules`. KB knowledge lives in a separate ChromaDB collection `odoo_knowledge`. Graph relationships live in a NetworkX graph serialized to JSON. No overlap.

**Warning signs:**
- Two different vector databases running simultaneously
- Search results differ between the two stores for the same query
- "Which store should I query?" becomes a recurring question
- Index rebuild scripts need to update multiple stores

**Phase to address:**
Phase 2 (Architecture Design) -- the storage architecture must be decided before any knowledge graph implementation.

**Confidence:** HIGH (verified via [Cognee vector store docs](https://docs.cognee.ai/setup-configuration/vector-stores) and existing ChromaDB integration in `search/index.py`)

---

### Pitfall 6: Cold Start Problem -- RL/APO Needs Data You Do Not Have Yet

**What goes wrong:**
APO requires training AND validation datasets with labeled examples. For our system, a "labeled example" is: `(module_spec, agent_prompt_version, generated_code, validation_outcome)`. As of v2.1, no such dataset exists. The system generates modules interactively -- there is no persistent record of which prompts produced which code with which outcomes. Starting APO with no data means:
1. You must first build a data collection pipeline
2. Then generate enough modules to create a dataset (50+ diverse specs minimum)
3. Then run APO, which itself generates multiple rollouts per optimization step
4. Total: 200+ module generation + validation cycles before seeing any optimization benefit

At 30-120 seconds per Docker validation, this is 2-7 hours of validation time alone, not counting generation.

**Why it happens:**
Agent Lightning's examples show simple tasks (room selection, text-to-SQL) where generating 29 training examples is trivial. Code generation is orders of magnitude more expensive per example. The cold start cost is not visible until you try to actually run the optimization.

**How to avoid:**
- **Start with a data collection phase, not an optimization phase.** Instrument the current system to log: module spec, agent prompts used, generated code, all validation results (pylint scores, Docker outcomes, test results). Store as JSONL.
- **Use existing test fixtures as seed data.** The 444 tests include module fixtures that were generated and validated. These can bootstrap the dataset.
- **Synthetic data generation:** Use the rendering engine to generate modules from varied specs, run validation, and collect outcomes automatically. This can run unattended.
- **Set a "data readiness" gate:** Do not attempt APO until the dataset has at least 50 diverse module generation outcomes. Define "diverse" as: at least 5 different module categories, at least 3 different model counts per module, both passing and failing examples.

**Warning signs:**
- APO is attempted with fewer than 20 examples
- All examples in the training set are passing (no negative signal)
- All examples are simple (1-2 models) -- no complex modules represented
- Dataset collection is treated as a side task rather than a prerequisite phase

**Phase to address:**
Phase 2 (Data Collection Infrastructure) -- must be built and populated before any optimization work begins.

**Confidence:** MEDIUM (Agent Lightning docs show [29 samples as sufficient for simple tasks](https://microsoft.github.io/agent-lightning/latest/how-to/train-first-agent/), but code generation complexity is orders of magnitude higher -- extrapolation, not verified)

---

### Pitfall 7: Cognee Requires LLM API Keys for Knowledge Graph Construction -- Our System Does Not Make LLM Calls

**What goes wrong:**
Cognee's core pipeline (`cognify`) uses LLM calls to extract entities, relationships, and semantic structure from documents. It requires `openai`, `litellm`, or `mistralai` API keys configured in environment variables. Our system does NOT make direct LLM calls -- all LLM interaction happens through the user's AI coding assistant (Claude Code, Gemini). This means:
1. **API key management** -- users must configure OpenAI/Mistral API keys just for knowledge graph construction, even though they already have LLM access through their coding assistant
2. **LLM cost** -- every KB update triggers LLM calls for entity extraction. With 13 KB files, this is manageable. But if the KB grows or is regenerated frequently, costs accumulate.
3. **Rate limiting** -- LLM API calls during `cognify` may hit rate limits, especially with OpenAI
4. **Model mismatch** -- Cognee's entity extraction uses one model (e.g., GPT-4o), but the actual code generation uses whatever model the AI coding assistant provides. Different models may extract/interpret entities differently.

**Why it happens:**
Cognee is designed for applications that already have LLM API integration. Our architecture deliberately avoids direct LLM API calls -- we author prompts, the coding assistant executes them. This is another instance of the abstraction mismatch (Pitfall 1).

**How to avoid:**
- **If using Cognee:** Accept the LLM API key requirement as a build-time dependency only. Run `cognify` once during KB setup, not at runtime. Cache the graph. Users do not need API keys for normal operation.
- **If building custom:** Use rule-based entity extraction instead of LLM-based. Our KB files have a consistent structure (markdown with WRONG/CORRECT headings, specific patterns). A simple parser can extract entities without LLM calls:
  - Pattern names from headings
  - Model/field references from code blocks
  - Dependency relationships from "depends" mentions
  - WRONG/CORRECT pair associations from document structure
- **Hybrid approach:** Use LLM-based extraction once (during development) to build the initial graph, then maintain it with rule-based updates as KB files change.

**Warning signs:**
- Users report "API key not configured" errors during normal module generation
- Knowledge graph construction fails in CI (no API keys available)
- LLM costs for KB processing exceed $1 per rebuild (excessive for 13 files)
- KB updates require internet access and LLM availability

**Phase to address:**
Phase 2 (Knowledge Graph Design) -- must decide LLM-based vs rule-based entity extraction before implementation.

**Confidence:** HIGH (verified via [Cognee's core dependencies](https://github.com/topoteretes/cognee/blob/main/pyproject.toml) -- openai, litellm, mistralai are all mandatory, not optional)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Installing Cognee as a direct dependency | "6 lines of code" to knowledge graph | 30+ transitive deps, Python version conflicts, FastAPI/Uvicorn bloat, double vector store | Never -- use concept extraction only, or isolate in separate venv |
| Using Agent Lightning's full framework | "Zero code change" RL integration | Requires agent runtime we do not have, Lightning Server overhead, VERL needs PyTorch (~2GB) | Never -- extract APO concept, implement as lightweight prompt feedback loop |
| Skipping baseline measurements | Ship features faster | Cannot prove value of new integrations, no rollback criteria | Never -- measure before optimizing |
| Binary reward (pass/fail only) | Simple to implement | RL cannot learn from sparse signal, prompt optimization random walks | Only acceptable as MVP if supplemented with granular signals within 2 sprints |
| Single global prompt optimization | Optimize one prompt for all module types | Prompt overfitting to common patterns, rare module types degrade by up to 30% | Never -- optimize per agent, per module complexity tier |
| Using OpenAI embeddings in Cognee + ONNX in ChromaDB | Each tool uses its default | Different embedding spaces cannot be compared, dual index maintenance | Never -- standardize on one embedding model |
| Storing knowledge graph in Cognee's default LanceDB | Quick start, no configuration | Two vector stores, divergent data, double storage cost | Only during prototyping, must migrate to ChromaDB before merge |
| Running APO optimization in the Docker validation loop | Real reward signal from real validation | 30-120 seconds per validation, 200+ rollouts = hours of compute | Never -- separate optimization from generation pipeline |

---

## Integration Gotchas

Common mistakes when connecting to external services and libraries.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Agent Lightning APO | Trying to trace LLM calls that happen inside Claude Code/Gemini | Build a separate feedback loop: log prompt + outcome, run APO offline on collected data |
| Agent Lightning VERL | Installing PyTorch + vLLM for weight training when we use hosted LLMs | Use APO only (prompt optimization). VERL is for fine-tuning your own models, which we do not do. |
| Cognee + ChromaDB | Two vector stores with different embeddings, inconsistent search results | Configure Cognee to use ChromaDB as vector backend, OR build custom graph without Cognee |
| Cognee KB ingestion | Running `cognify` on every KB change, incurring LLM costs | Run `cognify` once to build initial graph; use rule-based updates for incremental changes |
| Cognee Python 3.12 | Assuming all 30+ deps resolve cleanly on `>=3.12,<3.13` | Test dependency resolution in isolated venv before committing to Cognee; pin exact versions |
| NetworkX graph serialization | Building graph in memory, losing it between CLI invocations | Serialize to JSON (node-link format) alongside ChromaDB persistence |
| APO prompt validation | Optimized prompt is syntactically valid but semantically wrong for Odoo domain | Include domain-specific validation in reward: does the prompt reference Odoo 17 API correctly? |
| Reward function design | Using Docker validation as the only reward signal | Combine fast signals (pylint, pattern matching) with slow signals (Docker) in a weighted reward |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| LLM-based entity extraction on every KB update | 5-30 second delay + API cost per KB file change | Cache extracted entities; re-extract only changed files; use rule-based extraction for structured KB | >20 KB files or frequent updates |
| Full graph traversal for every query | Query latency grows with graph size | Index common traversal paths; limit traversal depth to 2-3 hops | >500 nodes in knowledge graph |
| APO rollout during module generation | Generation time increases from seconds to minutes | Run APO offline in batch; apply optimized prompts as static updates | Any real-time usage |
| Storing full module source in knowledge graph nodes | Graph database size explodes; traversal slows | Store only metadata + ChromaDB document ID; retrieve full content from ChromaDB when needed | >100 modules indexed |
| ChromaDB + NetworkX graph both in memory | Memory usage doubles; startup time increases | Lazy-load graph on first query; ChromaDB already handles its own persistence | >1000 nodes or >10MB graph |
| Synchronous Cognee pipeline in CLI | CLI hangs during `cognify` processing | Run knowledge graph updates asynchronously or as a background task | Any user-facing operation |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing OpenAI/Mistral API keys in project config files | API key exposure in git commits | Use environment variables only; add `.env` to `.gitignore`; validate key presence at runtime |
| Cognee's FastAPI server exposed on network | Unauthorized access to knowledge graph, potential data exfiltration | If using Cognee server mode, bind to localhost only; better yet, use Cognee as library, not server |
| Untrusted module code executed during reward evaluation | Generated Odoo modules could contain malicious code that runs during Docker validation | Already mitigated by Docker isolation; ensure Docker containers have no network access during validation |
| Knowledge graph contains proprietary Odoo EE patterns | Leaking Enterprise-only patterns via graph queries | Separate CE and EE knowledge; tag nodes with edition; filter queries by edition context |
| APO-generated prompts could include prompt injection | Optimized prompts might contain adversarial patterns that cause LLM misbehavior | Validate optimized prompts against a whitelist of allowed prompt structures before applying |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Requiring OpenAI API key for basic functionality | Users who only have Claude Code access cannot use the system | Make LLM-dependent features optional; knowledge graph construction is a developer/admin task, not user-facing |
| Knowledge graph rebuild takes minutes with LLM calls | User waits or thinks system is broken | Show progress indicator; run in background; cache aggressively |
| "Optimized" prompts produce different (not better) output | User confusion: "it was working before" | Version prompt changes; A/B test before deploying; allow rollback to previous prompt version |
| Agent Lightning training loop visible to users | Users see cryptic RL training output during normal module generation | Completely separate optimization from generation; optimization is a developer workflow, not a user workflow |
| Knowledge graph adds latency to module search | Search that was instant now takes 2-3 seconds for graph traversal | Cache frequent queries; use graph only for relationship-enriched queries, not as primary search |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Knowledge Graph "works":** Often missing relationship validation -- verify that extracted entities actually correspond to real Odoo models/fields, not LLM hallucinations
- [ ] **APO "optimized" a prompt:** Often missing A/B validation -- verify the optimized prompt performs better on held-out test cases, not just the training set (prompt overfitting is documented at up to 30% performance drop on reformulated inputs)
- [ ] **Cognee integration "complete":** Often missing ChromaDB unification -- verify there is only ONE vector store, not two competing ones
- [ ] **Reward function "designed":** Often missing per-agent attribution -- verify you can tell WHICH agent's prompt needs improvement when a module fails, not just that "it failed"
- [ ] **Data collection "sufficient":** Often missing diversity -- verify the dataset includes failing examples, complex modules (5+ models), and multiple Odoo module categories, not just simple passing cases
- [ ] **Graph search "faster":** Often missing baseline comparison -- verify graph-augmented search is actually faster/more relevant than ChromaDB-only search with the same query
- [ ] **Prompt optimization "converged":** Often missing stability check -- verify the optimized prompt produces consistent results across 10+ runs, not just one good result
- [ ] **Dependencies "resolved":** Often missing Python 3.12 constraint verification -- verify ALL transitive dependencies work with `>=3.12,<3.13`, not just direct dependencies

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Agent Lightning fully integrated but no execution surface | MEDIUM | Extract the reward function and prompt feedback loop code; discard Lightning Server/Client infrastructure; rewrite as standalone prompt optimizer |
| Cognee installed as direct dependency, conflicts everywhere | LOW | Remove from pyproject.toml; extract the 3 concepts needed (entity extraction, graph building, graph query) into standalone modules using networkx only |
| Dual vector stores causing inconsistent search | MEDIUM | Pick ChromaDB (incumbent); migrate any Cognee-stored data; update all queries to use single store; remove LanceDB dependency |
| APO optimized prompts that are worse than originals | LOW | Revert to pre-optimization prompts (git); discard APO results; re-examine reward function before retrying |
| Cold start: optimization attempted with insufficient data | LOW | Stop optimization; switch to data collection mode; set calendar reminder to revisit after 50+ examples accumulated |
| LLM API costs from Cognee exceeded budget | LOW | Switch to rule-based entity extraction; remove openai/litellm deps; rebuild graph with parser-based approach |
| Knowledge graph too complex to maintain | MEDIUM | Simplify to a flat relationship map (JSON); keep ChromaDB for search; use graph only for explicit cross-references between KB rules |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Abstraction mismatch (no agent runtime) | Phase 1: Research/Feasibility | Architecture doc explicitly states "we build a prompt feedback loop, not an Agent Lightning integration" |
| Cognee dependency explosion | Phase 1: Research/Feasibility | `pyproject.toml` has no more than 5 new dependencies for knowledge graph features |
| No reward signal | Phase 2: Reward Signal Design | Reward function returns continuous 0-1 score; tested on 10+ diverse module specs |
| Over-engineering working system | Phase 1: Research/Feasibility | Baseline metrics document exists with current pass rates before any changes |
| Dual vector store | Phase 2: Architecture Design | Architecture doc specifies single vector store (ChromaDB) for all features |
| Cold start / insufficient data | Phase 2: Data Collection | Dataset of 50+ module generation outcomes exists before optimization begins |
| Cognee LLM API requirement | Phase 2: Knowledge Graph Design | Entity extraction works without LLM API keys (rule-based for structured KB) |
| Prompt overfitting | Phase 3: Prompt Optimization | A/B test protocol defined; held-out validation set shows improvement on unseen specs |
| Maintenance burden | Phase 3: Integration Testing | Integration tests verify graph + vector store + prompt optimization work together; CI runs clean |

---

## Honest Assessment: Is This Integration Worth It?

### Agent Lightning / RL Prompt Optimization

**Verdict: The CONCEPT is valuable. The FRAMEWORK is wrong for our architecture.**

APO (Automatic Prompt Optimization) could improve agent prompts over time. But Agent Lightning assumes you run an agent execution loop it can instrument. We author markdown prompts consumed by external AI coding assistants. The right approach is to implement the APO algorithm's core loop (collect outcomes -> generate critiques -> improve prompts) as a lightweight Python module, NOT to install Agent Lightning.

**Expected effort for concept extraction:** 2-3 days
**Expected effort for full Agent Lightning integration:** 2-3 weeks (and it will not work)
**Expected improvement:** Modest (5-15% better first-pass validation rates), based on APO literature showing "5-10 examples" baseline. Code generation is harder than APO's published benchmarks.

### Cognee / Knowledge Graph

**Verdict: The CONCEPT is valuable for larger KBs. Current KB is too small to benefit.**

A knowledge graph adds value when you have hundreds of interconnected entities where relationships matter for retrieval. Our KB has 13 files with ~80 WRONG/CORRECT pairs. This is a flat lookup table, not a graph problem. The right approach:

1. **Now:** Add explicit cross-references to existing KB files (costs nothing, immediate value)
2. **When KB reaches 50+ files:** Consider a lightweight graph (NetworkX + JSON serialization)
3. **When KB reaches 200+ files:** Consider Cognee (if dependency story improves) or a custom knowledge graph pipeline

**Expected effort for cross-references:** 1 day
**Expected effort for NetworkX graph:** 3-5 days
**Expected effort for full Cognee integration:** 2-3 weeks (dependency hell + LLM API keys)
**Expected improvement from graph at current KB size:** Near zero (13 files are greppable)

---

## Sources

**Agent Lightning:**
- [Agent Lightning official docs](https://microsoft.github.io/agent-lightning/latest/)
- [Agent Lightning GitHub](https://github.com/microsoft/agent-lightning)
- [Agent Lightning architecture deep-dive](https://microsoft.github.io/agent-lightning/latest/deep-dive/birds-eye-view/)
- [APO algorithm docs](https://microsoft.github.io/agent-lightning/latest/algorithm-zoo/apo/)
- [Agent Lightning installation](https://microsoft.github.io/agent-lightning/latest/tutorials/installation/)
- [Agent Lightning paper (arXiv)](https://arxiv.org/abs/2508.03680)
- [Microsoft Research blog on Agent Lightning](https://www.microsoft.com/en-us/research/blog/agent-lightning-adding-reinforcement-learning-to-ai-agents-without-code-rewrites/)

**Cognee:**
- [Cognee GitHub](https://github.com/topoteretes/cognee)
- [Cognee PyPI](https://pypi.org/project/cognee/)
- [Cognee pyproject.toml](https://github.com/topoteretes/cognee/blob/main/pyproject.toml)
- [Cognee vector store configuration](https://docs.cognee.ai/setup-configuration/vector-stores)
- [Cognee GraphRAG approach](https://www.cognee.ai/blog/deep-dives/cognee-graphrag-supercharging-search-with-knowledge-graphs-and-vector-magic)

**RL/Prompt Optimization:**
- [State of RL for LLM reasoning (Sebastian Raschka)](https://sebastianraschka.com/blog/2025/the-state-of-reinforcement-learning-for-llm-reasoning.html)
- [APO concept overview (Cameron Wolfe)](https://cameronrwolfe.substack.com/p/automatic-prompt-optimization)
- [Prompt overfitting in RL (NAACL 2025)](https://aclanthology.org/2025.findings-naacl.390.pdf)

**Knowledge Graphs:**
- [Production-ready knowledge graphs 2025](https://medium.com/@claudiubranzan/from-llms-to-knowledge-graphs-building-production-ready-graph-systems-in-2025-2b4aff1ec99a)
- [KG-based repository-level code generation](https://arxiv.org/html/2505.14394v1)
- [Context-augmented code generation with programming KGs](https://arxiv.org/abs/2410.18251)

---
*Pitfalls research for: Agent Lightning + Cognee integration into Odoo module automation system*
*Researched: 2026-03-04*
