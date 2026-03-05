---
phase: 28-computed-chains-cycle-detection
plan: 01
subsystem: codegen
tags: [graphlib, topological-sort, cycle-detection, computed-fields, odoo-api-depends]

# Dependency graph
requires:
  - phase: 27-relationship-patterns
    provides: _process_relationships() preprocessor pattern, _build_model_context() pipeline
provides:
  - _validate_no_cycles() for circular dependency detection in computation_chains
  - _process_computation_chains() for enriching fields with depends/store/compute
  - _topologically_sort_fields() for intra-model computed field ordering
  - _resolve_comodel() helper for cross-model dotted path resolution
affects: [template-generation, spec-validation]

# Tech tracking
tech-stack:
  added: [graphlib (stdlib)]
  patterns: [spec-level validation before rendering, computation chain preprocessing, topological field ordering]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/tests/test_renderer.py
    - python/tests/test_render_stages.py

key-decisions:
  - "Used graphlib.TopologicalSorter from stdlib for both sorting and cycle detection -- zero new dependencies"
  - "Cycle validation runs FIRST in render_module(), before any file generation"
  - "Chain preprocessor is pure function returning new spec (immutability preserved)"

patterns-established:
  - "Spec-level validation pattern: validate constraints before any processing or rendering"
  - "Computation chain enrichment: computation_chains section enriches field dicts with depends/store/compute"

requirements-completed: [SPEC-03, SPEC-05]

# Metrics
duration: 5min
completed: 2026-03-05
---

# Phase 28 Plan 01: Computed Chains & Cycle Detection Summary

**graphlib-based cycle detection and chain preprocessing for multi-model computed fields with dotted @api.depends paths, store=True injection, and topological ordering**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T17:58:10Z
- **Completed:** 2026-03-05T18:03:29Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Circular dependency detection rejects invalid specs with actionable error messages before any files are generated
- computation_chains section enriches fields with correct @api.depends dotted paths, store=True, and compute method names
- Computed fields topologically sorted within each model so upstream fields appear before downstream
- Full backward compatibility -- specs without computation_chains work identically to before
- 19 new tests (14 unit + 5 integration), full suite green with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Cycle detection, chain preprocessor, and topological sort functions** - `8945f51` (feat)
2. **Task 2: Integration tests for end-to-end chain rendering and cycle rejection** - `0e8fdf4` (test)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added _validate_no_cycles(), _process_computation_chains(), _topologically_sort_fields(), _resolve_comodel(); wired into render_module() and _build_model_context()
- `python/tests/test_renderer.py` - 14 new unit tests in TestValidateNoCycles, TestProcessComputationChains, TestTopologicallySortFields
- `python/tests/test_render_stages.py` - 5 new integration tests in TestRenderModelsComputedChains

## Decisions Made
- Used graphlib.TopologicalSorter from stdlib -- zero new dependencies, provides both sorting and CycleError with cycle participant reporting
- Cycle validation placed as FIRST operation in render_module() to prevent any partial file output on invalid specs
- Chain preprocessor follows immutable pattern established in Phase 27 (_process_relationships)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Computation chain infrastructure complete, ready for template generation phases
- All 231 renderer tests pass (212 existing + 19 new)

---
*Phase: 28-computed-chains-cycle-detection*
*Completed: 2026-03-05*
