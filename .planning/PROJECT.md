# Agentic Odoo Module Development Workflow

## What This Is

A CLI-based multi-agent orchestration system that automates the development of production-ready Odoo 17.0 modules. A developer describes a business need in natural language, the system semantically searches GitHub and the Odoo Community Association (OCA) for similar existing modules, then either forks and extends a match or builds from scratch — producing enterprise-grade modules through coordinated AI agents with human review at key checkpoints.

## Core Value

Compress months of repetitive Odoo module development into days by leveraging existing open-source modules as foundations and coordinating multiple AI agents to handle the mechanical work, so developers focus on business logic and design decisions.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can describe a module need in natural language via CLI
- [ ] System asks structured follow-up questions to fill gaps in the description
- [ ] System semantically searches GitHub repos for similar Odoo modules
- [ ] System semantically searches OCA repos for similar Odoo modules
- [ ] System scores and ranks candidate modules by relevance to user's intent
- [ ] System forks and clones the best-matching module when a match is found
- [ ] System builds a module from scratch when no suitable match exists
- [ ] Multiple AI agents collaborate on module generation (models, views, security, logic, tests)
- [ ] Human reviews and approves at checkpoints (after models, after views, after logic, etc.)
- [ ] Generated modules install cleanly on Odoo 17.0 (CE and EE)
- [ ] Generated modules include full security (ACLs, record rules, group hierarchy)
- [ ] Generated modules include unit and integration tests
- [ ] Generated modules pass OCA quality standards (pylint-odoo, i18n, coding standards)
- [ ] Docker-based Odoo environment validates module installation and test execution
- [ ] System targets Odoo 17.0 as primary version, supports both Community and Enterprise

### Out of Scope

- Web UI / browser interface — CLI-only for v1
- Mobile app — not applicable
- Odoo 18.0 support — defer until 17.0 pipeline is solid
- Selling this as a product — internal dev team tool only
- Real-time collaborative editing — single-user CLI workflow
- Module deployment to production — system generates, human deploys

## Context

- The team has some Odoo development experience (built modules, knows the basics) but wants to eliminate the months of boilerplate and repetitive work that characterizes Odoo module development
- Odoo modules span dozens of interconnected files (models, views, security, data, wizards, reports, controllers, tests) with XML boilerplate, ORM quirks, and cross-module integration complexity
- The OCA ecosystem has thousands of existing modules that often partially solve what teams need — finding and extending them is faster than building from scratch
- Multi-agent AI systems (Claude Code, OpenAI Codex CLI, Gemini CLI) can each handle different aspects of module generation, with custom skills encoding Odoo-specific patterns
- MCP servers can give agents access to running Odoo instances, documentation, and schema introspection
- The orchestration approach (Python coordinator vs n8n vs Claude-as-orchestrator) is an open design question — research should determine the best fit
- Volume expectation: 1-2 modules per week at a steady quality-focused pace

## Constraints

- **Target Version**: Odoo 17.0 — stable, widely adopted, good community support
- **Quality Standard**: OCA-grade — pylint-odoo clean, proper i18n, full security, tests, clean install
- **Interface**: CLI tool — `odoo-gen` or similar command-line interface
- **Edition Support**: Both Community and Enterprise edition modules
- **Test Infrastructure**: Docker-based Odoo instances for validation (to be set up as part of project)
- **Build Strategy**: Search-first — always check for existing modules before building from scratch
- **Human Oversight**: Checkpoint-based review at key generation stages
- **API Budget**: Unconstrained — prioritize quality over cost savings

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Odoo 17.0 as primary target | Stable, widely adopted, strong OCA support; 18.0 can come later | — Pending |
| CLI interface for v1 | Fastest to build, matches dev team workflow, web UI is scope creep | — Pending |
| Fork-and-extend strategy | Leveraging existing OCA/GitHub modules is faster and more reliable than always building from scratch | — Pending |
| Semantic search over keyword | User intent matters more than exact naming; "leave management" should find "hr_holidays" extensions | — Pending |
| Checkpoint-based human review | Balance between full automation (risky) and per-line review (slow); approve at stage boundaries | — Pending |
| OCA quality as the bar | If modules pass OCA standards, they're production-ready by definition | — Pending |
| Orchestration approach TBD | Let research phase determine best fit rather than premature commitment | — Pending |
| Docker for validation | Only way to truly verify module installs and tests pass; no shortcut | — Pending |

---
*Last updated: 2026-03-01 after initialization*
