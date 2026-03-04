# Retrospective

## Milestone: v1.0 — Odoo Module Automation MVP

**Shipped:** 2026-03-03
**Phases:** 9 | **Plans:** 26 | **Commits:** 139 | **Timeline:** 3 days

### What Was Built

1. GSD extension architecture with 12 commands, 8 specialized AI agents, install.sh-based setup
2. Comprehensive Odoo 17.0 knowledge base (13 domain files, 80+ WRONG/CORRECT example pairs)
3. Validation pipeline: pylint-odoo integration + Docker-based Odoo validation + auto-fix loops
4. Specification pipeline: natural language to structured JSON spec with tiered follow-up questions and approval gate
5. Jinja2 rendering engine: 24 templates producing models, views, security, wizards, tests, i18n
6. Semantic search: ChromaDB vector index + OCA repo crawl + gap analysis + fork-and-extend workflow
7. Edition/version support: Enterprise module registry, version-aware templates (17.0/18.0/shared), FileSystemLoader fallback

### What Worked

- **GSD extension model**: Inheriting orchestration (~19% of requirements) let us focus entirely on Odoo domain logic
- **TDD workflow**: RED/GREEN approach prevented regressions across 243 tests — zero test failures at milestone end
- **Wave-based execution**: Parallel plan execution within phases kept velocity high (avg 4.4 min/plan)
- **Knowledge base architecture**: WRONG/CORRECT example pairs in knowledge files effectively guided AI agents
- **Jinja2 + AI hybrid**: Deterministic template rendering for structure + AI agents for business logic was the right split
- **Phase sequencing**: Building validation (Phase 3) before generation (Phase 5) meant we could verify output quality from the start

### What Was Inefficient

- **Context exhaustion**: Multiple sessions hit context limits during complex workflows (milestone audit, complete-milestone), requiring state serialization and resumption
- **Frontmatter inconsistency**: SUMMARY.md files had varying frontmatter formats across phases, making automated extraction difficult
- **Docker validation untested**: All Docker integration tests mock subprocess — never validated against a live Odoo 17.0 Docker instance
- **gh CLI not authenticated**: Search features require `gh auth login` which was never set up during development
- **Orphaned templates**: 3 template files (view_search.xml.j2, view_tree.xml.j2 x2) were created but never wired into the renderer

### Patterns Established

- **Agent + Knowledge pattern**: Each agent gets @include references to relevant knowledge files, preventing hallucinations
- **Immutable data flow**: Frozen dataclasses for validation types, tuple fields for hashability
- **CLI wrapping venv**: bin/odoo-gen-utils wrapper script resolves Python venv portably
- **Spec-first generation**: JSON spec is source of truth; all downstream tools consume it
- **Version-aware templates**: FileSystemLoader([version_dir, shared_dir]) for clean version separation

### Key Lessons

1. **Fix integration bugs early**: The extract-i18n argument mismatch (2 args passed, 1 accepted) persisted through multiple phases because Step 3.5 is non-blocking. Integration testing across workflow boundaries catches these.
2. **Frontmatter should be standardized**: Agreeing on SUMMARY.md schema early would have made milestone extraction trivial.
3. **GSD tooling accelerates**: `gsd-tools` CLI for commits, state updates, and phase management removed significant boilerplate from every plan execution.
4. **3-day build is achievable**: 9 phases, 68 requirements, 4,150 LOC in 3 days with AI-assisted development at quality profile (Opus for all agents).

### Cost Observations

- Model mix: 100% Opus (quality profile selected for entire milestone)
- Sessions: ~8 context windows consumed (several exhaustions required /clear + resume)
- Notable: Average plan execution was 4.4 minutes — the bottleneck was planning and review, not execution

---

## Milestone: v1.2 — Template Quality

**Shipped:** 2026-03-04
**Phases:** 3 (12-14) | **Plans:** 4 | **Commits:** 29 | **Timeline:** 2 days

### What Was Built

1. Fixed 4 template correctness bugs: mail.thread auto-inheritance, conditional api import, clean manifests, clean test imports
2. AST-based auto-fix for missing mail.thread inheritance and unused imports with immutable read-transform-write pattern
3. Golden path E2E regression test: render realistic module → Docker install → Docker test execution
4. Docker fix dispatch wiring: run_docker_fix_loop connecting identify_docker_fix → fix functions → CLI validate
5. Knowledge base updated with mail.thread inheritance rules and triple dependency documentation

### What Worked

- **Milestone audit process**: The v1.2 audit identified exactly the right tech debt (3 orphaned exports), which Phase 14 resolved cleanly
- **Phase 14 surgical fix**: Adding a targeted phase for tech debt closure was efficient — 3 minutes execution, 6 tests, zero regressions
- **Golden path E2E test**: Module-scoped fixture renders once and all 3 staged tests share the result — catches template regressions without redundant rendering
- **AST-based import analysis**: More reliable than regex for detecting unused imports in complex Python files
- **TDD continued to work**: 309 tests at milestone end, zero failures, all phases TDD-verified

### What Was Inefficient

- **Verifier agent cwd drift**: Phase 14 verifier agent started in python/ subdirectory instead of project root, couldn't find .planning/ directory. Required manual verification and VERIFICATION.md creation. Same issue observed in prior sessions.
- **Context exhaustion during Phase 14**: Hit 90% context on first execution attempt, then 93% after execution completed. Required session restart and couldn't finish verification in the same context window.
- **TDEBT requirements not in REQUIREMENTS.md**: Phase 14 was added after REQUIREMENTS.md was finalized, so TDEBT-01/TDEBT-02 only exist in ROADMAP.md. Minor but breaks the 3-source cross-reference pattern.

### Patterns Established

- **Orphan detection in milestone audit**: Integration checker now identifies functions with test callers but no runtime callers
- **Dispatch dict pattern**: run_docker_fix_loop uses `{"missing_mail_thread": fix_missing_mail_thread}` for extensible fix dispatch
- **Staged E2E test pattern**: render → Docker install → Docker test execution with shared module-scoped fixture
- **Keyword-based pattern detection**: identify_docker_fix uses _DOCKER_PATTERN_KEYWORDS for error text classification

### Key Lessons

1. **Verifier agents need explicit cwd**: When spawning verifier agents, always specify the project root path — don't rely on inherited working directory
2. **Post-audit phases need requirements tracking**: When adding phases after REQUIREMENTS.md is finalized, add their requirements to the file (not just ROADMAP.md)
3. **Audit → fix → re-audit is the right loop**: The tech_debt audit status correctly flagged issues that Phase 14 resolved, and the re-audit confirmed clean passage
4. **Context management is the bottleneck**: Two context exhaustions in a single phase execution suggests the workflow needs more aggressive context pruning for late-milestone work

### Cost Observations

- Model mix: 100% Opus (quality profile), Sonnet for plan-checker and verifier
- Sessions: 3 context windows consumed (context exhaustion during Phase 14 execution)
- Notable: Phase 14 executed in 3 minutes — the tech debt fix was surgical

---

## Cross-Milestone Trends

| Metric | v1.0 | v1.2 |
|--------|------|------|
| Phases | 9 | 3 |
| Plans | 26 | 4 |
| Requirements | 68 | 12 |
| LOC (Python) | 4,150 | 10,999 |
| Tests | 243 | 309 |
| Commits | 139 | 29 |
| Timeline (days) | 3 | 2 |
| Avg plan duration | 4.4 min | 4 min |

---
*Last updated: 2026-03-04*
