---
phase: 27-relationship-patterns
verified: 2026-03-05T18:15:00Z
status: passed
score: 6/6 must-haves verified
---

# Phase 27: Relationship Patterns Verification Report

**Phase Goal:** Spec supports rich relationship declarations that generate through-models for M2M with extra fields, self-referential M2M with explicit relation/column params, and hierarchical parent_id with parent_path
**Verified:** 2026-03-05T18:15:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A spec with m2m_through relationship generates a through-model with two Many2one FKs and extra fields | VERIFIED | `_synthesize_through_model()` at renderer.py:80-131 creates model dict with FK fields (required=True, ondelete=cascade) + through_fields; 6 unit tests in `TestProcessRelationshipsM2MThrough` pass; 3 integration tests in `TestRenderModelsThroughModel` confirm rendered .py output |
| 2 | Through-model appears in rendered models/__init__.py and ir.model.access.csv | VERIFIED | Through-model is appended to `spec["models"]` at renderer.py:72, which is consumed by `init_models.py.j2` and `access_csv.j2` templates; integration tests `TestRenderManifestThroughModel` and `TestRenderSecurityThroughModel` pass |
| 3 | A spec with self_m2m relationship generates Many2many fields with relation, column1, column2 params | VERIFIED | `_enrich_self_referential_m2m()` at renderer.py:170-218 adds relation/column1/column2; template renders via `{% if field.type == 'Many2many' and field.relation is defined %}` at model.py.j2:56-60 (17.0) and :57-61 (18.0); 5 unit tests in `TestProcessRelationshipsSelfM2M` + 2 integration tests pass |
| 4 | A spec with hierarchical: true generates parent_id, child_ids, parent_path fields and _parent_store class attribute | VERIFIED | `_build_model_context()` at renderer.py:457-487 injects all three fields; template renders `_parent_store = True` and `_parent_name = "parent_id"` at model.py.j2:14-17; 6 unit tests in `TestBuildModelContextHierarchical` + 4 integration tests pass |
| 5 | parent_path is excluded from view-relevant field lists | VERIFIED | `view_fields` at renderer.py:490 filters `internal` fields; all view_form.xml.j2 templates use `view_fields | default(fields)` (18 occurrences across 17.0 and 18.0); integration test `test_parent_path_not_in_form_view` passes |
| 6 | Duplicate One2many injection on parent models is prevented | VERIFIED | `_inject_one2many_links()` at renderer.py:151/160 checks `any(f.get("name") == target_field_name ...)` before appending; unit test `test_no_duplicate_injection` passes |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/src/odoo_gen_utils/renderer.py` | `_process_relationships()` preprocessor, hierarchical detection | VERIFIED | Contains `_process_relationships`, `_synthesize_through_model`, `_inject_one2many_links`, `_enrich_self_referential_m2m`, hierarchical block in `_build_model_context`, `view_fields` filtering |
| `python/src/odoo_gen_utils/templates/17.0/model.py.j2` | M2M relation/column rendering, _parent_store, parent_path | VERIFIED | Lines 14-17: `_parent_store`/`_parent_name`; Lines 45-49: parent_path with unaccent=False; Lines 56-60: M2M relation/column params; Lines 65-70: index and ondelete |
| `python/src/odoo_gen_utils/templates/18.0/model.py.j2` | Same template changes as 17.0 | VERIFIED | Identical Phase 27 additions confirmed |
| `python/tests/test_renderer.py` | Unit tests for relationship preprocessing and hierarchical context | VERIFIED | `TestProcessRelationshipsM2MThrough` (6 tests), `TestProcessRelationshipsSelfM2M` (5 tests), `TestBuildModelContextHierarchical` (6 tests) = 17 unit tests at lines 1867-2166 |
| `python/tests/test_render_stages.py` | Integration tests for rendered output | VERIFIED | `TestRenderModelsThroughModel` (3), `TestRenderManifestThroughModel` (1), `TestRenderSecurityThroughModel` (1), `TestRenderModelsSelfM2M` (2), `TestRenderModelsHierarchical` (5) = 12 integration tests at lines 550-655 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `render_module()` | `_process_relationships()` | Called before `_build_module_context()` | WIRED | renderer.py:986: `spec = _process_relationships(spec)` -- before line 989: `ctx = _build_module_context(spec, module_name)` |
| `_build_model_context()` | `model.py.j2` template | `is_hierarchical` context key | WIRED | renderer.py:535: `"is_hierarchical": is_hierarchical` passed to template; template checks `{% if is_hierarchical is defined and is_hierarchical %}` |
| `_synthesize_through_model()` | `init_models.py.j2` and `access_csv.j2` | Appended to spec['models'] list | WIRED | renderer.py:72: `new_models.append(through_model)` -- through-model becomes part of `spec["models"]` which templates iterate |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SPEC-02 | 27-01-PLAN.md | Spec supports relationships section with through-models, self-referential M2M, and hierarchical parent_id patterns | SATISFIED | All three relationship patterns implemented and tested: m2m_through (through-model synthesis), self_m2m (relation/column params), hierarchical (parent_id/child_ids/parent_path/_parent_store). 27 tests pass (all Phase 27 specific), 0 regressions in core suite. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No anti-patterns found in Phase 27 modified files |

No TODO/FIXME/placeholder/stub patterns found in renderer.py or templates. All implementations are substantive.

### Human Verification Required

None required. All behaviors are testable programmatically and verified by the test suite.

### Gaps Summary

No gaps found. All 6 observable truths verified, all 5 artifacts substantive and wired, all 3 key links confirmed, SPEC-02 requirement satisfied. The pre-existing test failures in `test_docker_integration.py`, `test_golden_path.py`, and `test_verifier_integration.py` are unrelated to Phase 27 (those files were not modified in this phase).

---

_Verified: 2026-03-05T18:15:00Z_
_Verifier: Claude (gsd-verifier)_
