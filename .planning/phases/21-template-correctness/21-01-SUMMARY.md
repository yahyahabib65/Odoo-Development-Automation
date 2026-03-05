---
phase: 21-template-correctness
plan: 01
subsystem: codegen
tags: [jinja2, mail.thread, odoo, renderer, line-item-detection]

# Dependency graph
requires:
  - phase: 12-template-quality
    provides: "mail.thread auto-inheritance in _build_model_context()"
provides:
  - "Smart mail.thread injection with line item detection"
  - "Chatter flag support (force/skip/auto)"
  - "In-module parent deduplication for mail.thread"
affects: [21-template-correctness, codegen]

# Tech tracking
tech-stack:
  added: []
  patterns: ["line item detection via required Many2one _id to in-module model"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/tests/test_renderer.py"

key-decisions:
  - "Line item detection uses 4 criteria: Many2one type, required, comodel in module, field name ends in _id"
  - "chatter flag is tri-state: None=auto-detect, True=force, False=skip"
  - "In-module parent detection prevents double mail.thread injection"

patterns-established:
  - "Line item detection pattern: required M2O _id field pointing to in-module model"
  - "Tri-state flag pattern: None=auto, True=force, False=skip"

requirements-completed: [TMPL-01]

# Metrics
duration: 2min
completed: 2026-03-05
---

# Phase 21 Plan 01: Smart mail.thread Injection Summary

**Smart mail.thread injection skipping line items and honoring per-model chatter flag in _build_model_context()**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-05T07:32:45Z
- **Completed:** 2026-03-05T07:34:28Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Line item models (required Many2one _id to in-module model) no longer get mail.thread injected
- Explicit `chatter` flag on models overrides auto-detection in both directions (True forces, False skips)
- Models extending in-module parents skip mail.thread to avoid duplication
- All 83 tests pass (76 existing + 7 new skip-case tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tests for mail.thread skip cases** - `49a6658` (test) - TDD RED: 7 new test methods, 3 expected to fail
2. **Task 2: Implement smart mail.thread injection** - `227aec7` (feat) - TDD GREEN: all 83 tests pass

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added line item detection, chatter flag, and in-module parent check to _build_model_context()
- `python/tests/test_renderer.py` - Added 7 new test methods for mail.thread skip/inject cases

## Decisions Made
- Line item detection requires all 4 criteria (Many2one, required, comodel in module, name ends in _id) to avoid false positives
- Tri-state chatter flag: None auto-detects based on line item status, True/False override explicitly
- Parent-in-module check uses simple set membership on spec model names

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 21-02 can proceed with remaining template correctness fixes
- The `is_line_item` and `chatter` patterns are established for any future template logic

---
*Phase: 21-template-correctness*
*Completed: 2026-03-05*
