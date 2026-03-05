# Phase 30: Scheduled Actions & Render Pipeline - Research

**Researched:** 2026-03-05
**Domain:** Odoo ir.cron XML generation + renderer pipeline stage wiring
**Confidence:** HIGH

## Summary

Phase 30 has two distinct goals: (1) generate `ir.cron` XML records from a `cron_jobs` spec section with corresponding `@api.model` stub methods on target models, and (2) wire three new render stages (`render_cron`, `render_reports`, `render_controllers`) into the existing renderer pipeline. The cron generation is the substantive feature work; the render stage wiring is pipeline plumbing that prepares slots for Phases 31 and 32.

The codebase already has a well-established pattern for render stages -- 7 existing stages in `render_module()`, each accepting `(env, spec, module_dir, module_context)` and returning `Result[list[Path]]`. Adding 3 more stages follows the exact same pattern. The `data/data.xml` file is currently a static stub; this phase replaces it with templated content when `cron_jobs` are present.

The Odoo 17+ `ir.cron` format uses `model_id` (ref to model XML ID), `state` set to `"code"`, and `code` containing a `model.method_name()` call. The old `model`/`function` format is deprecated. Generated crons must be inside `<odoo noupdate="1">` to prevent overwrite on module upgrade.

**Primary recommendation:** Add a `cron_data.xml.j2` template in `shared/`, a `render_cron` stage function, two no-op placeholder stages (`render_reports`, `render_controllers`), inject `@api.model` stub methods into model context, and wire all three into the `render_module()` pipeline after `render_static`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TMPL-05 | Generator produces `ir.cron` XML records in `data/data.xml` with interval, model reference, and `@api.model` stub method on target model | Cron XML template pattern, model context enrichment for cron methods, `_build_model_context()` extension |
| TMPL-06 | New render stages (`render_reports`, `render_controllers`, `render_cron`) wired into renderer pipeline returning `Result[list[Path]]` | Pipeline stage pattern documented, 3 new functions follow existing `render_wizards`/`render_tests` signatures |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | (existing) | Template rendering for cron XML | Already in use, no changes needed |
| Python 3.12 | (existing) | Render stage functions in renderer.py | Already in use |

### Supporting
No new libraries needed. This is pure logic + template + pipeline wiring.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 template for cron XML | String concatenation in Python | Template is cleaner, consistent with all other XML generation in the project |
| Separate `data/cron_data.xml` file | Append to existing `data/data.xml` | Separate file is cleaner for manifest ordering; Odoo loads files in manifest order so cron data must come after model registration |

**Installation:**
No new packages needed.

## Architecture Patterns

### Recommended Project Structure

No new directories. New/modified files:
```
python/src/odoo_gen_utils/
  renderer.py                          # +3 render stage functions, cron context enrichment
  templates/shared/
    cron_data.xml.j2                   # NEW: ir.cron XML template
```

### Pattern 1: Render Stage Function Signature

**What:** Every render stage follows the same signature and return type.
**When to use:** For all 3 new stages.

```python
# Source: Existing pattern from render_views(), render_wizards(), render_tests()
def render_cron(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render ir.cron data XML for scheduled actions.

    Returns Result.ok([]) when no cron_jobs in spec (no-op).
    """
    try:
        cron_jobs = spec.get("cron_jobs", [])
        if not cron_jobs:
            return Result.ok([])
        created: list[Path] = []
        # ... template rendering ...
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_cron failed: {exc}")
```

### Pattern 2: Odoo 17 ir.cron XML Record

**What:** The standard XML format for scheduled actions in Odoo 17+.
**When to use:** In the `cron_data.xml.j2` template.

```xml
<!-- Source: Odoo 17 official pattern, verified via multiple sources -->
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">

    <record id="cron_{{ module_name }}_{{ cron.method }}" model="ir.cron">
        <field name="name">{{ cron.name }}</field>
        <field name="active" eval="True"/>
        <field name="user_id" ref="base.user_root"/>
        <field name="interval_number">{{ cron.interval_number }}</field>
        <field name="interval_type">{{ cron.interval_type }}</field>
        <field name="numbercall">-1</field>
        <field name="doall" eval="False"/>
        <field name="model_id" ref="model_{{ cron.model_name | to_xml_id }}"/>
        <field name="state">code</field>
        <field name="code">model.{{ cron.method }}()</field>
    </record>

</odoo>
```

**Key fields:**
- `noupdate="1"`: Prevents cron config from being overwritten on module upgrade
- `model_id ref="model_<xml_id>"`: Odoo auto-generates `ir.model` records with ID `model_<dotted_name_underscored>` for all models
- `state="code"` + `code="model.method()"`: Odoo 17+ pattern (not the deprecated `function`/`args` pattern)
- `numbercall=-1`: Unlimited executions
- `doall eval="False"`: **Critical** -- prevents server overload from running all missed executions on restart (requirement SC-3)

### Pattern 3: Cron Method Stub on Target Model

**What:** An `@api.model` method stub on the model referenced by the cron job.
**When to use:** In `_build_model_context()` to enrich the model with cron methods, and in `model.py.j2` to render the stub.

```python
# In _build_model_context():
# Find cron jobs targeting this model
cron_jobs = spec.get("cron_jobs", [])
cron_methods = [
    cron for cron in cron_jobs
    if cron.get("model_name") == model["name"]
]

# In model.py.j2:
# {% for cron in cron_methods %}
#
#     @api.model
#     def {{ cron.method }}(self):
#         """Scheduled action: {{ cron.name }}."""
#         # TODO: implement scheduled action logic
#         pass
# {% endfor %}
```

### Pattern 4: Placeholder Render Stages

**What:** No-op render stages that return `Result.ok([])` when their spec section is empty.
**When to use:** For `render_reports` and `render_controllers` which are wired now but implemented in Phases 31 and 32.

```python
def render_reports(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render QWeb report templates. Placeholder -- implemented in Phase 31."""
    return Result.ok([])


def render_controllers(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render HTTP controllers. Placeholder -- implemented in Phase 32."""
    return Result.ok([])
```

### Pattern 5: Pipeline Wiring in render_module()

**What:** Add 3 new stages to the `stages` list in `render_module()`.
**When to use:** After the existing 7 stages.

```python
# Current (7 stages):
stages = [
    lambda: render_manifest(env, spec, module_dir, ctx),
    lambda: render_models(...),
    lambda: render_views(...),
    lambda: render_security(...),
    lambda: render_wizards(...),
    lambda: render_tests(...),
    lambda: render_static(...),
]

# After (10 stages):
stages = [
    lambda: render_manifest(env, spec, module_dir, ctx),
    lambda: render_models(...),
    lambda: render_views(...),
    lambda: render_security(...),
    lambda: render_wizards(...),
    lambda: render_tests(...),
    lambda: render_static(...),
    lambda: render_cron(env, spec, module_dir, ctx),        # Phase 30
    lambda: render_reports(env, spec, module_dir, ctx),      # Phase 30 (placeholder)
    lambda: render_controllers(env, spec, module_dir, ctx),  # Phase 30 (placeholder)
]
```

### Pattern 6: Manifest Data Integration

**What:** When `cron_jobs` exist, `data/cron_data.xml` must appear in the manifest `data` list.
**When to use:** In `_build_module_context()` when constructing `data_files`.

```python
# In _build_module_context():
has_cron = bool(spec.get("cron_jobs"))
if has_cron:
    data_files.append("data/cron_data.xml")
```

### Pattern 7: Cron Spec Schema

**What:** The expected structure of each entry in `spec.cron_jobs`.
**When to use:** As the contract between spec input and template rendering.

```python
# Each cron_jobs entry:
{
    "name": "Archive Old Records",           # Human-readable name
    "model_name": "academy.course",          # Dotted Odoo model name
    "method": "_cron_archive_old_records",   # Method name (convention: _cron_ prefix)
    "interval_number": 1,                    # How often (number)
    "interval_type": "days",                 # Unit: minutes|hours|days|weeks|months
    "active": True,                          # Optional, defaults to True
}
```

### Anti-Patterns to Avoid
- **Using deprecated `function`/`args` format:** Odoo 17 uses `model_id` + `state` + `code`. The old `model` + `function` + `args` format still works but is deprecated and inconsistent with Odoo's own modules.
- **Setting `doall="True"`:** This causes ALL missed executions to run when the server restarts, potentially overloading the system. Default to `False` per requirement SC-3.
- **Omitting `noupdate="1"`:** Without this, every module upgrade resets the cron configuration, losing any user customizations (changed interval, deactivation, etc.).
- **Hardcoding model XML ID format:** Use the existing `_to_xml_id()` helper. The Odoo model XML ID format is `model_<dotted_name_with_dots_replaced_by_underscores>`.
- **Mutating model spec to add cron methods:** Follow the immutable pattern -- add `cron_methods` as a new key in `_build_model_context()` return dict, don't modify the model dict.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML generation | String concatenation | Jinja2 template (`cron_data.xml.j2`) | Consistent with all other XML in the project; handles escaping |
| Model XML ID | Custom ID logic | `_to_xml_id()` helper + `"model_"` prefix | Odoo's convention; already used elsewhere |
| Method name validation | Regex validator | Convention (`_cron_` prefix) + Python identifier check | Simple, follows Odoo patterns |

## Common Pitfalls

### Pitfall 1: model_id ref Must Match Auto-Generated ir.model ID
**What goes wrong:** `model_id ref="my_custom_id"` fails because Odoo auto-generates model IDs as `model_<name_underscored>`.
**Why it happens:** Developers use arbitrary XML IDs for the model reference.
**How to avoid:** Always use `model_<model_name | to_xml_id>` format. For `academy.course`, the ref is `model_academy_course`.
**Warning signs:** `ValueError: External ID not found in the system: module.model_xxx` during install.

### Pitfall 2: Cron Method Not on the Right Model
**What goes wrong:** The cron XML references `model.some_method()` but the method doesn't exist on the model class.
**Why it happens:** The cron method stub was not added to the correct model's template context.
**How to avoid:** In `_build_model_context()`, filter `spec["cron_jobs"]` by `cron["model_name"] == model["name"]` to get only the cron methods for the current model.
**Warning signs:** `AttributeError: 'academy.course' object has no attribute '_cron_archive'` at runtime.

### Pitfall 3: Missing `needs_api` Flag for @api.model
**What goes wrong:** Template renders `@api.model` but the `from odoo import api` import is missing.
**Why it happens:** `needs_api` flag in `_build_model_context()` doesn't account for cron methods.
**How to avoid:** Add `bool(cron_methods)` to the `needs_api` condition.
**Warning signs:** `NameError: name 'api' is not defined` in generated model.

### Pitfall 4: Cron Data File Not in Manifest
**What goes wrong:** Cron XML is generated but not loaded because it's not listed in `__manifest__.py["data"]`.
**Why it happens:** `_build_module_context()` doesn't add `data/cron_data.xml` to `data_files`.
**How to avoid:** Add conditional `data_files.append("data/cron_data.xml")` when `spec.get("cron_jobs")` is non-empty.
**Warning signs:** Cron jobs don't appear in Settings > Technical > Scheduled Actions.

### Pitfall 5: Cron Runs Before Model is Loaded
**What goes wrong:** Cron XML is loaded before the model's Python file, causing `model_id ref` resolution failure.
**Why it happens:** Odoo loads manifest `data` files in order; if cron data comes before the model registration, the `ir.model` record doesn't exist yet.
**How to avoid:** Place cron data file AFTER model registration in the manifest. Since models are registered from Python imports (not data files), this is not strictly an issue -- but the cron data file should still come after security files in the manifest for clean ordering.
**Warning signs:** Module install fails with model reference errors.

### Pitfall 6: render_static Overwrites data.xml
**What goes wrong:** `render_static` currently creates a stub `data/data.xml`. If `render_cron` also writes to `data/`, the files could conflict.
**Why it happens:** The current `render_static` writes a hardcoded stub `data/data.xml`.
**How to avoid:** Use a separate file `data/cron_data.xml` for cron records rather than writing to `data/data.xml`. This avoids conflicts and maintains clean separation.

## Code Examples

### Cron Data Template (cron_data.xml.j2)

```jinja2
{# cron_data.xml.j2 -- ir.cron scheduled action records #}
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
{% for cron in cron_jobs %}

    <record id="cron_{{ module_name }}_{{ cron.method }}" model="ir.cron">
        <field name="name">{{ cron.name }}</field>
        <field name="active" eval="{{ cron.active | default(True) }}"/>
        <field name="user_id" ref="base.user_root"/>
        <field name="interval_number">{{ cron.interval_number | default(1) }}</field>
        <field name="interval_type">{{ cron.interval_type | default('days') }}</field>
        <field name="numbercall">-1</field>
        <field name="doall" eval="False"/>
        <field name="model_id" ref="model_{{ cron.model_name | to_xml_id }}"/>
        <field name="state">code</field>
        <field name="code">model.{{ cron.method }}()</field>
    </record>
{% endfor %}

</odoo>
```

### Model Context Enrichment for Cron Methods

```python
# In _build_model_context(), after existing Phase 29 block:

# Phase 30: cron method stubs for this model
cron_jobs = spec.get("cron_jobs", [])
cron_methods = [
    cron for cron in cron_jobs
    if cron.get("model_name") == model["name"]
]

# Update needs_api to include cron methods
needs_api = bool(
    computed_fields or onchange_fields or constrained_fields
    or sequence_fields or has_temporal or has_create_override
    or cron_methods  # Phase 30
)
```

### Model Template Extension for Cron Stubs

```jinja2
{# At the end of model.py.j2, after write() override block #}
{% for cron in cron_methods %}

    @api.model
    def {{ cron.method }}(self):
        """Scheduled action: {{ cron.name }}."""
        # TODO: implement scheduled action logic
        pass
{% endfor %}
```

### render_cron Stage Function

```python
def render_cron(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render ir.cron XML data file for scheduled actions.

    No-op (returns empty list) when spec has no cron_jobs.
    """
    try:
        cron_jobs = spec.get("cron_jobs", [])
        if not cron_jobs:
            return Result.ok([])
        created: list[Path] = []
        cron_ctx = {
            **module_context,
            "cron_jobs": cron_jobs,
        }
        created.append(
            render_template(
                env, "cron_data.xml.j2",
                module_dir / "data" / "cron_data.xml",
                cron_ctx,
            )
        )
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_cron failed: {exc}")
```

### Sample Spec with cron_jobs

```json
{
    "module_name": "academy",
    "models": [
        {
            "name": "academy.course",
            "fields": [
                {"name": "name", "type": "Char", "required": true},
                {"name": "active", "type": "Boolean", "default": "True"}
            ]
        }
    ],
    "cron_jobs": [
        {
            "name": "Archive Expired Courses",
            "model_name": "academy.course",
            "method": "_cron_archive_expired",
            "interval_number": 1,
            "interval_type": "days"
        }
    ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `model` + `function` + `args` in ir.cron | `model_id` + `state` + `code` | Odoo 11+ | Old format deprecated; new format is standard in Odoo 17 |
| `<openerp>` root tag | `<odoo>` root tag | Odoo 10+ | `<openerp>` still works but `<odoo>` is standard |
| No `doall` default | `doall="False"` recommended | Odoo best practice | Prevents server overload on restart after downtime |
| 7 render stages | 10 render stages (Phase 30) | This phase | Pipeline prepared for reports, controllers, cron |

## Open Questions

1. **Should `cron_data.xml` be a separate file or merged into `data/data.xml`?**
   - What we know: Currently `data/data.xml` is a stub. Merging would reduce file count but complicate the template.
   - Recommendation: Use separate `data/cron_data.xml`. Cleaner separation, easier testing, consistent with `data/sequences.xml` pattern. Add to manifest data list alongside `data/data.xml`.

2. **Should the cron method name be validated against Python identifier rules?**
   - What we know: Invalid method names would cause syntax errors in generated Python.
   - Recommendation: Add a simple `str.isidentifier()` check in the render stage, returning `Result.fail()` for invalid names. Low effort, high safety.

3. **Should placeholder stages (render_reports, render_controllers) accept spec sections now?**
   - What we know: These stages will be implemented in Phases 31 and 32.
   - Recommendation: No. Return `Result.ok([])` unconditionally. Phase 31/32 will add the logic. Wiring now means the pipeline is ready.

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
| TMPL-05a | Spec with cron_jobs generates data/cron_data.xml with ir.cron records | integration | `pytest tests/test_render_stages.py::TestRenderCron -x` | Wave 0 |
| TMPL-05b | Cron XML has correct interval_type, interval_number, model_id ref | integration | `pytest tests/test_render_stages.py::TestRenderCron -x` | Wave 0 |
| TMPL-05c | Cron XML has `doall="False"` by default | unit | `pytest tests/test_render_stages.py::TestRenderCron -x` | Wave 0 |
| TMPL-05d | Target model gets @api.model stub method | integration | `pytest tests/test_render_stages.py::TestRenderCronModelStub -x` | Wave 0 |
| TMPL-05e | Spec without cron_jobs: render_cron returns Result.ok([]) | unit | `pytest tests/test_render_stages.py::TestRenderCron -x` | Wave 0 |
| TMPL-05f | cron_data.xml in manifest when cron_jobs present | unit | `pytest tests/test_renderer.py::TestBuildModuleContextCron -x` | Wave 0 |
| TMPL-05g | needs_api set when model has cron methods | unit | `pytest tests/test_renderer.py::TestBuildModelContextCron -x` | Wave 0 |
| TMPL-06a | render_reports returns Result.ok([]) (placeholder) | unit | `pytest tests/test_render_stages.py::TestRenderReportsPlaceholder -x` | Wave 0 |
| TMPL-06b | render_controllers returns Result.ok([]) (placeholder) | unit | `pytest tests/test_render_stages.py::TestRenderControllersPlaceholder -x` | Wave 0 |
| TMPL-06c | render_module calls 10 stages (was 7) | unit | `pytest tests/test_render_stages.py::TestRenderModulePipeline -x` | Wave 0 |
| TMPL-06d | Full render_module with cron_jobs produces cron XML + model method | integration | `pytest tests/test_render_stages.py::TestRenderModuleCronIntegration -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q`
- **Per wave merge:** `cd python && .venv/bin/python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green (686+ tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_render_stages.py::TestRenderCron` -- cron XML generation tests
- [ ] `tests/test_render_stages.py::TestRenderCronModelStub` -- verify @api.model method on model
- [ ] `tests/test_render_stages.py::TestRenderReportsPlaceholder` -- placeholder no-op test
- [ ] `tests/test_render_stages.py::TestRenderControllersPlaceholder` -- placeholder no-op test
- [ ] `tests/test_render_stages.py::TestRenderModulePipeline` -- stage count verification
- [ ] `tests/test_render_stages.py::TestRenderModuleCronIntegration` -- end-to-end with cron
- [ ] `tests/test_renderer.py::TestBuildModuleContextCron` -- manifest data includes cron file
- [ ] `tests/test_renderer.py::TestBuildModelContextCron` -- cron_methods and needs_api
- [ ] `python/src/odoo_gen_utils/templates/shared/cron_data.xml.j2` -- new template file

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `renderer.py` (~1314 lines, 7 render stages, `_build_model_context()`, `_build_module_context()`, `render_module()`)
- Codebase analysis: `17.0/model.py.j2` and `18.0/model.py.j2` (template structure, `@api.model` pattern from sequence fields)
- Codebase analysis: `shared/sequences.xml.j2` (XML data template pattern in `data/` directory)
- Codebase analysis: `test_render_stages.py` (stage test patterns with `_make_spec()` helpers)
- Codebase analysis: `validation/types.py` (Result type: `Result.ok(data)`, `Result.fail(*errors)`)

### Secondary (MEDIUM confidence)
- [Odoo Development Docs: ir.cron](https://odoo-development.readthedocs.io/en/latest/odoo/models/ir.cron.html) -- XML field structure, noupdate, doall
- [Cybrosys: Scheduled Actions in Odoo 17](https://medium.com/cybrosys/how-to-configure-scheduled-actions-in-odoo-17-2c73b2ee3aee) -- Odoo 17 specific model_id/state/code pattern
- [odoo-sample cron.xml](https://github.com/alexis-via/odoo-sample/blob/master/cron.xml) -- Complete XML example with both old and new format

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure pipeline extension
- Architecture: HIGH -- follows exact existing render stage pattern; 7 stages already proven
- Pitfalls: HIGH -- Odoo ir.cron format well-documented; 6 pitfalls identified with clear prevention
- Cron XML format: HIGH -- verified via multiple sources, consistent between Odoo 17/18

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain, ir.cron API unchanged since Odoo 11)
