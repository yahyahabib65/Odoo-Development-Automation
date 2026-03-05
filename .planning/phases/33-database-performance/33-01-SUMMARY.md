---
phase: 33-database-performance
plan: 01
subsystem: database
tags: [odoo, index, store, sql_constraints, transient, performance, jinja2]

# Dependency graph
requires:
  - phase: 28-computation-chains
    provides: "_process_computation_chains() preprocessor pattern, computed field awareness"
  - phase: 29-complex-constraints
    provides: "_process_constraints() preprocessor, complex_constraints model enrichment"
  - phase: 32-controllers-import-export
    provides: "render_controllers(), import_wizard.py.j2 template"
provides:
  - "_process_performance() preprocessor for automatic index/store/sql_constraints/transient enrichment"
  - "model_order context key for _order attribute rendering"
  - "index=True rendering on all field types in model.py.j2"
  - "_transient_max_hours/_transient_max_count on wizard and import wizard templates"
affects: [34-archival-cron, future-performance-phases]

# Tech tracking
tech-stack:
  added: []
  patterns: ["_process_performance() pure function preprocessor", "field usage analysis for index detection"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/src/odoo_gen_utils/templates/17.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/18.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/shared/wizard.py.j2"
    - "python/src/odoo_gen_utils/templates/shared/import_wizard.py.j2"
    - "python/tests/test_renderer.py"
    - "python/tests/test_render_stages.py"

key-decisions:
  - "INDEXABLE_TYPES constant defines which field types can receive index=True (Char, Integer, Float, Date, Datetime, Boolean, Selection, Many2one, Monetary)"
  - "model.order requires explicit spec key -- no auto-inference from field names"
  - "Selection fields indexed for group-by filters (PostgreSQL handles low-cardinality reasonably)"
  - "TransientModel defaults: 1.0 hours max, 0 count limit (hour-based cleanup sufficient)"

patterns-established:
  - "_process_performance() follows same pure-function pattern as _process_relationships, _process_computation_chains, _process_constraints"
  - "Field usage analysis: search_fields | order_fields | domain_fields determines index candidates"

requirements-completed: [PERF-01, PERF-05]

# Metrics
duration: 12min
completed: 2026-03-06
---

# Phase 33 Plan 01: Database Performance Summary

**Automatic database performance optimization: index=True on search/order/domain fields, store=True on view-referenced computed fields, _sql_constraints from unique_together, and TransientModel cleanup config**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-05T20:35:20Z
- **Completed:** 2026-03-05T20:47:20Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added _process_performance() pure function preprocessor that auto-detects fields needing index=True (search, order, domain) and store=True (computed fields in views)
- Auto-generates _sql_constraints from unique_together spec key with field validation
- TransientModel models get _transient_max_hours/_transient_max_count with configurable defaults
- Updated model.py.j2 templates (both 17.0 and 18.0) to render _order attribute and index=True on all field type blocks
- 14 unit tests + 5 integration tests, all passing with zero regressions (326 total)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _process_performance() preprocessor (TDD)** - `ad3a043` (feat)
2. **Task 2: Update Jinja2 templates for _order, index=True, TransientModel** - `d7ff77e` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added _process_performance(), _enrich_model_performance(), INDEXABLE_TYPES/NON_INDEXABLE_TYPES constants, updated _build_model_context with Phase 33 keys, wired into render_module pipeline
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added _order rendering, index=True on Selection/computed/Monetary/generic field blocks
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same changes as 17.0
- `python/src/odoo_gen_utils/templates/shared/wizard.py.j2` - Added _transient_max_hours/_transient_max_count rendering
- `python/src/odoo_gen_utils/templates/shared/import_wizard.py.j2` - Added _transient_max_hours/_transient_max_count with defaults
- `python/tests/test_renderer.py` - Added TestProcessPerformance class with 14 tests
- `python/tests/test_render_stages.py` - Added TestRenderModelsPerformance class with 5 integration tests

## Decisions Made
- INDEXABLE_TYPES = {Char, Integer, Float, Date, Datetime, Boolean, Selection, Many2one, Monetary} -- excludes One2many, Many2many, Html, Text, Binary
- model.order is explicit (not auto-inferred) -- safer and more predictable
- Selection fields indexed for group-by (low-cardinality is OK for PostgreSQL)
- TransientModel defaults: _transient_max_hours=1.0, _transient_max_count=0

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Performance preprocessing complete, ready for Phase 34 or milestone wrap-up
- All generated modules now automatically get correct database indexes, stored computed fields, uniqueness constraints, and wizard cleanup

---
*Phase: 33-database-performance*
*Completed: 2026-03-06*
