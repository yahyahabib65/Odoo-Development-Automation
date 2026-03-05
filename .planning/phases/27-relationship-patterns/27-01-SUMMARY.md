---
phase: 27-relationship-patterns
plan: 01
subsystem: code-generation
tags: [odoo, jinja2, relationships, m2m, hierarchical, through-model, parent-store]

# Dependency graph
requires:
  - phase: 26-monetary-field-detection
    provides: monetary field detection pattern, immutable field rewriting in _build_model_context()
provides:
  - _process_relationships() preprocessor for m2m_through and self_m2m
  - _synthesize_through_model() for auto-generating intermediate models
  - _inject_one2many_links() for parent model reverse relations
  - _enrich_self_referential_m2m() for relation/column params
  - hierarchical model detection with parent_id/child_ids/parent_path injection
  - view_fields filtering to exclude internal fields from views
  - Updated model.py.j2 templates (17.0 + 18.0) for M2M params, ondelete, index, parent_store
affects: [28-model-inheritance, 29-workflow-patterns, template-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [relationship-preprocessing, through-model-synthesis, hierarchical-injection, view-field-filtering]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/src/odoo_gen_utils/templates/18.0/model.py.j2
    - python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2
    - python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2
    - python/tests/test_renderer.py
    - python/tests/test_render_stages.py

key-decisions:
  - "Through-model FK names derived from model last part + _id, with collision check against through_fields"
  - "One2many injection uses {through_model_last_part}_ids naming convention with dedup check"
  - "Self-referential M2M relation table named {model_table}_{field_name}_rel"
  - "Hierarchical fields injected in _build_model_context(), not _process_relationships(), because hierarchy is a model-level property"
  - "view_fields list excludes internal fields; templates use view_fields|default(fields) for backward compatibility"

patterns-established:
  - "Relationship preprocessing: _process_relationships() called before _build_module_context() in render_module()"
  - "Through-model synthesis: auto-generate intermediate models with _synthesized=True flag"
  - "view_fields filtering: internal fields excluded from view rendering via view_fields context key"

requirements-completed: [SPEC-02]

# Metrics
duration: 11min
completed: 2026-03-05
---

# Phase 27 Plan 01: Relationship Patterns Summary

**Through-model synthesis for M2M with extra fields, self-referential M2M with relation/column params, and hierarchical parent_id/parent_path injection with _parent_store class attribute**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-05T17:21:25Z
- **Completed:** 2026-03-05T17:32:40Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- _process_relationships() preprocessor synthesizes through-models and enriches self-referential M2M fields
- model.py.j2 templates (17.0 + 18.0) render relation/column1/column2, ondelete, index, _parent_store
- parent_path excluded from form/tree views via view_fields filtering
- Through-models auto-included in __init__.py imports and ir.model.access.csv ACL entries
- 30 new tests (18 unit + 12 integration), all passing with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: _process_relationships() preprocessor and hierarchical detection (RED)** - `530aa46` (test)
2. **Task 1: _process_relationships() preprocessor and hierarchical detection (GREEN)** - `edd6e7b` (feat)
3. **Task 2: Template updates and integration tests (RED)** - `dbaa16c` (test)
4. **Task 2: Template updates and integration tests (GREEN)** - `007a8f9` (feat)

_Note: TDD tasks have RED (test) and GREEN (feat) commits_

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added _process_relationships(), _synthesize_through_model(), _inject_one2many_links(), _enrich_self_referential_m2m(), hierarchical detection in _build_model_context(), view_fields filtering
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added _parent_store/_parent_name, M2M relation/column params, ondelete/index on M2one, parent_path with unaccent=False
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same template changes as 17.0
- `python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2` - Use view_fields to exclude internal fields
- `python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2` - Use view_fields to exclude internal fields
- `python/tests/test_renderer.py` - 18 new unit tests across 3 test classes
- `python/tests/test_render_stages.py` - 12 new integration tests across 6 test classes

## Decisions Made
- Through-model FK names derived from model last part (e.g., "course_id" from "university.course"), with ValueError on collision with through_fields
- Hierarchical detection placed in _build_model_context() rather than _process_relationships() because it is a model-level property, not a cross-model relationship
- view_fields uses `| default(fields)` Jinja2 fallback for backward compatibility with existing templates that don't pass view_fields

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Relationship patterns complete: through-models, self-referential M2M, and hierarchical models all working
- Template infrastructure extended with index, ondelete, relation/column params
- view_fields pattern ready for future use in excluding other internal/computed fields from views

## Self-Check: PASSED

All files exist on disk. All 4 commit hashes verified in git log.

---
*Phase: 27-relationship-patterns*
*Completed: 2026-03-05*
