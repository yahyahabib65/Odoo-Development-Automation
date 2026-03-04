# Stack Research: Agent Lightning + Cognee Integration

**Domain:** RL-based agent optimization + knowledge graph pipeline for Odoo module automation
**Researched:** 2026-03-04
**Confidence:** MEDIUM (both libraries are actively evolving; Agent Lightning is pre-1.0, Cognee is beta)

> **SCOPE:** This research covers ONLY the new stack additions for v3.0. The existing stack (Python 3.12, Jinja2, Click, pylint-odoo, ChromaDB, Docker, uv) is validated and unchanged. See the original STACK.md header for prior research.

---

## New Stack Additions

### Agent Lightning (RL-Based Agent Optimization)

| Attribute | Value | Confidence |
|-----------|-------|------------|
| **Package name** | `agentlightning` | HIGH (verified PyPI) |
| **Latest stable** | 0.3.0 (Dec 24, 2024) | HIGH (verified PyPI + GitHub releases) |
| **Latest dev** | 0.3.1+ (main branch) | MEDIUM (pyproject.toml on GitHub shows 0.3.1) |
| **Python requirement** | >=3.10 | HIGH (verified pyproject.toml) |
| **Python 3.12 compatible** | YES | HIGH |
| **License** | MIT | HIGH |
| **Wheel size** | 612 KB | HIGH (verified PyPI) |
| **Source size** | 1.3 MB | HIGH (verified PyPI) |
| **GPU required** | NO (APO mode is CPU-only, uses LLM API calls) | HIGH (verified: APO tests run on GitHub Actions Ubuntu runners) |
| **PyTorch required** | NO (optional, only for VERL/SFT modes) | HIGH (verified: PyTorch is in optional extras, not core deps) |

#### Core Dependencies (what it pulls in)

| Dependency | Version | Size Impact | Overlap with Our Stack |
|------------|---------|-------------|----------------------|
| litellm[proxy] | >=1.74 | ~50MB (moderate) | NEW - also used by Cognee (>=1.76) - compatible |
| pydantic | >=2.11 | ~5MB | COMPATIBLE - we already use pydantic |
| openai | (unversioned) | ~10MB | NEW - required for APO LLM calls |
| fastapi | (unversioned) | ~5MB | NEW - used for internal dashboard/API |
| uvicorn | (unversioned) | ~2MB | NEW - ASGI server |
| gunicorn | (unversioned) | ~1MB | NEW |
| flask | (unversioned) | ~3MB | NEW - used for legacy endpoints |
| aiohttp | (unversioned) | ~5MB | NEW |
| rich | (unversioned) | ~3MB | COMPATIBLE - we already use rich |
| graphviz | (unversioned) | ~1MB | NEW |
| psutil | (unversioned) | ~1MB | NEW |
| gpustat | (unversioned) | ~1MB | NEW (harmless on CPU-only) |
| agentops | >=0.4.13 | ~5MB | NEW - agent observability |
| opentelemetry-api/sdk/exporter | >=1.35 | ~15MB | NEW - telemetry |
| portpicker | (unversioned) | ~1MB | NEW |
| aiologic | (unversioned) | ~1MB | NEW |

**Total estimated new dependency footprint (APO mode):** ~100-120MB
**With PyTorch (VERL mode):** +2GB (not recommended for our use case)

#### What We Actually Need: APO Only

For our use case (optimizing agent prompts based on validation outcomes), we ONLY need APO:

```bash
pip install agentlightning[apo]
```

The `[apo]` extra adds only `poml` (Prompt Optimization Markup Language), a lightweight package. The heavy extras (verl, torch-stable, torch-gpu-stable) are NOT needed.

#### How APO Works (Relevant to Our Agents)

1. **Emit spans**: Wrap agent calls with `agl.emit_xxx()` helpers or use tracer
2. **Define reward**: Score agent output (e.g., 1.0 if module passes pylint + Docker, 0.0 if not)
3. **APO optimizes**: Uses LLM-generated "textual gradients" to iteratively improve prompt templates
4. **Output**: Optimized `PromptTemplate` objects (NOT fine-tuned models)

APO uses two LLM calls per optimization step:
- **Gradient model** (default: gpt-4-mini): Generates critique of current prompt
- **Apply-edit model** (default: gpt-4-mini): Rewrites prompt based on critique

Configuration parameters:
- `beam_width`: 4 (top prompts retained per round)
- `branch_factor`: 4 (new candidates per parent)
- `beam_rounds`: 3 (optimization iterations)
- Training a single agent takes ~10 minutes with 8 parallel runners

---

### Cognee (Knowledge Graph Pipeline)

| Attribute | Value | Confidence |
|-----------|-------|------------|
| **Package name** | `cognee` | HIGH (verified PyPI) |
| **Latest stable** | 0.5.3 (Feb 27, 2026) | HIGH (verified PyPI) |
| **Python requirement** | >=3.10, <3.14 | HIGH (verified pyproject.toml) |
| **Python 3.12 compatible** | YES | HIGH |
| **License** | Apache-2.0 | HIGH |
| **Wheel size** | 1.7 MB | HIGH (verified PyPI) |
| **Source size** | 14.6 MB | HIGH (verified PyPI) |
| **Development status** | Beta (4 - Beta) | HIGH |
| **LLM API key required** | YES (default: OpenAI; configurable to Anthropic, Ollama, etc.) | HIGH |

#### Core Dependencies (37 packages)

| Dependency | Version | Size Impact | Overlap with Our Stack |
|------------|---------|-------------|----------------------|
| openai | >=1.80.1 | ~10MB | SHARED with Agent Lightning |
| litellm | >=1.76.0 | ~50MB | SHARED with Agent Lightning (>=1.74) - compatible |
| pydantic | >=2.10.5 | ~5MB | COMPATIBLE - we already use pydantic |
| pydantic-settings | (unversioned) | ~1MB | COMPATIBLE |
| numpy | >=1.26.4, <=4.0.0 | ~30MB | NEW |
| sqlalchemy | >=2.0.39, <3.0.0 | ~10MB | NEW |
| aiosqlite | (unversioned) | ~1MB | NEW |
| tiktoken | (unversioned) | ~10MB | NEW |
| instructor | >=1.9.1, <2.0.0 | ~5MB | NEW - structured LLM output |
| fastembed | <=0.6.0 | ~20MB | NEW - local ONNX embeddings (like ChromaDB's built-in) |
| onnxruntime | <=1.22.1 | ~50MB | NEW - needed by fastembed |
| lancedb | >=0.24.0, <1.0.0 | ~30MB | NEW - default vector store |
| kuzu | ==0.11.3 | ~20MB | NEW - default graph database |
| jinja2 | (unversioned) | ~1MB | COMPATIBLE - we already use jinja2 |
| networkx | (unversioned) | ~5MB | NEW - graph algorithms |
| fastapi | (unversioned) | ~5MB | SHARED with Agent Lightning |
| uvicorn | (unversioned) | ~2MB | SHARED with Agent Lightning |
| gunicorn | (unversioned) | ~1MB | SHARED with Agent Lightning |
| aiohttp | (unversioned) | ~5MB | SHARED with Agent Lightning |
| alembic | (unversioned) | ~5MB | NEW - DB migrations |
| rdflib | (unversioned) | ~5MB | NEW - RDF/knowledge graph |
| pypdf | (unversioned) | ~3MB | NEW - PDF parsing |
| structlog | (unversioned) | ~1MB | NEW - structured logging |
| Other (15+ small pkgs) | various | ~20MB | NEW |

**Total estimated new dependency footprint (core only):** ~250-300MB
**With ChromaDB extra:** +ChromaDB (already installed) + pypika (~1MB)

#### Storage Backends

**Vector Store (default: LanceDB - file-based)**
| Backend | Type | Setup | Our Use |
|---------|------|-------|---------|
| LanceDB | File-based (default) | Zero config | Use this - no infrastructure needed |
| ChromaDB | HTTP server | `cognee[chromadb]` extra | CAN point to our existing ChromaDB instance |
| PGVector | PostgreSQL | Needs postgres | Overkill |
| Qdrant | Server | Needs Qdrant | Overkill |
| Redis | Server | Needs Redis | Overkill |
| FalkorDB | Server | Needs FalkorDB | Overkill |

**Graph Store (default: Kuzu - file-based)**
| Backend | Type | Setup | Our Use |
|---------|------|-------|---------|
| Kuzu | File-based (default) | Zero config, included in core deps | Use this - embedded, no infrastructure |
| Neo4j | Server | Needs Neo4j | Production option for later |
| Neptune | AWS cloud | Needs AWS | Overkill |
| Memgraph | Server | Needs Memgraph | Overkill |
| NetworkX | In-memory | Zero config | Too limited for persistence |

**Embedding Provider (default: OpenAI)**
| Backend | Type | API Key? | Our Use |
|---------|------|----------|---------|
| OpenAI | API | YES | Default but costs money |
| **Fastembed** | **Local ONNX** | **NO** | **Use this - CPU-friendly, no API key, included by default** |
| Ollama | Local server | NO | Alternative local option |

**RECOMMENDATION:** Use defaults (LanceDB + Kuzu + Fastembed) for zero-infrastructure local operation. This means NO external services needed beyond the LLM API for graph generation.

#### ChromaDB Overlap Analysis

**Critical finding:** Cognee and our existing stack both touch vector search, but they serve DIFFERENT purposes:

| Concern | Our ChromaDB | Cognee's Vector Store |
|---------|-------------|----------------------|
| **Purpose** | Semantic search for OCA/GitHub module matching | Knowledge graph embeddings for Odoo documentation |
| **Data** | Module manifests, READMEs, descriptions | Odoo patterns, OCA standards, API docs, KB articles |
| **Query pattern** | "Find modules similar to X" | "What are the relationships between sale.order and account.move?" |
| **Overlap** | NONE - different data, different queries | NONE |

**Decision:** Keep both. ChromaDB for module search, Cognee's LanceDB for knowledge graph embeddings. They store different data and serve different retrieval needs. No need to consolidate.

**Optional:** If desired later, Cognee CAN be configured to use our existing ChromaDB as its vector backend via `VECTOR_DB_PROVIDER=chromadb` and `VECTOR_DB_URL=http://localhost:3002`. But LanceDB default is simpler (file-based, no server).

---

## Compatibility Analysis

### Python 3.12 Compatibility Matrix

| Package | Python 3.12 Support | Verified |
|---------|-------------------|----------|
| agentlightning | YES (>=3.10) | PyPI classifiers |
| cognee | YES (>=3.10, <3.14) | PyPI + pyproject.toml |
| litellm | YES (>=3.9, <4.0) | PyPI |
| kuzu | YES | PyPI (pinned ==0.11.3) |
| lancedb | YES | PyPI |
| fastembed | YES (Python <3.13) | PyPI + community reports |
| onnxruntime | YES | PyPI |

**Verdict:** All packages support Python 3.12. No blockers.

### Shared Dependency Compatibility

Both Agent Lightning and Cognee depend on several shared packages. Here is the conflict analysis:

| Dependency | Agent Lightning | Cognee | Compatible? |
|------------|----------------|--------|-------------|
| litellm | >=1.74 | >=1.76 | YES - Cognee's floor is higher, resolver picks >=1.76 |
| pydantic | >=2.11 | >=2.10.5 | YES - Agent Lightning's floor is higher, resolver picks >=2.11 |
| openai | unversioned (core-stable: >=2.0) | >=1.80.1 | YES - both want recent openai |
| fastapi | unversioned | unversioned | YES - no conflict |
| uvicorn | unversioned | unversioned | YES - no conflict |
| aiohttp | unversioned | unversioned | YES - no conflict |

**Verdict:** No dependency conflicts detected. Both can coexist in the same venv.

### Can Both Coexist in Same Venv?

**YES.** Analysis:
1. Shared deps (litellm, pydantic, openai, fastapi, uvicorn, aiohttp) have compatible version ranges
2. No mutually exclusive version pins
3. Both target Python >=3.10, our env is 3.12
4. Both use pydantic v2 (no v1/v2 split)
5. Agent Lightning's litellm[proxy]>=1.74 satisfies with Cognee's litellm>=1.76 (resolver picks >=1.76)

**Recommendation:** Single venv. No isolation needed. Use `uv add` to install both.

---

## Recommended Installation

```bash
# Agent Lightning - APO mode only (no PyTorch, no GPU)
uv add agentlightning[apo]

# Cognee - core with ChromaDB support as optional bridge
uv add cognee

# If you want Cognee to use our existing ChromaDB instance (optional)
# uv add "cognee[chromadb]"

# Environment variables needed
# For Cognee knowledge graph generation:
export LLM_API_KEY="your-openai-or-anthropic-key"
export LLM_PROVIDER="openai"  # or "anthropic"
export LLM_MODEL="gpt-4.1-mini"  # or "claude-sonnet-4-20250514"

# For local embeddings (no API key needed):
export EMBEDDING_PROVIDER="fastembed"
export EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
export EMBEDDING_DIMENSIONS="384"

# For Agent Lightning APO:
export OPENAI_API_KEY="your-openai-key"  # APO uses OpenAI for prompt optimization
```

### Updated pyproject.toml Additions

```toml
[project]
dependencies = [
    # ... existing deps ...
    "agentlightning[apo]>=0.3.0",
    "cognee>=0.5.3",
]

[project.optional-dependencies]
# Full RL training (requires GPU + PyTorch)
rl-full = [
    "agentlightning[verl]>=0.3.0",
    "torch>=2.8.0",
]
# Cognee with ChromaDB bridge
cognee-chromadb = [
    "cognee[chromadb]>=0.5.3",
]
```

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `agentlightning[verl]` | Pulls in PyTorch (~2GB), vLLM, CUDA deps. Only needed for model fine-tuning, which is overkill for prompt optimization. | `agentlightning[apo]` - prompt optimization via LLM API calls |
| `agentlightning[torch-stable]` | Same as above - massive dependency for GPU training | `agentlightning[apo]` |
| `cognee[neo4j]` | Requires running a Neo4j server. Kuzu (default) is embedded and file-based. | Default Kuzu graph store |
| `cognee[postgres]` | Requires PostgreSQL with pgvector. LanceDB (default) is file-based. | Default LanceDB vector store |
| `sentence-transformers` | Was in original STACK.md but ChromaDB uses built-in ONNX embedding. Cognee uses fastembed (also ONNX). No need for sentence-transformers + PyTorch. | ChromaDB built-in embeddings + Cognee fastembed |
| `langchain` / `langgraph` | Neither Agent Lightning nor Cognee require these for our use case. Adds massive dependency trees. | Direct API integration |
| `transformers` (huggingface) | Only needed for Cognee's huggingface/ollama/codegraph extras. Not needed for core knowledge graphs. | Fastembed for embeddings |
| `torch` / `pytorch` | Not needed. APO is CPU-only (LLM API). Cognee uses fastembed (ONNX). ChromaDB uses ONNX. Zero PyTorch. | ONNX-based alternatives |

---

## Dependency Size Impact Summary

| Component | Estimated Size | Notes |
|-----------|---------------|-------|
| agentlightning (core) | 612 KB | Wheel only |
| agentlightning deps (new) | ~100 MB | litellm, opentelemetry, agentops, etc. |
| cognee (core) | 1.7 MB | Wheel only |
| cognee deps (new) | ~250 MB | numpy, sqlalchemy, kuzu, lancedb, fastembed, onnxruntime, etc. |
| Shared deps (deduplicated) | -70 MB | litellm, pydantic, openai, fastapi, aiohttp already counted once |
| **Total new footprint** | **~280-350 MB** | Without PyTorch (compare: PyTorch alone is 2GB) |

This is a SIGNIFICANT increase from the current lean stack but justified because:
1. Cognee replaces static markdown KB with a queryable knowledge graph (much richer retrieval)
2. Agent Lightning enables agents to improve over time (measurable quality gains)
3. We avoided PyTorch entirely (saved 2GB) by using APO + fastembed + ONNX
4. The alternative (building custom KG + RL) would be far more code and maintenance

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Cognee (knowledge graphs) | Custom NetworkX + ChromaDB | Cognee provides the full pipeline (ingest, cognify, memify, search) out of the box. Building custom would take weeks and produce worse results. |
| Cognee (knowledge graphs) | LlamaIndex Knowledge Graphs | LlamaIndex pulls in more dependencies, is less focused on knowledge graphs, and doesn't provide the graph+vector hybrid search Cognee offers. |
| Cognee (knowledge graphs) | GraphRAG (Microsoft) | GraphRAG is research code, not a maintained library. Cognee is actively developed with proper packaging. |
| Agent Lightning APO | DSPy | DSPy does prompt optimization but is more complex, less framework-agnostic, and doesn't integrate as cleanly with arbitrary agents. |
| Agent Lightning APO | TextGrad | TextGrad is research code. Agent Lightning is maintained by Microsoft with proper packaging and docs. |
| Agent Lightning APO | Custom prompt tuning | Manual A/B testing of prompts doesn't scale. APO automates this with measurable reward signals. |
| Kuzu (graph DB) | Neo4j | Neo4j requires running a server. Kuzu is embedded (file-based), zero config, and sufficient for our scale. |
| LanceDB (vector DB for Cognee) | Reuse our ChromaDB | LanceDB is Cognee's default, requires zero setup. Using ChromaDB would require running it as an HTTP server. Different data anyway. |
| Fastembed (embeddings for Cognee) | OpenAI text-embedding-3-large | Fastembed is local, free, no API key. OpenAI embeddings cost money per call. For KB indexing, local is better. |

---

## Integration Architecture

```
Existing Stack (unchanged)          New Stack (v3.0)
================================    ================================
ChromaDB                            Cognee
  - Module search embeddings           - Knowledge graph (Kuzu)
  - OCA/GitHub module matching         - KB embeddings (LanceDB)
  - ONNX built-in embeddings           - Fastembed (ONNX)
                                       - Replaces static markdown KB

8 Specialized Agents                Agent Lightning (APO)
  - model-gen, view-gen, etc.          - Wraps agent invocations
  - Static prompt templates            - Collects reward signals
  - No learning/improvement            - Optimizes prompts over time
                                       - Stores optimized templates
```

### Data Flow

```
1. KNOWLEDGE GRAPH (Cognee):
   Odoo docs + OCA standards + KB files
     → cognee.add(documents)
     → cognee.cognify()  [extracts entities, relationships]
     → Knowledge graph (Kuzu) + embeddings (LanceDB)
     → cognee.search("how does sale.order relate to account.move?")
     → Structured, connected results (not just similarity)

2. AGENT OPTIMIZATION (Agent Lightning):
   Agent executes (e.g., model-gen generates models.py)
     → agl.emit_xxx() captures prompt + output
     → Validator scores result (pylint pass=0.5, Docker pass=1.0, fail=0.0)
     → APO analyzes scored trajectories
     → Generates improved prompt template
     → Next execution uses optimized prompt
```

---

## Sources

### Agent Lightning
- [GitHub Repository](https://github.com/microsoft/agent-lightning) (HIGH confidence)
- [Official Documentation](https://microsoft.github.io/agent-lightning/latest/) (HIGH confidence)
- [PyPI Package](https://pypi.org/project/agentlightning/) (HIGH confidence)
- [Installation Guide](https://microsoft.github.io/agent-lightning/latest/tutorials/installation/) (HIGH confidence)
- [APO Algorithm](https://microsoft.github.io/agent-lightning/latest/algorithm-zoo/apo/) (HIGH confidence)
- [Training Tutorial](https://microsoft.github.io/agent-lightning/latest/how-to/train-first-agent/) (HIGH confidence)
- [Microsoft Research Blog](https://www.microsoft.com/en-us/research/blog/agent-lightning-adding-reinforcement-learning-to-ai-agents-without-code-rewrites/) (HIGH confidence)
- [arXiv Paper](https://arxiv.org/abs/2508.03680) (HIGH confidence)
- [GitHub Releases](https://github.com/microsoft/agent-lightning/releases) (HIGH confidence)

### Cognee
- [GitHub Repository](https://github.com/topoteretes/cognee) (HIGH confidence)
- [PyPI Package](https://pypi.org/project/cognee/) (HIGH confidence)
- [Official Documentation - Vector Stores](https://docs.cognee.ai/setup-configuration/vector-stores) (HIGH confidence)
- [Official Documentation - Graph Stores](https://docs.cognee.ai/setup-configuration/graph-stores) (HIGH confidence)
- [Official Documentation - Embedding Providers](https://docs.cognee.ai/setup-configuration/embedding-providers) (HIGH confidence)
- [Cognee + LanceDB Case Study](https://lancedb.com/blog/case-study-cognee/) (MEDIUM confidence)
- [Cognee + Kuzu Blog Post](https://blog.kuzudb.com/post/cognee-kuzu-relational-data-to-knowledge-graph/) (MEDIUM confidence)

### Shared Dependencies
- [LiteLLM PyPI](https://pypi.org/project/litellm/) (HIGH confidence)
- [LiteLLM + Agent Lightning Docs](https://docs.litellm.ai/docs/projects/Agent%20Lightning) (MEDIUM confidence)

---
*Stack research for: Agent Lightning + Cognee Integration (v3.0)*
*Researched: 2026-03-04*
