---
phase: 34-production-patterns
plan: 01
subsystem: code-generation
tags: [jinja2, odoo, bulk-create, ormcache, api-model-create-multi, tools]

requires:
  - phase: 29-complex-constraints
    provides: "create/write override infrastructure (has_create_override, has_write_override, create_constraints, write_constraints)"
  - phase: 33-database-performance
    provides: "_process_performance() preprocessor pattern, pipeline wiring"
provides:
  - "_process_production_patterns() preprocessor for bulk/cache model enrichment"
  - "@api.model_create_multi with batched _post_create_processing for bulk models"
  - "@tools.ormcache lookup with clear_caches() invalidation for cacheable models"
  - "Merged create/write overrides (constraints + bulk + cache in single methods)"
affects: [34-production-patterns-plan-02, template-generation]

tech-stack:
  added: []
  patterns: ["_process_production_patterns() pure function preprocessor", "conditional tools import in model template", "ormcache lookup method pattern", "bulk post-create batch processing pattern"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/src/odoo_gen_utils/templates/17.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/18.0/model.py.j2"
    - "python/tests/test_renderer.py"
    - "python/tests/test_render_stages.py"

key-decisions:
  - "cache_lookup_field defaults to first unique Char field, then 'name' -- covers most reference data models"
  - "clear_caches() called BEFORE super() in create/write -- invalidate early to prevent stale reads"
  - "bulk _post_create_processing iterates per-record after super().create -- matches Odoo batch-then-process pattern"

patterns-established:
  - "Production pattern preprocessor: pure function that enriches spec models with is_bulk/is_cacheable/needs_tools flags"
  - "Template merge strategy: bulk/cache/constraints all contribute to single create()/write() methods via conditional Jinja2 blocks"

requirements-completed: [PERF-02, PERF-03]

duration: 9min
completed: 2026-03-06
---

# Phase 34 Plan 01: Production Patterns Summary

**Bulk @api.model_create_multi with batched post-processing and @tools.ormcache lookup with cache invalidation, merged with existing constraint overrides into single create/write methods**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-05T21:16:52Z
- **Completed:** 2026-03-05T21:25:53Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- _process_production_patterns() preprocessor enriches models with bulk/cache flags and merges override flags with existing constraint flags
- Model templates render @api.model_create_multi with _post_create_processing for bulk models
- Model templates render @tools.ormcache lookup + clear_caches() invalidation for cacheable models
- Combined bulk+cache+constraints produce single create()/write() methods (no duplicate methods)
- Import line conditionally includes `tools` when needed

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _process_production_patterns() preprocessor (TDD)** - `ac9e0cf` (feat)
2. **Task 2: Extend model.py.j2 templates for bulk and cache patterns** - `84b4b14` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added _process_production_patterns() preprocessor, wired into pipeline, updated _build_model_context() with new keys
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added tools import, ormcache lookup, cache invalidation, bulk post-processing, _post_create_processing stub
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Identical changes as 17.0 template
- `python/tests/test_renderer.py` - 10 unit tests for _process_production_patterns()
- `python/tests/test_render_stages.py` - 4 integration tests for generated output

## Decisions Made
- cache_lookup_field defaults to first unique Char field, then "name" -- covers most reference data models
- clear_caches() called BEFORE super() in create/write -- invalidate early to prevent stale reads
- bulk _post_create_processing iterates per-record after super().create -- matches Odoo batch-then-process pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Production pattern infrastructure complete for bulk and cache
- Plan 02 (archival patterns) can build on same preprocessor function

---
*Phase: 34-production-patterns*
*Completed: 2026-03-06*
