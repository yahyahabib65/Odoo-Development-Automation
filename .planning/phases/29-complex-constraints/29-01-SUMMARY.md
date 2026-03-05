---
phase: 29-complex-constraints
plan: 01
subsystem: codegen
tags: [jinja2, constraints, validation, odoo-orm, preprocessor]

# Dependency graph
requires:
  - phase: 28-computed-chains-cycle-detection
    provides: preprocessor pipeline pattern (_process_computation_chains), render_module() orchestration
provides:
  - _process_constraints() preprocessor handling temporal, cross_model, capacity constraint types
  - model.py.j2 template extensions for constraint method rendering (17.0 + 18.0)
  - Complex constraint context keys in _build_model_context()
affects: [30-cron-schedules, 31-qweb-reports]

# Tech tracking
tech-stack:
  added: []
  patterns: [constraint preprocessor enrichment, create/write override generation, temporal False guards]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/src/odoo_gen_utils/templates/18.0/model.py.j2
    - python/tests/test_renderer.py
    - python/tests/test_render_stages.py

key-decisions:
  - "Temporal constraints use @api.constrains; cross_model and capacity use create()/write() overrides (Odoo ORM limitation: @api.constrains ignores dotted field names)"
  - "Preprocessor generates check_body as pre-rendered string for cross_model/capacity; template inserts with indent filter"
  - "All error messages wrapped in _() for i18n; needs_translate context key triggers import"

patterns-established:
  - "Constraint preprocessor: classify by type, enrich model dict with metadata, template renders"
  - "Single create()/write() override per model with multiple _check_* calls (avoids clobbering)"

requirements-completed: [SPEC-04]

# Metrics
duration: 10min
completed: 2026-03-05
---

# Phase 29 Plan 01: Complex Constraints Summary

**Declarative constraint generation from spec: temporal (@api.constrains with date guards), cross-model (create/write overrides with search_count), and capacity (count-based validation) -- all with _() translated error messages**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-05T18:26:44Z
- **Completed:** 2026-03-05T18:36:42Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- `_process_constraints()` pure preprocessor handling 3 constraint types with immutable spec transformation
- model.py.j2 templates (17.0 + 18.0) extended with @api.constrains, create/write override, and _check_* method blocks
- 16 new tests (11 unit + 5 integration), full suite green (662 non-Docker tests pass)

## Task Commits

Each task was committed atomically:

1. **Task 1: Constraint preprocessor, template extensions, and unit tests** - `a37b494` (feat)
2. **Task 2: Integration tests for end-to-end constraint rendering** - `0b34a87` (test)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added _process_constraints() preprocessor, wired into render_module(), extended _build_model_context() with constraint context keys
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added _() import, @api.constrains blocks, create/write overrides, _check_* methods
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same additions as 17.0
- `python/tests/test_renderer.py` - TestProcessConstraints with 11 unit tests
- `python/tests/test_render_stages.py` - TestRenderModelsComplexConstraints with 5 integration tests

## Decisions Made
- Temporal constraints use @api.constrains with False guards (Odoo Date defaults to False); cross_model and capacity use create()/write() overrides because @api.constrains silently ignores dotted field names
- Pre-rendered check_body strings in preprocessor for cross_model/capacity; template uses indent filter for correct indentation
- needs_translate context key controls `from odoo.tools.translate import _` import

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Code Quality] Moved inline `import re` to module level**
- **Found during:** Task 1
- **Issue:** `import re` was inside the nested function _enrich_constraint
- **Fix:** Moved to top-level imports
- **Files modified:** python/src/odoo_gen_utils/renderer.py
- **Verification:** All tests pass
- **Committed in:** a37b494

---

**Total deviations:** 1 auto-fixed (1 code quality)
**Impact on plan:** Minor cleanup, no scope change.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Constraint generation complete for all 3 types
- Template infrastructure ready for Phase 30 (cron schedules) and beyond
- Full backward compatibility confirmed

---
## Self-Check: PASSED

All 6 files found, both commits verified.

---
*Phase: 29-complex-constraints*
*Completed: 2026-03-05*
