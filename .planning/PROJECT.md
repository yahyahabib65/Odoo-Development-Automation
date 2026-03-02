# Agentic Odoo Module Development Workflow

## What This Is

A domain-specific extension of the GSD (Get Shit Done) framework that specializes its orchestration layer for automated Odoo 17.0 module development. A developer describes a business need in natural language through their AI coding assistant (Claude Code, Gemini, Codex, OpenCode), the system semantically searches GitHub and the Odoo Community Association (OCA) for similar existing modules, then either forks and extends a match or builds from scratch — producing enterprise-grade modules through coordinated AI agents with human review at key checkpoints.

**This is NOT a standalone CLI tool.** It is a GSD extension — a set of agents, workflows, commands, templates, and knowledge base files that plug into GSD's proven orchestration layer. GSD handles context management, state persistence, hallucination prevention, phase execution, and checkpoint coordination. We build the Odoo-specific intelligence on top.

## Core Value

Compress months of repetitive Odoo module development into days by leveraging GSD's orchestration + existing open-source modules as foundations + Odoo-specialized AI agents, so developers focus on business logic and design decisions.

## Architecture

```
Layer 1: GSD Orchestration (INHERITED — not built by us)
  - Context management, hallucination prevention
  - Phase/wave execution, state persistence
  - Checkpoint-based human review
  - Agent spawning with fresh context windows
  - Git integration, atomic commits

Layer 2: Odoo Extension (BUILT BY US)
  - Odoo-specific agents (model gen, view gen, security gen, etc.)
  - Odoo-specific workflows (module creation, validation, fork-and-extend)
  - Odoo-specific commands (/odoo-gen:new, /odoo-gen:validate, etc.)
  - Odoo knowledge base (OCA standards, Odoo 17 patterns, pylint-odoo rules)
  - Jinja2 templates for module scaffolding

Layer 3: Python Utilities (BUILT BY US)
  - Jinja2 template rendering engine
  - pylint-odoo integration
  - Docker-based Odoo 17 validation
  - ChromaDB semantic search index
  - Module structure analysis tools

Layer 4: AI Coding Assistant (USER'S ENVIRONMENT)
  - Claude Code, Gemini, Codex, OpenCode, etc.
  - GSD + odoo-gen extension installed
```

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Inherited from GSD (we get these for free):**
- [x] CLI command invocation (GSD command system)
- [x] Rich terminal output (GSD + AI coding assistant UI)
- [x] Configuration file for settings (GSD config.json)
- [x] Help text and usage (GSD command descriptions)
- [x] Human review checkpoints (GSD checkpoint system)
- [x] Approve/change/reject at checkpoints (GSD pattern)
- [x] State persistence and resumability (GSD STATE.md)
- [x] Extensible knowledge base (GSD skills system)

**We build (Odoo-specific):**
- [ ] User describes module need in natural language
- [ ] System asks Odoo-specific follow-up questions (models, fields, views, inheritance)
- [ ] System parses input into structured module specification
- [ ] User reviews and approves parsed spec before generation
- [ ] System semantically searches GitHub/OCA for similar modules
- [ ] System scores, ranks, and presents matches with gap analysis
- [ ] System forks and extends matching modules when chosen
- [ ] System builds modules from scratch when no match
- [ ] System generates complete module files (models, views, security, manifest, tests)
- [ ] Generated modules install cleanly on Odoo 17.0 (CE and EE)
- [ ] Generated modules include full security (ACLs, record rules, group hierarchy)
- [ ] Generated modules include tests with real assertions
- [ ] Generated modules pass OCA quality standards (pylint-odoo, i18n)
- [ ] Docker-based Odoo 17 validates installation and test execution
- [ ] System auto-fixes pylint/Docker failures before escalating to human
- [ ] System supports Odoo 17.0 (primary) and 18.0, CE and EE editions

### Out of Scope

- Web UI / browser interface — GSD extension runs inside AI coding assistants
- Mobile app — not applicable
- Standalone CLI tool — we inherit GSD's interface, not build our own
- Building our own orchestration layer — GSD provides this
- Selling as a product — internal dev team tool
- Real-time collaborative editing — single-user workflow
- Module deployment to production — system generates, human deploys

## Context

- The team has some Odoo development experience but wants to eliminate months of boilerplate work
- Odoo modules span dozens of interconnected files with XML boilerplate, ORM quirks, and cross-module complexity
- The OCA ecosystem has thousands of existing modules that often partially solve what teams need
- GSD (Get Shit Done) is a proven orchestration framework that solves context rot, manages state, and coordinates AI agents — we extend it rather than reinventing it
- Distribution: users clone into `~/.claude/` (same pattern as GSD itself)
- GSD is AI-assistant agnostic — works with Claude Code, Gemini, Codex, OpenCode
- Volume expectation: 1-2 modules per week at a steady quality-focused pace

## Constraints

- **Dependency**: Requires GSD installed (`~/.claude/get-shit-done/`)
- **Target Version**: Odoo 17.0 primary, 18.0 secondary
- **Quality Standard**: OCA-grade — pylint-odoo clean, proper i18n, full security, tests
- **Interface**: GSD commands via AI coding assistant (not standalone CLI)
- **Distribution**: Clone into `~/.claude/odoo-gen/` (like GSD)
- **Edition Support**: Both Community and Enterprise
- **Test Infrastructure**: Docker-based Odoo instances for validation
- **Build Strategy**: Search-first — check for existing modules before building from scratch
- **Human Oversight**: GSD checkpoint-based review at key generation stages
- **API Budget**: Unconstrained — prioritize quality
- **Python Utilities**: Python 3.12 (Odoo 17 constraint: 3.10-3.12 only, 3.13+ breaks validation)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GSD extension (not standalone CLI) | GSD provides orchestration, context management, hallucination prevention — no need to reinvent | Decided |
| Depend on GSD (not fork) | Benefit from GSD updates automatically, avoid divergence | Decided |
| Clone-based install (~/.claude/) | Same pattern as GSD, works with any AI coding assistant | Decided |
| Odoo 17.0 primary target | Stable, widely adopted, strong OCA support | Decided |
| Fork-and-extend strategy | Leverage existing OCA/GitHub modules as foundation | Decided |
| Semantic search (ChromaDB + sentence-transformers) | Intent-based matching, not just keywords | Decided |
| Python 3.12 for utilities | Odoo 17 supports 3.10-3.12 only; 3.13+ breaks validation | Decided |
| Checkpoint-based human review | GSD provides the mechanism; we wire Odoo-specific checkpoints | Decided |
| OCA quality as the bar | pylint-odoo, i18n, full security, tests | Decided |
| Docker for validation | Only way to truly verify module installs and tests pass | Decided |
| UI UX Pro Max Skill pattern | Reasoning engine + hierarchical system + rule library as template for skill architecture | Decided |

## Prior Art

| Project | Relevance | How we use it |
|---------|-----------|---------------|
| **GSD (Get Shit Done)** | INHERIT | Full orchestration layer — context, state, phases, agents, checkpoints |
| **erp_claude** (Baptiste-banani) | ADOPT KNOWLEDGE | Odoo 17 model/view skills → foundation for our knowledge base |
| **UI UX Pro Max Skill** | ADOPT PATTERN | Reasoning engine, hierarchical system, rule library → template for our skill architecture |
| **Ralph** (snarktank) | REFERENCE | Fresh context loop + accumulated knowledge pattern → confirms GSD approach |
| **Cognee** (topoteretes) | REFERENCE | Knowledge graph pipeline (cognify/memify/search) → informs knowledge base design |
| **LangExtract** (Google) | REFERENCE | Source-grounded extraction → informs spec parsing approach |
| **Agent Lightning** (Microsoft) | FUTURE | RL-based agent optimization → v2+ when we have agents to optimize |
| **Gemini-Odoo-Module-Generator** | COMPETITOR | Single-agent Gemini CLI → baseline we must exceed |
| **Ruflo** (ruvnet) | SKIP | Over-engineered for our needs (60+ agents, Byzantine consensus) |
| **LobeHub** | SKIP | Web chat platform, different product category |

---
*Last updated: 2026-03-01 — architecture pivoted to GSD extension*
