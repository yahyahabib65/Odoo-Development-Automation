---
phase: 34-production-patterns
verified: 2026-03-06T12:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 34: Production Patterns Verification Report

**Phase Goal:** Generated modules support bulk operations, reference data caching, and archival strategies for production-scale usage
**Verified:** 2026-03-06T12:00:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Models with `bulk: true` in spec generate `@api.model_create_multi` on `create()` with batched post-processing | VERIFIED | `_process_production_patterns()` sets `is_bulk=True` + `has_create_override=True` (renderer.py:473-475). Template 17.0/model.py.j2:212 emits `@api.model_create_multi`, line 221-223 emits `_post_create_processing()` loop. 17 unit tests + 4 integration tests pass. |
| 2 | Near-static reference models generate `@tools.ormcache` on lookup methods with cache invalidation in `write()` and `create()` | VERIFIED | `cacheable:true` sets `is_cacheable=True`, `needs_tools=True`, both override flags (renderer.py:477-495). Template emits `@tools.ormcache` lookup (line 205), `clear_caches()` in create (line 215) and write (line 231). Import line includes `, tools` when `needs_tools` (line 2). |
| 3 | Models with `archival: true` generate an `active` field, an archival wizard TransientModel, and an `ir.cron` scheduled action for periodic cleanup | VERIFIED | Preprocessor injects active Boolean field (renderer.py:502-514), archival wizard into spec wizards (516-533), archival cron into spec cron_jobs (535-543). Wizard template `archival_wizard.py.j2` has `action_archive()` with date-based search. Form template has `days_threshold` field and action button. Model template has `_cron_archive_old_records` method. |
| 4 | Archival crons use batch processing with commit-per-batch to avoid long transactions | VERIFIED | Model template (17.0/model.py.j2:262-282) generates `_cron_archive_old_records` with `BATCH_SIZE`, while-loop, `limit=BATCH_SIZE`, and `self.env.cr.commit()` per batch. Integration test `test_archival_cron_has_batch_commit` confirms `cr.commit()` and `BATCH_SIZE` in generated output. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/src/odoo_gen_utils/renderer.py` | `_process_production_patterns()` preprocessor | VERIFIED | Function at line 438, 110+ lines of substantive logic. Wired into pipeline at line 1815. Context keys passed at lines 1128-1132. |
| `python/src/odoo_gen_utils/templates/17.0/model.py.j2` | Bulk/cache/archival template blocks | VERIFIED | `is_bulk`, `is_cacheable`, `is_archival` conditional blocks present at lines 203-282. |
| `python/src/odoo_gen_utils/templates/18.0/model.py.j2` | Same blocks for 18.0 | VERIFIED | Identical pattern at matching line numbers (204-282). Both templates in sync. |
| `python/src/odoo_gen_utils/templates/shared/archival_wizard.py.j2` | Archival wizard TransientModel | VERIFIED | 26 lines, substantive: `days_threshold` field, `action_archive()` method with date cutoff and batch write. |
| `python/src/odoo_gen_utils/templates/shared/archival_wizard_form.xml.j2` | Archival wizard form view | VERIFIED | 26 lines, substantive: form with `days_threshold` field, `action_archive` button, cancel button, act_window action record. |
| `python/tests/test_renderer.py` | Unit tests for production patterns | VERIFIED | 17 test methods: 10 for bulk/cache, 7 for archival. All pass. |
| `python/tests/test_render_stages.py` | Integration tests for generated output | VERIFIED | 10 test methods across `TestRenderModelsProductionPatterns` and `TestRenderModelsArchival`. All pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `renderer.py:_process_production_patterns()` | render_module pipeline | Called at line 1815 after `_process_performance()` | WIRED | `spec = _process_production_patterns(spec)` |
| `renderer.py` | model.py.j2 templates | Context keys: `is_bulk`, `is_cacheable`, `cache_lookup_field`, `needs_tools`, `is_archival` | WIRED | Keys set in `_build_model_context()` at lines 1043-1047, passed in context dict at lines 1128-1132 |
| `renderer.py` | spec['wizards'] | Archival wizard injected at lines 516-533 | WIRED | Wizard dict includes `template` key, `render_wizards()` dispatches via `wizard.get("template")` at line 1405 |
| `renderer.py` | spec['cron_jobs'] | Archival cron injected at lines 535-543 | WIRED | Cron dict uses `model_name` key matching existing `cron_data.xml.j2` expectations |
| `renderer.py` | archival cron dedup | Filters `_cron_archive_old_records` from generic `cron_methods` when `is_archival` | WIRED | Line 1051-1053 prevents duplicate method stubs |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PERF-02 | 34-01 | Models with `bulk: true` generate `@api.model_create_multi` with batched post-processing | SATISFIED | Truth 1 verified. Preprocessor + template + tests all confirm. |
| PERF-03 | 34-01 | Near-static reference models generate `@tools.ormcache` with cache invalidation | SATISFIED | Truth 2 verified. ormcache lookup, clear_caches(), tools import all present. |
| PERF-04 | 34-02 | Models with `archival: true` generate active field, archival wizard, ir.cron | SATISFIED | Truths 3 and 4 verified. Active field, wizard, cron with batch commit all present. |

No orphaned requirements found -- all 3 IDs (PERF-02, PERF-03, PERF-04) are claimed by plans and verified.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `templates/17.0/model.py.j2` | 246 | `# TODO: implement post-create processing` | Info | Intentional -- this is a stub in *generated* Odoo code for developers to fill in. Not a gap in the tool itself. |
| `templates/17.0/model.py.j2` | 255 | `# TODO: implement scheduled action logic` | Info | Same -- intentional stub in generated code for generic cron methods. The archival cron has its own complete implementation. |

No blocker or warning-level anti-patterns found.

### Human Verification Required

### 1. Generated Module Renders Correctly End-to-End

**Test:** Create a spec with a model having `bulk: true`, `cacheable: true`, and `archival: true`, then run `/odoo-gen:new` and inspect the generated Python file.
**Expected:** Single `create()` method with `@api.model_create_multi`, `clear_caches()`, constraint checks, and `_post_create_processing`. Single `write()` method with `clear_caches()` and constraint checks. `@tools.ormcache` lookup method. `_cron_archive_old_records` with batch commit. Archival wizard files in wizards/ directory. Cron XML in data/ directory.
**Why human:** Full end-to-end module generation involves filesystem, template rendering, and __init__.py wiring that integration tests only partially cover.

### 2. Generated Module Installs in Odoo

**Test:** Install a generated module with all three production patterns in a Docker Odoo instance.
**Expected:** Module installs without errors. Active field enables archive/unarchive in list view. Archival wizard opens and archives records. Cron scheduled action appears in Settings > Technical > Scheduled Actions.
**Why human:** Docker validation confirms real Odoo compatibility, not just template correctness.

### Gaps Summary

No gaps found. All 4 success criteria from ROADMAP.md are verified:

1. Bulk create with `@api.model_create_multi` and batched post-processing -- preprocessor, template, and tests all confirmed.
2. ORM cache with `@tools.ormcache` lookup and `clear_caches()` invalidation -- preprocessor, template, tools import, and tests all confirmed.
3. Archival with active field, wizard, and cron -- preprocessor injection, dedicated templates, model template cron method, and tests all confirmed.
4. Batch cron with `cr.commit()` per batch -- template generates while-loop with BATCH_SIZE and commit, integration test confirms.

All 27 tests (17 unit + 10 integration) pass. All 5 commits verified in git history.

---

_Verified: 2026-03-06T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
