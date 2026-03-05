---
phase: 32-controllers-import-export
verified: 2026-03-06T20:30:00Z
status: passed
score: 8/8 must-haves verified
---

# Phase 32: Controllers & Import/Export Verification Report

**Phase Goal:** Generator produces HTTP controllers with secure defaults and import/export TransientModel wizards with file upload, validation, and batch processing
**Verified:** 2026-03-06T20:30:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A spec with controllers entries generates controllers/main.py with @http.route decorators | VERIFIED | controller.py.j2 line 9-15 has `@http.route()` decorator loop; render_controllers() line 1336-1340 renders to `controllers/main.py`; 8 tests in TestRenderControllers pass |
| 2 | Generated controllers default to auth='user' and csrf=True (secure by default) | VERIFIED | controller.py.j2 line 12 `auth='{{ route.get("auth", "user") }}'`, line 13 `csrf={{ route.get("csrf", True) }}`; defaults applied via dict.get() |
| 3 | JSON routes include try/except error handling with structured error response | VERIFIED | controller.py.j2 lines 19-23: `try/except Exception as e` with `{'status': 'error', 'message': str(e)}` return |
| 4 | controllers/__init__.py is generated and imports main; root __init__.py conditionally imports controllers | VERIFIED | init_controllers.py.j2 has `from . import main`; init_root.py.j2 line 6-8 has `{% if has_controllers %}from . import controllers{% endif %}` |
| 5 | A spec with import_export:true on a model generates a TransientModel import wizard | VERIFIED | import_wizard.py.j2 line 9 `class {{ wizard_class }}(models.TransientModel)`; render_controllers() lines 1348-1383 generates wizard files; 9 tests in TestRenderImportExport pass |
| 6 | Import wizard has Binary upload, state machine (upload/preview/done), magic byte validation, preview, batch import, and xlsx export | VERIFIED | import_wizard.py.j2: fields.Binary (line 23), state Selection (lines 13-21), _validate_file_content with `b'PK\x03\x04'` (lines 29-38), action_preview (lines 40-65), _do_import (lines 87-103), action_export with openpyxl (lines 114-142) |
| 7 | Import wizard form view has multi-state visibility and action buttons | VERIFIED | import_wizard_form.xml.j2: three groups with `invisible="state != 'upload/preview/done'"` (lines 11-25), footer buttons for Preview/Import/Export All/Close (lines 27-42) |
| 8 | external_dependencies includes openpyxl and import wizard gets ACL entry | VERIFIED | renderer.py line 1461-1462 adds `external_dependencies: {python: [openpyxl]}`; manifest.py.j2 lines 25-35 render external_dependencies; access_csv.j2 lines 10-12 loop over import_export_wizards with ACL entries |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/src/odoo_gen_utils/templates/shared/controller.py.j2` | HTTP controller class template | VERIFIED | 29 lines, @http.route loop, JSON error handling, secure defaults |
| `python/src/odoo_gen_utils/templates/shared/init_controllers.py.j2` | controllers/__init__.py template | VERIFIED | 2 lines, `from . import main` |
| `python/src/odoo_gen_utils/templates/shared/init_root.py.j2` | Root init with conditional controllers import | VERIFIED | 8 lines, has_wizards + has_controllers conditionals |
| `python/src/odoo_gen_utils/templates/shared/import_wizard.py.j2` | TransientModel import/export wizard | VERIFIED | 153 lines, Binary upload, magic bytes, preview, batch import, xlsx export |
| `python/src/odoo_gen_utils/templates/shared/import_wizard_form.xml.j2` | Wizard form view with state groups | VERIFIED | 57 lines, 3 state groups, action buttons, act_window |
| `python/src/odoo_gen_utils/renderer.py` | render_controllers() + _build_module_context enrichment | VERIFIED | Lines 1301-1401 (render_controllers), lines 1429-1462 (context enrichment) |
| `python/src/odoo_gen_utils/templates/shared/manifest.py.j2` | external_dependencies support | VERIFIED | Lines 25-35 render external_dependencies conditionally |
| `python/src/odoo_gen_utils/templates/shared/access_csv.j2` | Import wizard ACL entries | VERIFIED | Lines 10-12 loop over import_export_wizards |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| renderer.py::render_controllers() | controller.py.j2 | render_template call | WIRED | Line 1336-1340: `render_template(env, "controller.py.j2", ...)` |
| renderer.py::render_controllers() | init_controllers.py.j2 | render_template call | WIRED | Line 1331-1335: `render_template(env, "init_controllers.py.j2", ...)` |
| renderer.py::render_controllers() | import_wizard.py.j2 | render_template call | WIRED | Line 1374-1378: `render_template(env, "import_wizard.py.j2", ...)` |
| renderer.py::render_controllers() | import_wizard_form.xml.j2 | render_template call | WIRED | Line 1379-1383: `render_template(env, "import_wizard_form.xml.j2", ...)` |
| renderer.py::_build_module_context() | manifest.py.j2 | has_controllers, external_dependencies | WIRED | Lines 1457-1462 set has_controllers, has_import_export, external_dependencies |
| renderer.py::_build_module_context() | access_csv.j2 | import_export_wizards list | WIRED | Line 1436-1438 builds import_export_wizards, line 1459 passes to context |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TMPL-03 | 32-01 | HTTP controllers with @http.route, auth, CSRF, input validation | SATISFIED | controller.py.j2 with secure defaults, render_controllers() implementation, 11 controller tests pass |
| TMPL-04 | 32-02 | Import/export TransientModel wizards with Binary upload, validation, preview, batch import, xlsx export | SATISFIED | import_wizard.py.j2 with full state machine, magic byte validation, openpyxl export; 16 import/export tests pass |

No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| controller.py.j2 | 20, 25 | `# TODO: implement {{ route.method_name }} logic` | Info | Expected -- these are in generated output as developer guidance, not in generator code itself |
| import_wizard.py.j2 | 108 | `TODO: implement field mapping for {{ model_name }}` | Info | Expected -- _parse_row is a stub for users to customize; basic dict(zip(headers, row)) fallback is provided |

No blocker or warning anti-patterns found. The TODOs are in Jinja2 templates that produce generated code -- they are intentional developer guidance comments in the output module, not incomplete generator code.

### Human Verification Required

### 1. Visual Form States

**Test:** Generate a module with `import_export: true` on a model, install in Odoo, open the import wizard
**Expected:** Form shows upload state initially, transitions to preview after file upload, then to done after import
**Why human:** State-dependent visibility and form layout require visual inspection in Odoo web client

### 2. Actual xlsx Import/Export

**Test:** Upload a real .xlsx file through the wizard, verify preview table renders, import creates records, export downloads valid .xlsx
**Expected:** Full round-trip: upload -> preview HTML table -> import records -> export downloads file
**Why human:** File I/O, openpyxl behavior, and Odoo record creation require live Odoo instance

### Gaps Summary

No gaps found. All 8 observable truths verified. All artifacts exist, are substantive, and are properly wired. Both requirements (TMPL-03, TMPL-04) are satisfied. Test suite passes with 711 tests, 9 skipped, 0 failures (excluding Docker-related test_dev_instance.py which has a pre-existing Docker error unrelated to this phase).

---

_Verified: 2026-03-06T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
