# Architecture: Agent Lightning + Cognee Integration

**Domain:** RL-based agent optimization + knowledge graph pipeline for Odoo module automation
**Researched:** 2026-03-04
**Confidence:** MEDIUM -- both tools are well-documented and actively maintained, but integrating them with our specific architecture (markdown-based agents inside AI coding assistants, not API-based agents) is a novel application that requires adaptation of standard patterns.

## The Fundamental Question

**Can RL optimize LLM-prompt-based agents?**

**YES, but not through traditional RL weight updates.** Our agents are markdown files (`agents/odoo-model-gen.md`, `agents/odoo-view-gen.md`, etc.) that run inside AI coding assistants (Claude Code, Gemini, Codex). We do not train the underlying LLMs. Instead, we optimize the **prompts themselves** using Agent Lightning's APO (Automatic Prompt Optimization) algorithm.

APO works by: (1) running the agent with a current prompt template, (2) collecting execution traces and outcomes, (3) generating textual critiques of the prompt, (4) rewriting the prompt to address weaknesses, (5) repeating. This is exactly what we need -- our agents ARE prompts.

**Critical distinction:**
- RL fine-tuning (PPO/GRPO) = trains model weights. Requires GPU, open-source models. NOT applicable to us.
- APO = optimizes prompt text iteratively. Requires only LLM API access. APPLICABLE to us.
- Our 8 agent markdown files are the optimization targets.

**Confidence:** MEDIUM -- APO is documented to work with API-based agents (LangChain, OpenAI SDK). Adapting it to optimize markdown agent files that run inside Claude Code/Gemini as system prompts is novel. The core algorithm (evaluate, critique, rewrite) should transfer, but the integration plumbing needs custom work.

## Recommended Architecture

### Current 4-Layer Architecture (Before Integration)

```
Layer 4: AI Coding Assistant (USER'S ENVIRONMENT)
  Claude Code, Gemini, Codex, OpenCode
  Reads: agents/*.md, knowledge/*.md, commands/*.md

Layer 3: Python Utilities (BUILT BY US)
  Jinja2 rendering, pylint-odoo, Docker validation
  ChromaDB semantic search, auto-fix pipeline
  context7.py, mcp/server.py

Layer 2: Odoo Extension (BUILT BY US)
  8 agents (markdown), 13 commands (markdown)
  Jinja2 templates, 13 KB files (markdown)
  workflows/*.md

Layer 1: GSD Orchestration (INHERITED)
  Context management, state, phases, checkpoints, git
```

### Proposed 5-Layer Architecture (After Integration)

```
Layer 5: Intelligence Layer (NEW)
  ┌─────────────────────────────────────────────────────┐
  │  Agent Lightning APO           Cognee KG Pipeline   │
  │  ┌──────────────────┐        ┌───────────────────┐  │
  │  │ Prompt Optimizer  │        │ Knowledge Engine  │  │
  │  │ ┌──────────────┐ │        │ ┌───────────────┐ │  │
  │  │ │ Rollout       │ │        │ │ cognee.add()  │ │  │
  │  │ │ Runner        │ │        │ │ (ingest KB)   │ │  │
  │  │ ├──────────────┤ │        │ ├───────────────┤ │  │
  │  │ │ Grader /      │ │        │ │ cognee.       │ │  │
  │  │ │ Reward Fn     │ │        │ │ cognify()     │ │  │
  │  │ ├──────────────┤ │        │ │ (build graph) │ │  │
  │  │ │ APO Trainer   │ │        │ ├───────────────┤ │  │
  │  │ │ (critique +   │ │        │ │ cognee.       │ │  │
  │  │ │  rewrite)     │ │        │ │ search()      │ │  │
  │  │ └──────────────┘ │        │ │ (hybrid query)│ │  │
  │  └──────────────────┘        │ └───────────────┘ │  │
  │         │                    └───────────────────┘  │
  │         │ writes optimized        │ serves enriched │
  │         │ agents/*.md             │ context          │
  │         ▼                         ▼                  │
  └─────────────────────────────────────────────────────┘
           │                          │
Layer 4: AI Coding Assistant (USER'S ENVIRONMENT)
  Claude Code, Gemini, Codex, OpenCode
  Reads: agents/*.md (now APO-optimized)
  Reads: knowledge from Cognee (graph-enriched context)

Layer 3: Python Utilities (BUILT BY US)
  Jinja2 rendering, pylint-odoo, Docker validation
  ChromaDB search (AUGMENTED by Cognee, not replaced)
  auto-fix pipeline, context7.py, mcp/server.py
  NEW: outcome_collector.py (feeds Agent Lightning)
  NEW: cognee_bridge.py (wraps Cognee API for KB)

Layer 2: Odoo Extension (BUILT BY US)
  8 agents (markdown) -- NOW targets for APO optimization
  13 commands (markdown), Jinja2 templates
  13 KB files (markdown) -- NOW also ingested by Cognee
  workflows/*.md

Layer 1: GSD Orchestration (INHERITED)
  Context management, state, phases, checkpoints, git
```

### Component Boundaries

| Component | Responsibility | Layer | New/Modified | Communicates With |
|-----------|---------------|-------|-------------|-------------------|
| **APO Trainer** | Runs prompt optimization cycles on agent markdown files | L5 (new) | NEW | Rollout Runner, Grader, Agent files (L2) |
| **Rollout Runner** | Executes agents against test tasks, collects traces | L5 (new) | NEW | Docker validation (L3), Agent files (L2) |
| **Grader / Reward Function** | Scores agent outputs (pylint pass rate, Docker install success, test pass count) | L5 (new) | NEW | Validation pipeline (L3) |
| **Cognee Knowledge Engine** | Ingests KB markdown, builds knowledge graph, serves hybrid search | L5 (new) | NEW | KB files (L2), cognee_bridge (L3) |
| **outcome_collector.py** | Captures validation results in Agent Lightning's span format | L3 | NEW | Docker runner, pylint runner, APO Trainer |
| **cognee_bridge.py** | Wraps Cognee's Python API; provides `enrich_context()` for agents | L3 | NEW | Cognee Engine (L5), agents (L2) |
| **ChromaDB search** | Continues module similarity search (Cognee does NOT replace this) | L3 | UNCHANGED | Search commands |
| **Agent markdown files** | System prompts for AI coding assistants -- now APO optimization targets | L2 | MODIFIED (by APO) | AI Coding Assistant (L4) |
| **KB markdown files** | Odoo conventions/patterns -- now also source data for Cognee | L2 | UNCHANGED (source) | Cognee Engine (L5) |
| **Validation pipeline** | pylint-odoo + Docker install + test execution | L3 | MODIFIED (adds outcome reporting) | Grader (L5) |
| **GSD Orchestration** | Phase execution, checkpoints, state | L1 | UNCHANGED | Everything above |

## Integration Surface Area

### Agent Lightning Integration Points

Agent Lightning's APO algorithm optimizes prompt templates. Our agents ARE prompt templates (markdown files). The integration is:

```
                    AGENT LIGHTNING APO LOOP
                    ========================

1. SELECT agent to optimize (e.g., odoo-model-gen.md)
2. LOAD current prompt template from agents/odoo-model-gen.md
3. RUN rollouts:
   For each task in training dataset:
     a. Invoke the agent via AI coding assistant subprocess
        (claude --print -p "Generate model for [task spec]"
         --system-prompt agents/odoo-model-gen.md)
     b. Capture generated module files
     c. Run validation pipeline:
        - pylint-odoo check
        - Docker install test
        - Odoo test execution
     d. Grade outcome (0.0 to 1.0):
        - 0.0 = pylint errors + install fails
        - 0.5 = installs but tests fail
        - 0.8 = installs, tests pass, minor lint warnings
        - 1.0 = clean install, all tests pass, zero lint issues
4. CRITIQUE: LLM analyzes rollout traces + grades → textual gradient
5. REWRITE: LLM edits prompt based on critique → new agent markdown
6. VALIDATE on held-out tasks
7. REPEAT (default: 3 beam rounds)
8. OUTPUT: optimized agents/odoo-model-gen.md

              ┌──────────────┐
              │  Task Dataset │ (module specs + expected outcomes)
              └──────┬───────┘
                     │
                     ▼
    ┌────────────────────────────────┐
    │  Agent Lightning APO Trainer   │
    │  algorithm=agl.APO(llm_client) │
    │  n_runners=4                   │
    └────────┬───────────────────────┘
             │
    ┌────────▼────────┐     ┌──────────────────────┐
    │  Rollout Runner  │────▶│  AI Coding Assistant  │
    │  (spawns agent)  │     │  (claude --print)     │
    └────────┬────────┘     └──────────┬───────────┘
             │                         │
             │    ┌────────────────────┘
             │    │  generated module files
             │    ▼
    ┌────────┴────────────┐
    │  Validation Pipeline │
    │  pylint + Docker     │
    └────────┬────────────┘
             │ scores (0.0-1.0)
             ▼
    ┌────────────────────┐
    │  Grader Function    │
    │  (reward signal)    │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │  APO Critique +     │
    │  Prompt Rewrite     │
    │  (textual gradient) │
    └────────┬───────────┘
             │ improved prompt
             ▼
    ┌────────────────────┐
    │  agents/*.md        │
    │  (updated file)     │
    └────────────────────┘
```

**What changes in existing components:**

| Component | Change | Effort |
|-----------|--------|--------|
| `validation/docker_runner.py` | Add structured outcome reporting (JSON with pass/fail, error counts, test results) | LOW -- extend `DockerResult` |
| `validation/pylint_runner.py` | Add structured outcome reporting (error count, warning count, categories) | LOW -- extend `PylintResult` |
| `validation/report.py` | Add `to_reward_signal()` method that computes 0.0-1.0 score | LOW -- new method |
| Agent markdown files | Become APO optimization targets; add version tracking header | LOW -- metadata addition |

**What is NEW:**

| Component | Purpose | Effort |
|-----------|---------|--------|
| `python/src/odoo_gen_utils/intelligence/apo_trainer.py` | Wraps Agent Lightning's APO for our agent format | HIGH |
| `python/src/odoo_gen_utils/intelligence/rollout_runner.py` | Spawns AI coding assistant, runs agent, captures output | HIGH |
| `python/src/odoo_gen_utils/intelligence/grader.py` | Converts validation results to reward signals | MEDIUM |
| `python/src/odoo_gen_utils/intelligence/task_dataset.py` | Manages training/validation task specs | MEDIUM |
| `training_data/tasks/` | Directory of module specs for training (JSON) | MEDIUM |
| `training_data/golden/` | Known-good module outputs for grading | MEDIUM |
| CLI command: `/odoo-gen:optimize` | Trigger APO training cycle | LOW |

### Cognee Integration Points

Cognee replaces the read path of our knowledge base, not the storage format. Our 13 markdown KB files remain the source of truth. Cognee ingests them into a knowledge graph, enabling relationship-aware retrieval instead of flat file reads.

```
              COGNEE KNOWLEDGE PIPELINE
              =========================

INGESTION (one-time + incremental updates):

  knowledge/*.md (13 files)
       │
       ▼
  cognee.add("knowledge/models.md")
  cognee.add("knowledge/views.md")
  cognee.add("knowledge/security.md")
  ... (all 13 files)
       │
       ▼
  cognee.cognify()
       │
       ├── Extract: chunk documents, identify entities
       │   (model names, field types, decorators, patterns)
       │
       ├── Relate: build edges between concepts
       │   ("Many2one field" --requires--> "comodel_name parameter")
       │   ("mail.thread" --depends-on--> "mail module in depends")
       │   ("@api.constrains" --forbids--> "@api.multi")
       │
       └── Embed: generate vector embeddings for each chunk
           (stored in LanceDB or existing ChromaDB)

RETRIEVAL (during agent execution):

  Agent needs context for "generate a Many2one field to res.partner"
       │
       ▼
  cognee.search("Many2one field res.partner")
       │
       ├── Vector search: finds semantically similar KB chunks
       │
       ├── Graph traversal: follows relationships
       │   "Many2one" → needs comodel_name → needs depends
       │   "res.partner" → belongs to base module → no extra depends
       │
       └── Returns: enriched context with related patterns
           (not just the chunk about Many2one, but also
            the related comodel rules, import patterns,
            and dependency resolution rules)

       ┌───────────────────────────────────────────┐
       │  Enriched Context (for agent prompt)       │
       │                                            │
       │  Primary: Many2one field declaration       │
       │  Related: comodel_name must be valid model │
       │  Related: add depends in __manifest__.py   │
       │  Related: import from odoo.fields          │
       │  Pattern: partner_id = fields.Many2one(    │
       │           "res.partner", string=_("...")    │
       │  Warning: do NOT use @api.multi with this  │
       └───────────────────────────────────────────┘
```

**What changes in existing components:**

| Component | Change | Effort |
|-----------|--------|--------|
| Knowledge markdown files | UNCHANGED -- remain source of truth | NONE |
| ChromaDB search (`search/index.py`) | UNCHANGED -- continues serving module similarity search | NONE |
| Agent markdown files | Add instruction to query Cognee for context enrichment | LOW |
| Commands (e.g., `new.md`, `validate.md`) | Add step to populate Cognee if not initialized | LOW |

**What is NEW:**

| Component | Purpose | Effort |
|-----------|---------|--------|
| `python/src/odoo_gen_utils/intelligence/cognee_bridge.py` | Wraps Cognee API; `ingest_kb()`, `enrich_context(query)`, `rebuild_graph()` | MEDIUM |
| `python/src/odoo_gen_utils/intelligence/kb_sync.py` | Detects KB file changes, triggers incremental re-ingestion | LOW |
| CLI command: `/odoo-gen:kb-sync` | Rebuild Cognee graph from knowledge/*.md | LOW |
| MCP tool: `search_knowledge` | Query Cognee graph from within AI coding assistant | MEDIUM |
| `.env` configuration | Cognee LLM provider, graph store, vector store settings | LOW |

### Cognee Does NOT Replace ChromaDB

This is important. The two serve different purposes:

| Concern | ChromaDB (existing) | Cognee (new) |
|---------|--------------------|----|
| **What it stores** | Module descriptions, manifests, README content from GitHub/OCA | Odoo development patterns, conventions, rules from our KB |
| **What it answers** | "Find modules similar to X" (module discovery) | "What rules apply when building X?" (pattern retrieval) |
| **Data source** | External (GitHub repos, OCA modules) | Internal (our 13 KB markdown files) |
| **Search type** | Vector similarity only | Hybrid: vector + graph traversal |
| **Update frequency** | On `/odoo-gen:index` command | On KB file changes |

ChromaDB handles module DISCOVERY. Cognee handles knowledge ENRICHMENT. They are complementary.

## Data Flow Changes

### Current Data Flow (v2.1)

```
User describes module → Agent reads knowledge/*.md files directly →
Agent generates code → Validation pipeline → Results logged → Done
```

Knowledge retrieval is flat file reads. No relationship awareness. The agent gets the whole `knowledge/models.md` file even if it only needs the Many2one section. No connection between related concepts across files.

### New Data Flow (v3.0)

```
User describes module
    │
    ├──▶ Cognee: enrich_context(module_description)
    │       Returns: relevant KB chunks + related patterns
    │       (graph-aware, not just keyword match)
    │
    ├──▶ Agent (APO-optimized prompt) generates code
    │       Uses: enriched context from Cognee
    │       Prompt: iteratively improved by Agent Lightning
    │
    ├──▶ Validation pipeline runs
    │       pylint + Docker + tests
    │       NEW: reports structured outcomes
    │
    ├──▶ Outcome Collector captures results
    │       Formats as Agent Lightning spans
    │       Stores in training dataset
    │
    └──▶ (Periodically) APO Trainer runs
            Uses accumulated outcomes
            Generates improved agent prompts
            Writes optimized agents/*.md
```

### Feedback Loop (the key architectural innovation)

```
┌────────────────────────────────────────────────────────────┐
│                    CONTINUOUS IMPROVEMENT LOOP              │
│                                                            │
│  1. Agent generates module (using current prompt)          │
│                    │                                       │
│                    ▼                                       │
│  2. Validation pipeline scores output                     │
│                    │                                       │
│                    ▼                                       │
│  3. Outcome stored as training data                       │
│                    │                                       │
│                    ▼                                       │
│  4. APO analyzes accumulated outcomes                     │
│     - What patterns of errors recur?                      │
│     - Which prompt sections cause issues?                 │
│     - What KB context was missing?                        │
│                    │                                       │
│                    ▼                                       │
│  5. APO rewrites agent prompt to address weaknesses       │
│     - Add guardrails for common errors                    │
│     - Strengthen weak instruction sections                │
│     - Add/refine examples                                 │
│                    │                                       │
│                    ▼                                       │
│  6. Improved agent generates better modules               │
│     (back to step 1)                                      │
│                                                            │
│  Meanwhile:                                                │
│  7. Cognee enriches context with related patterns          │
│     - Validation failures → new KB patterns ingested       │
│     - Graph connections surface non-obvious relationships  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Patterns to Follow

### Pattern 1: Disaggregated Training (Agent Lightning)

**What:** Separate agent execution from optimization. Agents run in their normal environment (AI coding assistants). Optimization happens offline in a separate process.

**Why:** Our agents are markdown prompts loaded by Claude Code/Gemini. We cannot modify how those tools execute agents. We CAN modify the markdown files between runs.

**How:**
```python
# apo_trainer.py -- runs as standalone Python process
import agentlightning as agl

async def optimize_agent(agent_name: str, task_dataset: list[dict]):
    """Optimize a single agent's markdown prompt via APO."""
    agent_md_path = f"agents/{agent_name}.md"
    current_prompt = Path(agent_md_path).read_text()

    trainer = agl.Trainer(
        algorithm=agl.APO(
            async_openai_client=openai_client,  # or litellm proxy
            gradient_model="gpt-4.1-mini",
            apply_edit_model="gpt-4.1-mini",
            beam_width=3,
            beam_rounds=3,
        ),
        n_runners=4,
        initial_resources={
            "agent_prompt": agl.PromptTemplate(
                template=current_prompt,
                engine="f-string",
            )
        },
    )

    result = trainer.fit(
        agent=make_rollout_fn(agent_name),
        train_dataset=task_dataset[:80],
        val_dataset=task_dataset[80:],
    )

    optimized_prompt = result.best_resources["agent_prompt"]
    Path(agent_md_path).write_text(optimized_prompt)
```

**Confidence:** MEDIUM -- APO is documented for API-based agents. Adapting to subprocess-based agents (claude --print) requires custom rollout functions.

### Pattern 2: Knowledge Graph Augmented Retrieval (Cognee)

**What:** Instead of agents reading flat markdown files, they query a knowledge graph that returns contextually relevant chunks with relationship-aware connections.

**Why:** Our 13 KB files total ~3,000 lines. Agents cannot consume all of them in every prompt. Currently, agents either get too much context (whole file) or too little (manual selection). Cognee's hybrid search returns the right context automatically.

**How:**
```python
# cognee_bridge.py
import cognee

async def ingest_kb(kb_dir: str = "knowledge/"):
    """Ingest all KB markdown files into Cognee."""
    for md_file in Path(kb_dir).glob("*.md"):
        await cognee.add(str(md_file), dataset_name="odoo-kb")
    await cognee.cognify()

async def enrich_context(query: str, max_chunks: int = 10) -> str:
    """Query Cognee for relevant KB context with relationships."""
    results = await cognee.search(query)
    # Format results as markdown context block
    context_parts = []
    for result in results[:max_chunks]:
        context_parts.append(f"### {result.source}\n{result.content}")
        if result.related:
            for rel in result.related:
                context_parts.append(f"**Related ({rel.relation}):** {rel.content}")
    return "\n\n".join(context_parts)
```

**Confidence:** HIGH for ingestion (Cognee natively supports .md files). MEDIUM for retrieval quality (depends on entity extraction quality from Odoo-specific markdown).

### Pattern 3: Outcome-Based Reward Signal

**What:** Convert our existing validation pipeline outputs into numerical reward signals for Agent Lightning.

**Why:** Agent Lightning's APO needs a grading function. We already have grading infrastructure (pylint scores, Docker pass/fail, test counts). We just need to normalize them to 0.0-1.0.

**How:**
```python
# grader.py
from dataclasses import dataclass

@dataclass(frozen=True)
class OutcomeReward:
    pylint_score: float      # 0.0-1.0 (errors=0, warnings penalized)
    install_score: float     # 0.0 or 1.0 (binary: installs or not)
    test_score: float        # 0.0-1.0 (fraction of tests passing)
    overall: float           # weighted combination

def grade_module_output(
    pylint_result: "PylintResult",
    docker_result: "DockerResult",
) -> OutcomeReward:
    # Pylint: start at 1.0, subtract for errors/warnings
    pylint_score = max(0.0, 1.0 - (pylint_result.error_count * 0.2)
                                 - (pylint_result.warning_count * 0.05))

    # Docker install: binary
    install_score = 1.0 if docker_result.install_success else 0.0

    # Tests: fraction passing
    if docker_result.tests_total > 0:
        test_score = docker_result.tests_passed / docker_result.tests_total
    else:
        test_score = 0.0  # no tests = bad

    # Weighted overall (install is most important)
    overall = (install_score * 0.5
             + test_score * 0.3
             + pylint_score * 0.2)

    return OutcomeReward(
        pylint_score=pylint_score,
        install_score=install_score,
        test_score=test_score,
        overall=overall,
    )
```

**Confidence:** HIGH -- straightforward mapping from existing validation outputs to numerical rewards.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Replacing ChromaDB with Cognee for Module Search

**What people might do:** Since Cognee has vector search, replace ChromaDB entirely.
**Why it is wrong:** ChromaDB indexes EXTERNAL modules (GitHub/OCA repos) for module discovery. Cognee indexes INTERNAL knowledge (our KB files) for pattern retrieval. Different data, different purpose, different update cadence.
**Do this instead:** Keep ChromaDB for module search (`/odoo-gen:search`). Add Cognee for knowledge enrichment (agent context). They are complementary.

### Anti-Pattern 2: Using RL Fine-Tuning Instead of APO

**What people might do:** Try to use Agent Lightning's PPO/GRPO algorithms to fine-tune Claude or GPT model weights.
**Why it is wrong:** We use closed-source LLMs (Claude, GPT). We cannot fine-tune them via RL. Even if we could, our users run agents inside their own AI coding assistant subscriptions -- we do not control the model.
**Do this instead:** Use APO exclusively. It optimizes the prompt text, not the model. The improved prompt works with any underlying model.

### Anti-Pattern 3: Running APO in the Generation Pipeline

**What people might do:** Run APO optimization as part of every module generation.
**Why it is wrong:** APO is expensive (multiple rollouts x multiple beam rounds x validation per rollout). A single APO cycle for one agent could take hours and cost significant API credits. Running it per-generation is wasteful and slow.
**Do this instead:** Run APO as a separate, periodic offline process (`/odoo-gen:optimize`). Collect outcomes during normal operation. Run optimization weekly/monthly when enough training data accumulates.

### Anti-Pattern 4: Cognee as Real-Time Query Service

**What people might do:** Query Cognee during every agent invocation in the generation pipeline, adding latency to each step.
**Why it is wrong:** Cognee's cognify() and search() involve LLM calls. Adding them to the hot path of generation adds latency and cost. Agents in Claude Code already have limited context windows.
**Do this instead:** Pre-compute enriched context at the start of module generation. Cache Cognee search results for the module's domain. Pass pre-computed context to agents as part of their prompt, not as real-time queries.

### Anti-Pattern 5: Abandoning Markdown KB Files

**What people might do:** Move all knowledge into Cognee's graph and stop maintaining markdown files.
**Why it is wrong:** Markdown files are human-readable, version-controlled, and serve as documentation for contributors. They are the "single source of truth" pattern. Cognee is a derived index, not a source.
**Do this instead:** Keep markdown KB files as the source. Cognee ingests them. When KB files change, re-run cognify(). This is the same pattern as "source code -> compiled binary."

## Integration Dependencies and Build Order

### Dependency Graph

```
                         ┌────────────────────┐
                         │  Training Dataset   │
                         │  (module specs +    │
                         │   golden outputs)   │
                         └────────┬───────────┘
                                  │ requires
         ┌────────────────────────┼───────────────────────┐
         ▼                        ▼                       ▼
┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐
│ Outcome Collector │  │  Rollout Runner    │  │  Grader Function │
│ (structured       │  │  (spawns agent,    │  │  (converts       │
│  validation       │  │   captures output) │  │   validation →   │
│  reporting)       │  │                    │  │   reward)        │
└────────┬─────────┘  └────────┬──────────┘  └────────┬─────────┘
         │                     │                       │
         │ requires            │ requires              │ requires
         ▼                     ▼                       ▼
┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐
│ Validation        │  │  Agent Markdown    │  │  Validation      │
│ Pipeline          │  │  Files (existing)  │  │  Result Types    │
│ (existing,        │  │                    │  │  (existing)      │
│  add reporting)   │  │                    │  │                  │
└──────────────────┘  └───────────────────┘  └──────────────────┘


┌──────────────────┐
│  Cognee Bridge    │
│  (KB ingestion +  │  ← Independent of Agent Lightning
│   search wrapper) │
└────────┬─────────┘
         │ requires
         ▼
┌──────────────────┐
│  Knowledge Base   │
│  Markdown Files   │
│  (existing)       │
└──────────────────┘
```

### Recommended Build Order

**Build Cognee integration FIRST.** It is simpler, has fewer dependencies, and delivers value immediately.

**Build Agent Lightning integration SECOND.** It requires training data (which accumulates during Cognee-enhanced operation) and has more complex integration plumbing.

| Order | Component | Rationale | Dependencies |
|-------|-----------|-----------|-------------|
| 1 | Cognee Bridge (`cognee_bridge.py`) | Standalone module. Ingests existing KB files. No changes to other components needed. | Cognee pip package, KB markdown files |
| 2 | KB Sync (`kb_sync.py`) | Detects KB file changes, triggers re-ingestion. Simple file watcher. | Cognee Bridge |
| 3 | MCP tool: `search_knowledge` | Exposes Cognee search to AI coding assistants via MCP. Immediate value. | Cognee Bridge, MCP server (existing) |
| 4 | Outcome Collector | Extends validation pipeline to report structured outcomes. Foundation for Agent Lightning. | Validation pipeline (existing) |
| 5 | Grader Function | Converts validation outcomes to 0.0-1.0 rewards. Simple pure function. | Outcome Collector |
| 6 | Training Dataset | Creates/manages sets of module specs for APO training. Requires collecting real-world specs. | None (but accumulates from real usage) |
| 7 | Rollout Runner | Spawns AI coding assistant subprocess, runs agent, captures output. Most complex new component. | Agent markdown files, validation pipeline |
| 8 | APO Trainer | Wraps Agent Lightning's APO algorithm for our agent format. | Rollout Runner, Grader, Training Dataset |
| 9 | CLI command: `/odoo-gen:optimize` | User-facing command to trigger APO training cycle. | APO Trainer |

**Build order rationale:**
- Cognee (steps 1-3) is independent and delivers value without Agent Lightning.
- Steps 4-5 (outcome collection) are small modifications to existing code, provide observability value on their own, and are prerequisites for Agent Lightning.
- Steps 6-8 (Agent Lightning core) require the most new code and benefit from data accumulated during steps 1-5.
- Step 9 is trivial CLI wiring after the core is built.

## Technology Requirements

### Agent Lightning

| Requirement | Details | Compatibility |
|------------|---------|---------------|
| Python | >=3.10 | COMPATIBLE with our 3.12 |
| `agentlightning` package | v0.3.0+ (pip install agentlightning) | OK |
| LLM API access | For APO critique/rewrite (uses LiteLLM proxy internally) | OK -- can use OpenAI or Anthropic via LiteLLM |
| GPU | NOT required for APO (CPU-only). Only needed for RL fine-tuning (which we skip). | OK -- no GPU needed |
| Training data | Module specs + expected outcomes for grading | Must create |
| Compute time | APO cycle: ~10 min per agent with 8 parallel runners | Acceptable for offline optimization |

### Cognee

| Requirement | Details | Compatibility |
|------------|---------|---------------|
| Python | 3.10-3.13 | COMPATIBLE with our 3.12 |
| `cognee` package | v0.5.3+ (pip install cognee) | OK |
| LLM API | For entity extraction during cognify() | OK -- supports Anthropic, OpenAI, Ollama |
| Graph store | Default: NetworkX (file-based, zero setup) | OK for our scale (~13 files) |
| Vector store | Default: LanceDB (file-based, zero setup) | OK -- or use existing ChromaDB |
| Disk space | Minimal for 13 KB files | OK |

### Combined Dependency Installation

```bash
# In python/ directory
uv add cognee agentlightning

# Or with extras
uv add "cognee[neo4j]"  # if wanting Neo4j graph backend later
```

## Scalability Considerations

| Concern | Current (13 KB files, 8 agents) | Future (50+ KB files, 20+ agents) |
|---------|--------------------------------|-----------------------------------|
| Cognee ingestion | ~30 seconds for 13 markdown files | ~2 minutes. Still fine. |
| Cognee search | <1 second with NetworkX/LanceDB | <1 second. NetworkX handles thousands of nodes fine. |
| APO per agent | ~10 min with 8 runners | Same per agent. More agents = run in sequence or parallelize. |
| Training data | Need 20-50 module specs minimum | More data = better optimization. No scaling issue. |
| Graph store | NetworkX (in-memory, file persistence) | Switch to Neo4j at 1000+ nodes. Currently ~200 nodes. |

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| APO optimizes prompts in ways that work for training tasks but fail on novel specs | HIGH | MEDIUM | Use diverse training dataset. Validate on held-out specs. Keep human review. Version-control agent files for rollback. |
| Cognee entity extraction misidentifies Odoo concepts (e.g., treats field names as general nouns) | MEDIUM | MEDIUM | Custom ontology hints. Test extraction quality on each KB file. Iterate cognify pipeline configuration. |
| Agent Lightning's OpenAI dependency blocks Anthropic-only users | MEDIUM | LOW | LiteLLM proxy supports Anthropic. APO critique/rewrite can use any model via LiteLLM. |
| APO rollouts are slow (each needs Docker validation) | MEDIUM | HIGH | Parallelize runners. Cache Docker images. Use pylint-only for fast feedback, Docker for final validation. |
| Cognee adds latency to agent context preparation | LOW | MEDIUM | Pre-compute at generation start. Cache per module domain. |
| Training data is insufficient (need 20+ diverse module specs) | HIGH | MEDIUM | Start collecting specs from real usage now. Create synthetic specs from OCA module manifests. |

## Sources

### Agent Lightning
- [Agent Lightning Official Docs](https://microsoft.github.io/agent-lightning/latest/) -- HIGH confidence, official documentation
- [Agent Lightning GitHub](https://github.com/microsoft/agent-lightning) -- HIGH confidence, source code + README
- [Agent Lightning Blog Post](https://www.microsoft.com/en-us/research/blog/agent-lightning-adding-reinforcement-learning-to-ai-agents-without-code-rewrites/) -- HIGH confidence, Microsoft Research
- [Agent Lightning APO Algorithm](https://microsoft.github.io/agent-lightning/latest/algorithm-zoo/apo/) -- HIGH confidence, official algorithm docs
- [Agent Lightning Training Guide](https://microsoft.github.io/agent-lightning/latest/how-to/train-first-agent/) -- HIGH confidence, official how-to
- [Agent Lightning arXiv Paper](https://arxiv.org/abs/2508.03680) -- HIGH confidence, research paper
- [Agent Lightning LiteLLM Integration](https://docs.litellm.ai/docs/projects/Agent%20Lightning) -- MEDIUM confidence, third-party integration docs
- [Agent Lightning MarkTechPost](https://www.marktechpost.com/2025/10/29/microsoft-releases-agent-lightning-a-new-ai-framework-that-enables-reinforcement-learning-rl-based-training-of-llms-for-any-ai-agent/) -- MEDIUM confidence, tech journalism
- [Agent Lightning pyproject.toml](https://github.com/microsoft/agent-lightning/blob/main/pyproject.toml) -- HIGH confidence, source file (requires-python >= 3.10)

### Cognee
- [Cognee GitHub](https://github.com/topoteretes/cognee) -- HIGH confidence, source code + README
- [Cognee Documentation](https://docs.cognee.ai/) -- HIGH confidence, official docs
- [Cognee Core Concepts](https://docs.cognee.ai/core-concepts) -- HIGH confidence, official
- [Cognee Vector Store Config](https://docs.cognee.ai/setup-configuration/vector-stores) -- HIGH confidence, official
- [Cognee LLM Providers](https://docs.cognee.ai/setup-configuration/llm-providers) -- HIGH confidence, official
- [Cognee Add Operation](https://docs.cognee.ai/core-concepts/main-operations/add) -- HIGH confidence, official
- [Cognee PyPI](https://pypi.org/project/cognee/) -- HIGH confidence, package registry
- [Cognee + FalkorDB Integration](https://docs.falkordb.com/agentic-memory/cognee.html) -- MEDIUM confidence, partner docs
- [Cognee Memory Architecture Blog](https://www.cognee.ai/blog/fundamentals/how-cognee-builds-ai-memory) -- MEDIUM confidence, vendor blog
- [Self-Hosting Cognee with Ollama](https://www.glukhov.org/post/2025/12/selfhosting-cognee-quickstart-llms-comparison/) -- LOW confidence, single blog post

---
*Architecture research for: Agent Lightning + Cognee integration with Odoo Module Automation v3.0*
*Researched: 2026-03-04*
