# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Compress months of repetitive Odoo module development into days by extending GSD's orchestration with Odoo-specialized agents, knowledge, and validation.
**Architecture:** GSD extension (not standalone CLI)
**Current focus:** Phase 4 - Input & Specification (Phases 2 and 3 complete)

## Current Position

Phase: 4 of 9 (Input & Specification) -- Phases 2 and 3 COMPLETE
Plan: Phase 2: 3 of 3 complete | Phase 3: 3 of 3 complete
Status: Completed 03-03 -- Error diagnosis, CLI integration, agent/command updates
Last activity: 2026-03-02 -- Completed 03-03 (Error patterns + validate CLI + agent updates)

Progress: [█████░░░░░] 45%

## Performance Metrics

**Velocity:**
- Total plans completed: 10
- Average duration: 4.5 min
- Total execution time: 0.7 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | 13 min | 3.25 min |
| 02 | 3 | 18 min | 6.0 min |
| 03 | 3 | 17 min | 5.7 min |

**Recent Trend:**
- Last 5 plans: 03-02 (6 min), 02-02 (6 min), 02-01 (7 min), 02-03 (5 min), 03-03 (6 min)
- Trend: Consistent

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Architecture]: odoo-gen is a GSD extension, not a standalone CLI tool
- [Architecture]: Depend on GSD (not fork) — benefit from upstream updates
- [Architecture]: Clone-based install into ~/.claude/odoo-gen/
- [Architecture]: UI UX Pro Max Skill pattern for reasoning engine + rule library
- [Roadmap]: Phase 1 is GSD extension setup + Odoo foundation (not CLI build)
- [Roadmap]: Knowledge Base moved to Phase 2 (before validation, so agents have expertise)
- [Roadmap]: Phases 2 and 3 can run in parallel after Phase 1
- [Roadmap]: Old standalone CLI plans deleted — wrong architecture
- [Commands]: Forward reference to scaffold.md in new.md (resolved at invocation time)
- [Commands]: help.md uses inline command table (self-contained, no external workflow)
- [Templates]: Combined form+tree+search views into single per-model view file for render_module
- [Templates]: Single menu.xml for all models (cleaner OCA structure)
- [Package]: Hatchling build backend for pyproject.toml-native packaging
- [Agents]: Symlinks for agent registration (ln -sf) instead of copy -- keeps agents in extension dir
- [Agents]: odoo-scaffold agent includes comprehensive Odoo 17.0 specifics to prevent LLM hallucinations
- [Security]: defaults.json api_keys uses $ENV_VAR references resolved at runtime -- never stores secrets
- [Infra]: Wrapper script at bin/odoo-gen-utils resolves venv path portably across platforms
- [Workflows]: Scaffold workflow defines 4 phases: input parsing, spec confirmation, generation (odoo-gen-utils), post-generation
- [Workflows]: Help workflow uses inline table with Active/Planned status labels
- [Templates]: Chatter section in form views conditional on 'mail' in depends
- [Validation]: Tuples (not lists) for frozen dataclass fields -- immutability compliance
- [Validation]: noqa F401 on __init__.py re-exports to prevent ruff from stripping public API
- [Validation]: Recursive tuple-to-list conversion needed for JSON serialization of dataclasses
- [Knowledge]: Each knowledge file follows consistent Rule + WRONG + CORRECT + Why format with Changed in 17.0 section
- [Knowledge]: TransactionCase as primary test base class (SavepointCase deprecated in 17.0)
- [Knowledge]: tree (not list) in view_mode for Odoo 17.0
- [Knowledge]: All three inheritance patterns documented: _inherit, _inherits, _name+_inherit
- [Knowledge]: Jinja2 template syntax for email templates in data.md (Odoo 17.0 default)
- [Knowledge]: pylint-odoo rules in compact table format (Rule | Trigger | Fix) to save context budget
- [Knowledge]: models.md trimmed from 646 to 482 lines by consolidating examples while preserving all rules
- [Validation]: Regex alternation pattern for module-not-found parsing (quoted vs unquoted)
- [Validation]: Always-teardown guarantee via finally blocks in Docker runner
- [Validation]: Graceful degradation when Docker unavailable (return empty/failure results, no exceptions)
- [Knowledge]: Custom rules extend defaults, never override shipped rules
- [Knowledge]: Format-only validation for custom rules (headings, code blocks, line count)
- [Knowledge]: Knowledge base installed via symlink (same pattern as agents)
- [Knowledge]: validate-kb defaults to custom/ only; --all flag validates shipped + custom
- [Knowledge]: All 6 agents wired to KB via @include references to ~/.claude/odoo-gen/knowledge/
- [Validation]: Module-level caching for error patterns (avoid repeated JSON file I/O)
- [Validation]: IGNORECASE | MULTILINE regex flags for robust log matching
- [Validation]: Unrecognized errors fall back to raw traceback (not silent failure)
- [Validation]: validate CLI exit code 1 for any violations/failures, 0 only when fully clean

### Pending Todos

None yet.

### Blockers/Concerns

- gh CLI not authenticated -- needed for Phase 8 (GitHub API search). Not blocking until then.
- sentence-transformers pulls PyTorch (~2GB) -- plan CPU-only install strategy for Phase 8.
- GSD must be installed as prerequisite -- document in setup instructions.

## Session Continuity

Last session: 2026-03-02
Stopped at: Completed 03-03-PLAN.md -- Phase 3 (Validation Infrastructure) complete
Resume file: Phase 4 (Input & Specification)
