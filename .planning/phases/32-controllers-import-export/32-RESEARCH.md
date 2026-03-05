# Phase 32: Controllers & Import/Export - Research

**Researched:** 2026-03-06
**Domain:** Odoo HTTP controller generation + import/export TransientModel wizard generation
**Confidence:** HIGH

## Summary

Phase 32 implements two features in the existing `render_controllers` placeholder stage: (1) HTTP controller generation with `@http.route` decorators, `controllers/main.py`, and `controllers/__init__.py` with proper root `__init__.py` import; and (2) import/export TransientModel wizards with `fields.Binary` file upload, content-type validation (magic bytes, not just extension), row-by-row validation with preview step, batch `_do_import()` processing, and xlsx export via openpyxl.

The codebase already has a wired `render_controllers()` placeholder returning `Result.ok([])` (stage 10 of 10 in `render_module()`). The existing patterns from `render_wizards` (TransientModel + form XML) and `render_reports` (template + context enrichment) provide clear blueprints. The `init_root.py.j2` template already conditionally imports `wizards`; it needs extension to conditionally import `controllers`. The `_build_module_context()` needs controller files in the manifest, and `_build_model_context()` needs `import_export` awareness.

For controllers, Odoo 17 uses `odoo.http.Controller` base class with `@http.route()` decorator. Key parameters are `type` (json/http), `auth` (user/public/none), `csrf` (True/False), and `methods`. The generator should default to `auth='user'` and `csrf=True` for security. JSON routes need try/except with proper error responses.

For import/export, the pattern is a TransientModel with `fields.Binary` for upload, `base64.b64decode()` + `io.BytesIO()` + `openpyxl.load_workbook()` for parsing, and `openpyxl.Workbook()` + `base64.b64encode()` for export. Content-type validation uses magic bytes (first 4 bytes of decoded file) to detect xlsx format (PK signature: `50 4B 03 04`) vs CSV. Note: openpyxl is a runtime dependency of the generated module, NOT of odoo-gen-utils itself (per REQUIREMENTS.md "Out of Scope").

**Primary recommendation:** Create 4 new Jinja2 templates (`controller.py.j2`, `init_controllers.py.j2`, `import_wizard.py.j2`, `import_wizard_form.xml.j2`) in `templates/shared/`, implement `render_controllers()` to produce controller files + import/export wizard files, extend `_build_module_context()` for manifest, modify `init_root.py.j2` to import controllers, and add export action to the import wizard form view.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TMPL-03 | Generator produces HTTP controllers (`controllers/main.py`) with `@http.route`, JSON/HTTP types, authentication modes, CSRF protection, and input validation | Controller template with `@http.route` decorator, secure defaults (auth='user', csrf=True), JSON error handling pattern, `controllers/__init__.py` + root import |
| TMPL-04 | Generator produces import/export TransientModel wizards with `fields.Binary` upload, row validation, preview step, batch `_do_import()`, and xlsx export | Import wizard TransientModel template with Binary field, base64 decode + openpyxl pattern, magic byte content-type validation, preview state, batch processing, xlsx export method |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | (existing) | Template rendering for controller/wizard Python and XML | Already in use for all generation |
| Python 3.12 | (existing) | Render stage logic in renderer.py | Already in use |

### Supporting (in generated modules, NOT in odoo-gen-utils)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openpyxl | 3.1+ | Read/write xlsx files in generated import/export wizard | Only in generated module's runtime deps; referenced in generated code, not imported by generator |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openpyxl for xlsx | xlsxwriter for export + openpyxl for import | xlsxwriter is write-only, openpyxl handles both; single dependency is cleaner |
| Magic bytes for content validation | python-magic library | Magic bytes check for xlsx (PK signature) is simple enough; python-magic adds OS-level libmagic dependency |
| Single controller.py template | Separate templates per route type | Single template with loop is consistent with existing patterns |

**Installation:**
No new packages needed for odoo-gen-utils. Generated modules will need `openpyxl` in their Python environment (Odoo servers typically have it installed already).

## Architecture Patterns

### Recommended Project Structure

New/modified files:
```
python/src/odoo_gen_utils/
  renderer.py                                    # render_controllers() implementation + context enrichment
  templates/shared/
    controller.py.j2                             # NEW: HTTP controller with @http.route
    init_controllers.py.j2                       # NEW: controllers/__init__.py
    import_wizard.py.j2                          # NEW: import/export TransientModel
    import_wizard_form.xml.j2                    # NEW: import wizard form view + export button
  templates/17.0/
    (no changes)
  templates/18.0/
    (no changes)
```

Modified existing files:
```
  templates/shared/init_root.py.j2               # MODIFIED: add `from . import controllers` conditional
```

### Pattern 1: Odoo 17 HTTP Controller Structure

**What:** The standard file layout for HTTP controllers in an Odoo module.
**When to use:** When `spec.controllers` is non-empty.

```
module_name/
  __init__.py              # from . import controllers
  controllers/
    __init__.py            # from . import main
    main.py                # Controller class with @http.route methods
```

### Pattern 2: Controller Class with @http.route

**What:** The standard Odoo controller class pattern.
**When to use:** In `controller.py.j2` template.

```python
# Source: Odoo 17.0 Web Controllers documentation
from odoo import http
from odoo.http import request


class {{ controller_class }}(http.Controller):

    @http.route('/{{ module_name }}/{{ route.path }}',
                type='{{ route.type | default("http") }}',
                auth='{{ route.auth | default("user") }}',
                csrf={{ route.csrf | default(True) }},
                methods={{ route.methods | default(["GET"]) }})
    def {{ route.method_name }}(self, **kw):
        """{{ route.description | default('') }}"""
        # ...
```

**Key defaults (secure by default):**
- `auth='user'`: Requires authenticated user (not public)
- `csrf=True`: CSRF protection enabled
- `type='http'`: Standard HTTP request (not JSON-RPC)
- `methods=['GET']`: Explicit method restriction

### Pattern 3: JSON Route with Error Handling

**What:** The proper error handling pattern for JSON-type controller routes.
**When to use:** When `route.type == 'json'`.

```python
# Source: Odoo forum + official docs
@http.route('/api/{{ module_name }}/{{ route.path }}',
            type='json', auth='user', csrf=True, methods=['POST'])
def {{ route.method_name }}(self, **kw):
    """{{ route.description }}."""
    try:
        # Business logic here
        return {'status': 'success', 'data': result}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
```

**Notes:**
- JSON routes receive/return JSON-RPC format
- `request.jsonrequest` contains the parsed JSON body
- Return value is auto-serialized to JSON-RPC response
- Exceptions in JSON routes return JSON error responses (Odoo handles this)
- Explicit try/except provides structured error messages

### Pattern 4: Import Wizard TransientModel

**What:** Complete import wizard with file upload, content validation, preview, and batch processing.
**When to use:** When `model.import_export` is `true` in spec.

```python
# Source: Cybrosys + Numla patterns, verified against Odoo 17
import base64
import io
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class {{ model_class }}ImportWizard(models.TransientModel):
    _name = '{{ model_name }}.import.wizard'
    _description = 'Import {{ model_description }}'

    state = fields.Selection([
        ('upload', 'Upload'),
        ('preview', 'Preview'),
        ('done', 'Done'),
    ], default='upload', readonly=True)

    file_data = fields.Binary(string='File', required=True)
    file_name = fields.Char(string='File Name')
    preview_html = fields.Html(string='Preview', readonly=True)
    import_count = fields.Integer(string='Records Imported', readonly=True)
    error_log = fields.Text(string='Errors', readonly=True)

    def _validate_file_content(self):
        """Validate file content type via magic bytes, not just extension."""
        self.ensure_one()
        if not self.file_data:
            raise UserError("Please upload a file.")
        raw = base64.b64decode(self.file_data)
        # XLSX files are ZIP archives: magic bytes PK\x03\x04
        if raw[:4] != b'PK\x03\x04':
            raise ValidationError(
                "Invalid file format. Please upload a valid .xlsx file."
            )
        return raw

    def action_preview(self):
        """Parse file and show preview of first N rows."""
        self.ensure_one()
        raw = self._validate_file_content()
        import openpyxl
        wb = openpyxl.load_workbook(filename=io.BytesIO(raw), read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(max_row=6, values_only=True))
        # Build preview HTML table
        html = '<table class="table table-sm">'
        if rows:
            html += '<thead><tr>' + ''.join(f'<th>{c or ""}</th>' for c in rows[0]) + '</tr></thead>'
            html += '<tbody>'
            for row in rows[1:]:
                html += '<tr>' + ''.join(f'<td>{c or ""}</td>' for c in row) + '</tr>'
            html += '</tbody>'
        html += '</table>'
        self.write({'state': 'preview', 'preview_html': html})
        return self._reopen_wizard()

    def action_import(self):
        """Validate rows and batch-import records."""
        self.ensure_one()
        raw = self._validate_file_content()
        import openpyxl
        wb = openpyxl.load_workbook(filename=io.BytesIO(raw), read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        errors, imported = self._do_import(rows)
        vals = {
            'state': 'done',
            'import_count': imported,
        }
        if errors:
            vals['error_log'] = '\n'.join(errors)
        self.write(vals)
        return self._reopen_wizard()

    def _do_import(self, rows):
        """Batch-process import rows with per-row validation.

        Returns (error_messages: list[str], success_count: int).
        """
        errors = []
        created = 0
        for idx, row in enumerate(rows, start=2):
            try:
                vals = self._parse_row(row)
                if vals:
                    self.env['{{ model_name }}'].create(vals)
                    created += 1
            except (ValidationError, ValueError) as exc:
                errors.append(f"Row {idx}: {exc}")
        return errors, created

    def _parse_row(self, row):
        """Parse a single spreadsheet row into a create vals dict.

        Override this method to customize field mapping.
        Returns dict or None to skip row.
        """
        # TODO: implement field mapping for {{ model_name }}
        return {}

    def _reopen_wizard(self):
        """Return action to re-display this wizard in its current state."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
```

### Pattern 5: Export Action (xlsx output)

**What:** Method on the import wizard that generates xlsx output for download.
**When to use:** When `import_export: true` -- the same wizard handles both directions.

```python
def action_export(self):
    """Export records to xlsx and trigger download."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '{{ model_description }}'

    # Header row
    headers = [{{ export_headers }}]
    ws.append(headers)

    # Data rows
    records = self.env['{{ model_name }}'].search([])
    for rec in records:
        ws.append([{{ export_field_access }}])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    self.write({
        'file_data': base64.b64encode(output.read()),
        'file_name': '{{ model_var }}_export.xlsx',
    })
    return {
        'type': 'ir.actions.act_url',
        'url': f'/web/content?model={self._name}&id={self.id}'
               f'&field=file_data&filename_field=file_name&download=true',
        'target': 'new',
    }
```

### Pattern 6: Import Wizard Form View (multi-state)

**What:** A wizard form view with state-dependent visibility for upload/preview/done steps.
**When to use:** For each model with `import_export: true`.

```xml
<record id="view_{{ model_xml_id }}_import_wizard_form" model="ir.ui.view">
    <field name="name">{{ model_name }}.import.wizard.form</field>
    <field name="model">{{ model_name }}.import.wizard</field>
    <field name="arch" type="xml">
        <form string="Import {{ model_description }}">
            <field name="state" invisible="1"/>
            <group invisible="state != 'upload'">
                <field name="file_data" filename="file_name"/>
                <field name="file_name" invisible="1"/>
            </group>
            <group invisible="state != 'preview'">
                <field name="preview_html" nolabel="1"/>
            </group>
            <group invisible="state != 'done'">
                <field name="import_count"/>
                <field name="error_log" invisible="not error_log"/>
            </group>
            <footer>
                <button name="action_preview" string="Preview"
                        type="object" class="btn-primary"
                        invisible="state != 'upload'"/>
                <button name="action_import" string="Import"
                        type="object" class="btn-primary"
                        invisible="state != 'preview'"/>
                <button name="action_export" string="Export All"
                        type="object" class="btn-secondary"/>
                <button string="Close" class="btn-secondary" special="cancel"/>
            </footer>
        </form>
    </field>
</record>

<record id="action_{{ model_xml_id }}_import_wizard" model="ir.actions.act_window">
    <field name="name">Import/Export {{ model_description }}</field>
    <field name="res_model">{{ model_name }}.import.wizard</field>
    <field name="view_mode">form</field>
    <field name="target">new</field>
</record>
```

### Pattern 7: init_root.py.j2 Extension

**What:** Root `__init__.py` must import the `controllers` package.
**When to use:** When spec has controllers or import_export models.

```jinja2
{# init_root.py.j2 -- Root __init__.py importing subpackages #}
from . import models
{% if has_wizards %}
from . import wizards
{% endif %}
{% if has_controllers %}
from . import controllers
{% endif %}
```

### Pattern 8: Controller Spec Schema

**What:** Expected structure of `spec.controllers` entries.
**When to use:** As the contract between spec input and template rendering.

```python
# Each spec["controllers"] entry:
{
    "name": "Main Controller",           # Human-readable name
    "class_name": "AcademyController",   # Optional; auto-derived from module_name if omitted
    "routes": [
        {
            "path": "courses",                    # URL path segment (prefixed by /module_name/)
            "method_name": "get_courses",         # Python method name
            "type": "json",                       # "json" or "http" (default: "http")
            "auth": "user",                       # "user", "public", "none" (default: "user")
            "csrf": True,                         # True/False (default: True)
            "methods": ["GET"],                   # HTTP methods (default: ["GET"])
            "description": "List all courses",    # Docstring
        },
        {
            "path": "course/<int:course_id>",
            "method_name": "get_course_detail",
            "type": "http",
            "auth": "user",
            "methods": ["GET"],
        },
    ],
}
```

### Anti-Patterns to Avoid

- **Using `auth='public'` by default:** Secure default is `auth='user'`. Public routes should be opt-in.
- **Setting `csrf=False` by default:** CSRF protection should be on by default. Only disable for external API endpoints.
- **Omitting `methods` parameter:** Without explicit methods, all HTTP methods are accepted. Always restrict to what is needed.
- **Bare except in JSON routes:** Use specific exception types (ValidationError, UserError, AccessDenied) for structured error messages.
- **Importing openpyxl at module top level:** Import inside methods to avoid ImportError when openpyxl is not installed (graceful degradation).
- **Mutating spec to add import wizards:** Follow the immutable pattern -- derive import wizard context from spec, do not modify the spec dict.
- **Validating file extension instead of content:** Extension can be spoofed. Always check magic bytes for xlsx (PK\x03\x04 signature).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Controller class structure | Custom routing | `odoo.http.Controller` + `@http.route` | Odoo's routing framework handles URL dispatch, auth, CSRF |
| File download response | Custom HTTP response | `request.make_response()` or `/web/content` URL | Odoo handles content disposition, streaming, auth |
| XLSX parsing | CSV-based workaround | `openpyxl.load_workbook()` | Handles all xlsx edge cases (merged cells, types, dates) |
| XLSX generation | String-based XML | `openpyxl.Workbook()` | Proper xlsx format, handles styles, large datasets |
| File content validation | Extension check only | Magic byte signature check | PK\x03\x04 for xlsx is reliable; extensions can be spoofed |
| Wizard state machine | Custom state tracking | `fields.Selection` state + `invisible` attrs | Standard Odoo wizard pattern, well-understood |

**Key insight:** Controllers follow a strictly declarative pattern (decorator parameters define behavior). Import/export wizards combine two well-known Odoo patterns (TransientModel + binary file handling) with openpyxl. The generator produces scaffolding code with TODO markers for business-specific logic.

## Common Pitfalls

### Pitfall 1: Missing controllers/__init__.py
**What goes wrong:** Module fails to load controllers -- no routes registered.
**Why it happens:** `controllers/` directory exists but `__init__.py` is missing or root `__init__.py` does not import `controllers`.
**How to avoid:** Generate both `controllers/__init__.py` (importing main) AND modify `init_root.py.j2` to `from . import controllers`. Pass `has_controllers` flag in module context.
**Warning signs:** Routes return 404 despite controller file existing.

### Pitfall 2: CSRF Token Missing on HTTP Forms
**What goes wrong:** POST requests to `type='http'` routes fail with 400 Bad Request.
**Why it happens:** `csrf=True` (default) requires a CSRF token in POST forms, but external callers do not have one.
**How to avoid:** For internal form routes, Odoo templates automatically include CSRF tokens. For external API routes, set `csrf=False` explicitly and document it in the route.
**Warning signs:** "Session expired" or "Invalid CSRF token" errors on POST.

### Pitfall 3: JSON Route Returns HTML Error
**What goes wrong:** JSON route exceptions return HTML error page instead of JSON response.
**Why it happens:** Uncaught exceptions in `type='json'` routes are handled by Odoo's generic error handler.
**How to avoid:** Wrap JSON route logic in try/except and return structured `{'status': 'error', 'message': str(e)}` dict. Odoo serializes the return value as JSON-RPC response.
**Warning signs:** JavaScript frontend receives HTML instead of JSON, causing parse errors.

### Pitfall 4: openpyxl Not Available at Runtime
**What goes wrong:** ImportError when user clicks Import button in generated module.
**Why it happens:** openpyxl is not installed in the Odoo server's Python environment.
**How to avoid:** Template should add `openpyxl` to the module's `external_dependencies` in `__manifest__.py` under `{'python': ['openpyxl']}`. Also, import openpyxl inside methods, not at module top level.
**Warning signs:** `ModuleNotFoundError: No module named 'openpyxl'` at runtime.

### Pitfall 5: Import Wizard Not in Security ACL
**What goes wrong:** Users get AccessError when opening the import wizard.
**Why it happens:** The TransientModel has no ir.model.access entry in the CSV.
**How to avoid:** Add ACL entry for `model_{{ model_name }}_import_wizard` in the security CSV generation. Follow the same pattern used for existing wizards in `render_security()`.
**Warning signs:** "You are not allowed to access this resource" when clicking Import button.

### Pitfall 6: File Content Validation Bypass via Extension
**What goes wrong:** User uploads a .xlsx-named file that is actually a malicious/corrupt file.
**Why it happens:** Only checking file extension, not actual content.
**How to avoid:** Validate magic bytes: xlsx files are ZIP archives starting with `PK\x03\x04` (hex `50 4B 03 04`). Reject files that do not match.
**Warning signs:** openpyxl crashes with `BadZipFile` or `InvalidFileException`.

### Pitfall 7: Large File Import Without Batching
**What goes wrong:** Import of large xlsx (10K+ rows) causes timeout or memory issues.
**Why it happens:** All rows processed in a single transaction.
**How to avoid:** The `_do_import()` method should use batch creation where possible. The template generates a per-row create pattern with error collection, which is safe but slower. For large imports, users can override `_do_import()` to batch.
**Warning signs:** HTTP timeout, "lock timeout" errors in PostgreSQL.

### Pitfall 8: Manifest Missing external_dependencies
**What goes wrong:** Module installs but crashes when import wizard is used.
**Why it happens:** `openpyxl` dependency not declared in manifest.
**How to avoid:** When any model has `import_export: true`, add `'external_dependencies': {'python': ['openpyxl']}` to the manifest template context.
**Warning signs:** ModuleNotFoundError at wizard runtime, not at install time.

## Code Examples

### Controller Template (controller.py.j2)

```jinja2
{# controller.py.j2 -- Odoo HTTP controller #}
from odoo import http
from odoo.http import request


class {{ controller_class }}(http.Controller):
{% for route in routes %}

    @http.route(
        '/{{ module_name }}/{{ route.path }}',
        type='{{ route.type | default("http") }}',
        auth='{{ route.auth | default("user") }}',
        csrf={{ route.csrf | default(True) }},
        methods={{ route.methods | default(["GET"]) }},
    )
    def {{ route.method_name }}(self, **kw):
        """{{ route.description | default(route.method_name | replace('_', ' ') | title) }}."""
{% if route.type | default("http") == "json" %}
        try:
            # TODO: implement {{ route.method_name }} logic
            return {'status': 'success', 'data': {}}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
{% else %}
        # TODO: implement {{ route.method_name }} logic
        return request.render('{{ module_name }}.template_name', {})
{% endif %}
{% endfor %}
```

### Controllers __init__.py Template (init_controllers.py.j2)

```jinja2
{# init_controllers.py.j2 -- Controllers package __init__.py #}
from . import main
```

### Import Wizard Template Key Sections

```jinja2
{# import_wizard.py.j2 key section: content type validation #}
    def _validate_file_content(self):
        """Validate file content type via magic bytes, not just extension."""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Please upload a file."))
        raw = base64.b64decode(self.file_data)
        # XLSX magic bytes: PK\x03\x04 (ZIP archive)
        if raw[:4] != b'PK\x03\x04':
            raise ValidationError(
                _("Invalid file format. Please upload a valid .xlsx file.")
            )
        return raw
```

### Manifest external_dependencies Extension

```python
# In _build_module_context() or manifest template:
# When any model has import_export, add external_dependencies
has_import_export = any(
    m.get("import_export") for m in spec.get("models", [])
)
if has_import_export:
    external_deps = {"python": ["openpyxl"]}
```

### Sample Spec with Controllers and Import/Export

```json
{
    "module_name": "academy",
    "models": [
        {
            "name": "academy.course",
            "import_export": true,
            "fields": [
                {"name": "name", "type": "Char", "required": true},
                {"name": "code", "type": "Char", "required": true},
                {"name": "credits", "type": "Integer"}
            ]
        }
    ],
    "controllers": [
        {
            "name": "Academy API",
            "routes": [
                {
                    "path": "api/courses",
                    "method_name": "api_list_courses",
                    "type": "json",
                    "auth": "user",
                    "methods": ["POST"],
                    "description": "List all active courses"
                },
                {
                    "path": "courses",
                    "method_name": "page_courses",
                    "type": "http",
                    "auth": "public",
                    "methods": ["GET"],
                    "description": "Public course listing page"
                }
            ]
        }
    ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `openerp.http.Controller` | `odoo.http.Controller` | Odoo 10+ | Namespace change |
| CSRF disabled by default | CSRF enabled by default for HTTP routes | Odoo 10+ | Security improvement |
| xlrd for xlsx reading | openpyxl for xlsx | xlrd 2.0+ dropped xlsx | xlrd only supports xls now |
| `attrs="{'invisible': ...}"` in views | `invisible="condition"` in Odoo 17+ | Odoo 17 | Simplified visibility syntax |
| Manual file download via controller | `/web/content` URL pattern | Odoo 14+ | Standard download mechanism |

**Deprecated/outdated:**
- `xlrd` for xlsx files: xlrd 2.0 dropped xlsx support; use openpyxl
- `openerp.http`: Replaced by `odoo.http` since Odoo 10
- `attrs=` dict syntax for visibility: Odoo 17+ uses inline expressions

## Open Questions

1. **Should import/export wizards be in `wizards/` directory alongside existing wizards?**
   - What we know: Existing wizards go to `wizards/`. Import wizards are also TransientModels.
   - Recommendation: Yes, place import wizards in `wizards/` directory for consistency. They follow the exact same TransientModel pattern. The `init_wizards.py.j2` needs to be extended to import them.

2. **How should export field mapping be determined?**
   - What we know: The import wizard's `_parse_row()` is a stub. The export needs field names.
   - Recommendation: Use all non-internal, non-relational fields from the model definition. The template generates header names from field labels and field access from field names. This provides a reasonable default that users can customize.

3. **Should the controller template support route inheritance (extending existing controllers)?**
   - What we know: Odoo supports controller inheritance via `class MyController(ExistingController)`.
   - Recommendation: Out of scope for Phase 32. The generated controller is standalone. Controller inheritance is a complex pattern best handled manually.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `python/pyproject.toml` |
| Quick run command | `cd python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q` |
| Full suite command | `cd python && .venv/bin/python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMPL-03a | Spec with controllers generates controllers/main.py with @http.route | integration | `pytest tests/test_render_stages.py::TestRenderControllers::test_controller_generates_main_py -x` | Wave 0 |
| TMPL-03b | Generated controllers have auth='user' and csrf=True defaults | unit | `pytest tests/test_render_stages.py::TestRenderControllers::test_controller_secure_defaults -x` | Wave 0 |
| TMPL-03c | JSON routes include try/except error handling | unit | `pytest tests/test_render_stages.py::TestRenderControllers::test_json_route_error_handling -x` | Wave 0 |
| TMPL-03d | controllers/__init__.py generated and imports main | unit | `pytest tests/test_render_stages.py::TestRenderControllers::test_controllers_init -x` | Wave 0 |
| TMPL-03e | Root __init__.py imports controllers package | integration | `pytest tests/test_render_stages.py::TestRenderControllers::test_root_init_imports_controllers -x` | Wave 0 |
| TMPL-03f | Controller files in manifest data | unit | `pytest tests/test_renderer.py::TestBuildModuleContextControllers -x` | Wave 0 |
| TMPL-03g | No controllers: render_controllers returns Result.ok([]) | unit | `pytest tests/test_render_stages.py::TestRenderControllers::test_no_controllers_noop -x` | Wave 0 |
| TMPL-04a | Spec with import_export generates TransientModel wizard | integration | `pytest tests/test_render_stages.py::TestRenderImportExport::test_import_wizard_generated -x` | Wave 0 |
| TMPL-04b | Import wizard has Binary upload field + state machine | unit | `pytest tests/test_render_stages.py::TestRenderImportExport::test_import_wizard_fields -x` | Wave 0 |
| TMPL-04c | Import wizard validates file content type (magic bytes) | unit | `pytest tests/test_render_stages.py::TestRenderImportExport::test_content_type_validation -x` | Wave 0 |
| TMPL-04d | Import wizard has preview step and _do_import batch method | unit | `pytest tests/test_render_stages.py::TestRenderImportExport::test_preview_and_batch_import -x` | Wave 0 |
| TMPL-04e | Export action generates xlsx output | unit | `pytest tests/test_render_stages.py::TestRenderImportExport::test_export_xlsx -x` | Wave 0 |
| TMPL-04f | Import wizard form view has multi-state visibility | unit | `pytest tests/test_render_stages.py::TestRenderImportExport::test_wizard_form_states -x` | Wave 0 |
| TMPL-04g | external_dependencies includes openpyxl when import_export | unit | `pytest tests/test_renderer.py::TestBuildModuleContextImportExport -x` | Wave 0 |
| TMPL-04h | Import wizard ACL entry generated | unit | `pytest tests/test_render_stages.py::TestRenderImportExport::test_import_wizard_security -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q`
- **Per wave merge:** `cd python && .venv/bin/python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green (719+ tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `python/src/odoo_gen_utils/templates/shared/controller.py.j2` -- controller template
- [ ] `python/src/odoo_gen_utils/templates/shared/init_controllers.py.j2` -- controllers __init__.py
- [ ] `python/src/odoo_gen_utils/templates/shared/import_wizard.py.j2` -- import/export TransientModel
- [ ] `python/src/odoo_gen_utils/templates/shared/import_wizard_form.xml.j2` -- wizard form + action
- [ ] `tests/test_render_stages.py::TestRenderControllers` -- controller generation tests
- [ ] `tests/test_render_stages.py::TestRenderImportExport` -- import/export wizard tests
- [ ] `tests/test_renderer.py::TestBuildModuleContextControllers` -- manifest includes controller info
- [ ] `tests/test_renderer.py::TestBuildModuleContextImportExport` -- external_dependencies + wizard files
- [ ] Modified `templates/shared/init_root.py.j2` -- add controllers import

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `renderer.py` (1445 lines, 10 render stages, `render_controllers()` placeholder at line 1301)
- Codebase analysis: `init_root.py.j2` (conditional `from . import wizards`, needs `controllers`)
- Codebase analysis: `wizard.py.j2` (TransientModel template pattern)
- Codebase analysis: `_build_module_context()`, `_build_model_context()`, `_compute_manifest_data()` (context enrichment patterns)
- Codebase analysis: `render_wizards()` (wizard generation pattern: __init__.py + per-wizard .py + form XML)
- [Odoo 17.0 Web Controllers documentation](https://www.odoo.com/documentation/17.0/developer/reference/backend/http.html) -- @http.route parameters, auth modes, CSRF

### Secondary (MEDIUM confidence)
- [Numla: Custom XLSX Import Wizard in Odoo](https://numla.com/blog/odoo-development-18/creating-custom-xlsx-import-wizard-in-odoo-286) -- TransientModel import pattern with openpyxl
- [Cybrosys: Import XLSX Files in Odoo Using Openpyxl](https://www.cybrosys.com/blog/import-xlsx-files-in-odoo-using-openpyxl) -- base64 decode + load_workbook pattern
- [Transines: Generate XLSX Report Using Controller in Odoo 18](https://transines.com/how-generate-xlsx-report/) -- Export pattern with controller download
- [OCA Discussion #154](https://github.com/orgs/OCA/discussions/154) -- Export to XLS/XLSX without DB persistence pattern

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies for odoo-gen-utils; openpyxl is standard in Odoo ecosystem
- Architecture: HIGH -- follows exact existing render stage and wizard patterns; placeholder already wired
- Pitfalls: HIGH -- 8 pitfalls identified from official docs, forum posts, and codebase analysis
- Controller pattern: HIGH -- Odoo controller API is stable and well-documented since Odoo 10+
- Import/export pattern: HIGH -- TransientModel + openpyxl is the de facto standard in Odoo community

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable domain; controller API unchanged since Odoo 10, openpyxl pattern standard)
