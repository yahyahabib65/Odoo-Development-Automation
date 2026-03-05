---
phase: 26-monetary-field-detection
plan: 01
subsystem: codegen
tags: [odoo, monetary, jinja2, fields, currency]

requires:
  - phase: 05-code-generation
    provides: "_build_model_context() and model.py.j2 template pipeline"
provides:
  - "Automatic Float->Monetary rewrite for monetary-named fields"
  - "currency_id companion field auto-injection in templates"
  - "MONETARY_FIELD_PATTERNS constant and _is_monetary_field() helper"
  - "needs_currency_id context key for template rendering"
affects: [template-generation, spec-design]

tech-stack:
  added: []
  patterns: ["immutable field rewrite via list comprehension with spread operator"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/src/odoo_gen_utils/templates/17.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/18.0/model.py.j2"
    - "python/tests/test_renderer.py"

key-decisions:
  - "Monetary branch placed before compute branch in template to handle both plain and computed Monetary fields"
  - "20 monetary keyword patterns chosen to cover common Odoo financial field names"
  - "Opt-out via monetary: false flag for edge cases where Float name matches but is not monetary"

patterns-established:
  - "Immutable field rewrite: use list comprehension with {**f, key: value} instead of mutating original"
  - "Template branch ordering: Selection -> Relational -> Sequence -> Monetary -> Compute -> Catch-all"

requirements-completed: [SPEC-01]

duration: 8min
completed: 2026-03-05
---

# Phase 26 Plan 01: Monetary Field Detection Summary

**Automatic Float-to-Monetary field detection with 20 keyword patterns, currency_id injection, and opt-out support for both 17.0 and 18.0 templates**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-05T16:52:31Z
- **Completed:** 2026-03-05T17:00:18Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Float fields with monetary name patterns (amount, price, cost, salary, etc.) auto-detected and rendered as fields.Monetary
- currency_id Many2one companion field auto-injected with company default when not present in spec
- Both 17.0 and 18.0 model templates updated with Monetary branch and currency_id injection block
- 59 new tests (54 unit + 5 integration) covering all 20 patterns, opt-out, immutability, and rendered output

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests + implement monetary detection in renderer.py** - `9be7e4d` (feat)
2. **Task 2: Update model.py.j2 templates + integration tests** - `c67f3d1` (feat)

_Note: Both tasks followed TDD (RED-GREEN) workflow_

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added MONETARY_FIELD_PATTERNS, _is_monetary_field(), monetary detection in _build_model_context(), needs_currency_id context key
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added currency_id injection block and Monetary field rendering branch
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same changes as 17.0 template
- `python/tests/test_renderer.py` - Added TestMonetaryPatternDetection (54 tests), TestBuildModelContextMonetary (6 tests), TestRenderModuleMonetary (5 integration tests)

## Decisions Made
- Placed Monetary branch before compute branch in template so computed Monetary fields get both compute= and currency_field= parameters
- Used 20 keyword patterns covering standard Odoo financial terms (amount, fee, salary, price, cost, balance, total, subtotal, tax, discount, payment, revenue, expense, budget, wage, rate, charge, premium, debit, credit)
- Opt-out supported via explicit "monetary": false in field spec

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Monetary detection complete and tested
- Ready for next v3.1 phase (SPEC-02 or other spec design work)

---
*Phase: 26-monetary-field-detection*
*Completed: 2026-03-05*
