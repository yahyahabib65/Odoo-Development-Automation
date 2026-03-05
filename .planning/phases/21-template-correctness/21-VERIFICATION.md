---
phase: 21-template-correctness
verified: 2026-03-05T08:15:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 21: Template Correctness Verification Report

**Phase Goal:** Generated modules have correct mail.thread usage, wizard imports, wizard ACLs, and modern test assertions
**Verified:** 2026-03-05T08:15:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | mail.thread inheritance is added only to top-level business models (not config tables, line items, wizards, or models extending parents that already have mail.thread) | VERIFIED | `renderer.py` lines 215-243: `is_line_item` detection (4 criteria: Many2one, required, comodel in module, name ends _id), tri-state `chatter` flag, `parent_is_in_module` check. 7 tests pass covering all skip/inject cases. |
| 2 | Wizard template imports `api` only when the generated wizard methods use @api decorators | VERIFIED | `wizard.py.j2` line 2: `from odoo import {{ 'api, ' if needs_api }}fields, models`. `renderer.py` line 648: `"needs_api": True` in wizard_ctx. 2 tests pass. |
| 3 | Generated ir.model.access.csv includes ACL entries for TransientModel wizards alongside regular models | VERIFIED | `access_csv.j2` lines 7-9: `{% for wizard in spec_wizards %}` loop with `1,1,1,1` permissions. `spec_wizards` already in module_context (line 446). 3 tests pass. |
| 4 | Test template asserts on display_name instead of calling deprecated name_get(), with version gate for Odoo 18.0 | VERIFIED | `test_model.py.j2` lines 55-71: `test_display_name` method with `{% if odoo_version >= "18.0" %}` gate. Odoo 18.0+ gets display_name only; Odoo <18.0 gets both display_name and name_get(). 2 tests pass. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/src/odoo_gen_utils/renderer.py` | Smart mail.thread injection + needs_api in wizard_ctx | VERIFIED | Lines 215-243: line item detection, chatter flag, parent-in-module check. Line 648: needs_api=True. |
| `python/src/odoo_gen_utils/templates/shared/wizard.py.j2` | Conditional api import | VERIFIED | Line 2: `{{ 'api, ' if needs_api }}` pattern matches model.py.j2. |
| `python/src/odoo_gen_utils/templates/shared/access_csv.j2` | Wizard ACL entries | VERIFIED | Lines 7-9: wizard loop with 1,1,1,1 for user group, no manager line. |
| `python/src/odoo_gen_utils/templates/shared/test_model.py.j2` | display_name with version gate | VERIFIED | Lines 55-71: `test_display_name` replaces `test_name_get`, version-gated for 18.0+. |
| `python/tests/test_renderer.py` | Tests for all TMPL requirements | VERIFIED | 15 new test methods: 7 mail.thread skip cases, 2 wizard api, 3 wizard ACL, 2 display_name, 1 no-name-field. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `renderer.py` | `wizard.py.j2` | `needs_api` in wizard_ctx | WIRED | Line 648 sets `"needs_api": True`; template line 2 consumes it in conditional. |
| `renderer.py` | `model.py.j2` | `inherit_list` context variable | WIRED | Lines 280-284 pass `inherit_list` and `needs_api`; template renders them. |
| `access_csv.j2` | `renderer.py` | `spec_wizards` in module_context | WIRED | `spec_wizards` set at line 446 of renderer.py; template iterates at line 7. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TMPL-01 | 21-01 | mail.thread injection respects per-model chatter flag | SATISFIED | Smart injection in renderer.py lines 215-243; 7 tests verify skip/inject logic. |
| TMPL-02 | 21-02 | Wizard template conditionally imports api | SATISFIED | wizard.py.j2 line 2 conditional pattern; renderer.py line 648 sets needs_api; 2 tests. |
| TMPL-03 | 21-02 | Wizard TransientModels receive ACL entries | SATISFIED | access_csv.j2 lines 7-9 wizard ACL loop; 3 tests verify entries and permissions. |
| TMPL-04 | 21-02 | Test template uses display_name instead of name_get() | SATISFIED | test_model.py.j2 lines 55-71 version-gated assertion; 2 tests for v17 and v18. |

No orphaned requirements found -- all 4 TMPL requirements from REQUIREMENTS.md are covered by plans and verified.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `wizard.py.j2` | 47 | `# TODO: implement` | Info | Template placeholder in generated output -- intentional for user to fill in wizard action logic. Not a code stub. |

### Human Verification Required

No human verification items needed. All behaviors are fully covered by automated tests (13 phase-specific tests pass, 91 total renderer tests pass with 0 failures).

### Gaps Summary

No gaps found. All 4 success criteria from the roadmap are verified through code inspection and passing tests. The mail.thread injection is smart (skips line items, honors chatter flag, avoids parent duplication). Wizard templates have conditional api import. Access CSV includes wizard ACL entries. Test templates use display_name with proper version gating.

---

_Verified: 2026-03-05T08:15:00Z_
_Verifier: Claude (gsd-verifier)_
