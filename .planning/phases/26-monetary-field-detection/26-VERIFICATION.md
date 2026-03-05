---
phase: 26-monetary-field-detection
verified: 2026-03-05T17:15:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 26: Monetary Field Detection Verification Report

**Phase Goal:** Spec fields matching monetary patterns (amount, fee, salary, price, cost, balance) automatically become fields.Monetary with currency_id companion field injected
**Verified:** 2026-03-05T17:15:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A spec field named 'amount' (type Float) renders as fields.Monetary in generated model | VERIFIED | `_is_monetary_field()` returns True for Float+amount; `_build_model_context()` rewrites type to "Monetary"; template renders `fields.Monetary`; integration test `test_monetary_field_rendered_as_fields_monetary` passes |
| 2 | A spec field named 'total_price' (type Float) renders as fields.Monetary in generated model | VERIFIED | Substring match via `any(pattern in name ...)` catches "price" in "total_price"; unit test `test_float_total_price_is_monetary` passes |
| 3 | When any monetary field is detected, currency_id Many2one to res.currency is auto-injected | VERIFIED | `needs_currency_id` context key set True when monetary detected and no currency_id present; template block at line 15-21 of 17.0/model.py.j2 injects `currency_id = fields.Many2one(comodel_name="res.currency", ...)`. Integration test `test_currency_id_injected_when_not_in_spec` passes |
| 4 | If currency_id already exists in the spec, no duplicate injection occurs | VERIFIED | `has_currency_id` check at renderer.py:249; unit test `test_needs_currency_id_false_when_currency_id_exists` passes |
| 5 | Explicit type: Integer on a field named 'amount' is NOT rewritten to Monetary | VERIFIED | `_is_monetary_field()` returns False for non-Float types; unit test `test_integer_amount_not_monetary` passes |
| 6 | A field with monetary: false opt-out is NOT rewritten to Monetary | VERIFIED | First check in `_is_monetary_field()` is `if field.get("monetary") is False: return False`; unit test `test_float_amount_opt_out` passes |
| 7 | Generated Monetary fields include currency_field='currency_id' parameter | VERIFIED | Template line 66 (17.0) and line 67 (18.0): `currency_field="currency_id"`; integration test asserts `'currency_field="currency_id"' in model_content` |
| 8 | Injected currency_id includes default=lambda self: self.env.company.currency_id | VERIFIED | Template line 19 (17.0) and line 20 (18.0): `default=lambda self: self.env.company.currency_id`; integration test asserts this string in output |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/src/odoo_gen_utils/renderer.py` | MONETARY_FIELD_PATTERNS, _is_monetary_field(), monetary detection in _build_model_context() | VERIFIED | Lines 21-26: 20-keyword frozenset. Lines 29-49: _is_monetary_field(). Lines 242-250: immutable rewrite + needs_currency_id. Line 329: context key returned |
| `python/src/odoo_gen_utils/templates/17.0/model.py.j2` | Monetary field rendering branch + currency_id injection block | VERIFIED | Lines 15-21: currency_id injection. Lines 63-79: Monetary branch with currency_field, compute, store, required, help support |
| `python/src/odoo_gen_utils/templates/18.0/model.py.j2` | Monetary field rendering branch + currency_id injection block (18.0) | VERIFIED | Lines 16-21: currency_id injection. Lines 65-79: Monetary branch (identical structure to 17.0) |
| `python/tests/test_renderer.py` | Unit tests for monetary detection and rendering | VERIFIED | 3 test classes: TestMonetaryPatternDetection (line 1672, 8 tests + 40 parametrized), TestBuildModelContextMonetary (line 1708, 6 tests), TestRenderModuleMonetary (line 1762, 5 integration tests). 59 tests total, all passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| renderer.py | 17.0/model.py.j2 | context key `needs_currency_id` | WIRED | renderer.py:329 returns `needs_currency_id`; template line 15 checks `{% if needs_currency_id %}` |
| renderer.py | 18.0/model.py.j2 | context key `needs_currency_id` | WIRED | Same context key consumed at template line 16 |
| renderer.py | 17.0/model.py.j2 | field type "Monetary" in fields list | WIRED | renderer.py:246 rewrites to "Monetary"; template line 63 checks `{% elif field.type == 'Monetary' %}` |
| renderer.py | 18.0/model.py.j2 | field type "Monetary" in fields list | WIRED | Same wiring as 17.0, template line 65 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SPEC-01 | 26-01-PLAN | Renderer auto-detects Monetary field patterns and generates fields.Monetary with currency_id injection | SATISFIED | All 8 truths verified. 59 tests passing. Both 17.0 and 18.0 templates updated |

No orphaned requirements found -- REQUIREMENTS.md maps only SPEC-01 to Phase 26, and the plan claims SPEC-01.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No anti-patterns detected |

No TODO/FIXME/placeholder comments, no empty implementations, no console.log stubs found in modified files.

### Human Verification Required

### 1. Generated Module Installation

**Test:** Generate a module with a Float field named "amount", install it in an Odoo 17 instance
**Expected:** Module installs without `AssertionError: unknown currency_field None`; the amount field displays with currency formatting
**Why human:** Requires a running Odoo instance with Docker to verify actual install behavior

---

_Verified: 2026-03-05T17:15:00Z_
_Verifier: Claude (gsd-verifier)_
