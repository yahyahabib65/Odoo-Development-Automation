# Research Summary: v3.0 Codebase Audit

**Date:** 2026-03-05
**Method:** 4 parallel codebase auditors verified 42 items from BUGS_FLAWS_DEBT.md against actual source code
**Confidence:** HIGH — every item verified by reading actual source files

## Audit Results

### Bugs: 12/12 CONFIRMED

| ID | Title | Severity | File | Status |
|----|-------|----------|------|--------|
| BUG-H1 | mail.thread blind injection | HIGH | renderer.py:218-221 | CONFIRMED |
| BUG-H2 | Docker exec race condition | HIGH | docker_runner.py:151 | CONFIRMED |
| BUG-H3 | Regex-based auto-fix | HIGH | auto_fix.py (5 of 6 functions) | CONFIRMED |
| BUG-M1 | string= multi-line fail | MEDIUM | auto_fix.py:121-150 | CONFIRMED |
| BUG-M2 | AST misses _inherit-only | MEDIUM | analyzer.py:89 | CONFIRMED |
| BUG-M3 | Unused imports whitelist | MEDIUM | auto_fix.py:1053-1058 | CONFIRMED |
| BUG-M4 | No GitHub rate limiting | MEDIUM | index.py:106-236 | CONFIRMED |
| BUG-M5 | CLI eager imports | MEDIUM | cli.py:11-43 | CONFIRMED |
| BUG-M6 | Wizard api import | MEDIUM | wizard.py.j2:2 | CONFIRMED |
| BUG-L1 | Wizard ACLs missing | LOW | access_csv.j2:3-6 | CONFIRMED |
| BUG-L2 | Deprecated name_get() | LOW | test_model.py.j2:57 | CONFIRMED |
| BUG-L3 | Inconsistent error handling | LOW | 6+ files | CONFIRMED |

### Tech Debt: 4/4 CONFIRMED

| ID | Title | Severity | File | Status |
|----|-------|----------|------|--------|
| DEBT-01 | render_module 371-line monolith | HIGH | renderer.py:330-701 | CONFIRMED |
| DEBT-02 | 5 parent path traversals | MEDIUM | docker_runner.py:42-51 | CONFIRMED |
| DEBT-03 | No unified Result type | MEDIUM | cross-cutting | CONFIRMED |
| DEBT-04 | GitHub rate limiting arch debt | MEDIUM | index.py | CONFIRMED (same root as M4) |

### Deduplication

- BUG-M4 and DEBT-04 share the same root cause → fix once as rate limiting infrastructure
- BUG-L3 and DEBT-03 share the same root cause → fix once as unified Result type
- BUG-H3 subsumes BUG-M1 → AST-based auto-fix resolves multi-line handling automatically
- **Effective unique items: 13**

### Flaws: Deferred to v3.1

24 CONFIRMED, 1 PARTIAL, 1 NOT FOUND (FLAW-22 Pakistan localization — correctly out of scope).
Full flaw audit preserved in auditor output files.

## v3.0 Scope

**IN SCOPE:** 12 bugs + 4 tech debt = 16 items (13 unique after dedup)
**DEFERRED to v3.1:** 24 design flaws
**OUT OF SCOPE:** FLAW-22 (Pakistan localization), FLAW-23 (academic calendar)

---
*Research completed: 2026-03-05*
*Ready for requirements: yes*
