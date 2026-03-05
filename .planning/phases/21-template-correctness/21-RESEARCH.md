# Phase 21: Template Correctness - Research

**Researched:** 2026-03-05
**Domain:** Jinja2 template generation for Odoo modules (renderer.py + .j2 templates)
**Confidence:** HIGH

## Summary

Phase 21 fixes four template-level bugs in the Odoo module generator. All four are well-documented in BUGS_FLAWS_DEBT.md with precise file locations and fix strategies. The bugs affect: (1) indiscriminate mail.thread injection into every model, (2) unconditional `api` import in wizard templates, (3) missing ACL entries for wizard TransientModels, and (4) deprecated `name_get()` usage in test templates.

The codebase is mature (444 tests, 15,700+ LOC Python) with comprehensive test infrastructure. All four fixes are localized to the renderer and template layer -- no cross-module dependencies. The fixes modify `renderer.py` (~264 lines of context-building logic) and four Jinja2 templates (`model.py.j2`, `wizard.py.j2`, `access_csv.j2`, `test_model.py.j2`).

**Primary recommendation:** Fix each TMPL requirement as a focused change to the template + renderer context, with corresponding unit tests. All four are independent of each other and could be in a single plan or two.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TMPL-01 | mail.thread injection respects per-model chatter flag (default true for top-level business models, false for config tables, line items, wizards, and models extending parents with mail.thread) | `_build_model_context()` lines 216-221 need conditional logic; auto-detect line items via required Many2one `_id` pattern |
| TMPL-02 | Wizard template conditionally imports `api` only when @api decorators are used | `wizard.py.j2` line 2 hardcodes `api` import; needs `needs_api` variable like `model.py.j2` already has |
| TMPL-03 | Wizard TransientModels receive ACL entries in ir.model.access.csv | `access_csv.j2` iterates only `models`; `spec_wizards` is already in the template context from `render_module()` |
| TMPL-04 | Test template uses display_name instead of deprecated name_get(), with version gate for Odoo 18.0 | `test_model.py.j2` lines 55-60 call `name_get()`; replace with `display_name` assertion, gate old pattern for < 18.0 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | >=3.1 | Template rendering | Already in use; StrictUndefined catches missing vars |
| pytest | >=8.0 | Test framework | Already in use; 444 existing tests |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| N/A | - | No new libraries needed | All fixes use existing stack |

**Installation:** No new packages required.

## Architecture Patterns

### Current Template Architecture
```
python/src/odoo_gen_utils/
├── renderer.py                    # _build_model_context() + render_module()
├── templates/
│   ├── shared/
│   │   ├── model.py.j2           # --> TMPL-01 (inherit_list logic is in renderer.py)
│   │   ├── wizard.py.j2          # --> TMPL-02 (needs conditional api import)
│   │   ├── access_csv.j2         # --> TMPL-03 (needs wizard ACL loop)
│   │   └── test_model.py.j2      # --> TMPL-04 (name_get -> display_name)
│   ├── 17.0/
│   │   └── model.py.j2           # Same structure as shared, version-specific
│   └── 18.0/
│       └── model.py.j2           # Same structure as shared, version-specific
```

### Pattern: Context-Building in Renderer, Logic-Free Templates

The codebase follows a pattern where `_build_model_context()` in `renderer.py` computes all derived values (booleans, filtered lists), and templates use simple conditionals. This pattern MUST be maintained:

```python
# renderer.py -- compute the value
needs_api = bool(computed_fields or onchange_fields or ...)

# template.j2 -- simple conditional
from odoo import {{ 'api, ' if needs_api }}fields, models
```

### Pattern: Version-Specific Template Overlay

Templates in `17.0/` and `18.0/` override `shared/` templates. The `create_versioned_renderer()` function loads version-specific first, then falls back to shared. For TMPL-04, the `odoo_version` variable is already passed to template context.

### Anti-Patterns to Avoid
- **Complex logic in templates:** Keep Jinja2 templates declarative. All model classification (line item vs top-level) belongs in `renderer.py`.
- **Breaking existing context keys:** `inherit_list`, `needs_api`, and `models` are used by existing templates. Additions must be backward-compatible.
- **Modifying both versioned templates when shared suffices:** `wizard.py.j2`, `access_csv.j2`, and `test_model.py.j2` are in `shared/` only. No version-specific copies needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Line item detection | Custom model type classifier | Simple heuristic: required Many2one field whose comodel is another model in the same module | The spec already has `fields[].type` and `fields[].comodel_name` |
| Version comparison | String comparison | `odoo_version < "18.0"` string comparison in Jinja2 | Odoo versions are lexicographically ordered (14.0 < 17.0 < 18.0) |

## Common Pitfalls

### Pitfall 1: mail.thread on Models That Extend Parents Already Having It
**What goes wrong:** Duplicate `_inherit` entries cause Odoo to process mail.thread twice, wasting DB space with duplicate mail.message triggers.
**Why it happens:** Current code checks if `"mail.thread"` is in `inherit_list` but doesn't check if the parent model already has it.
**How to avoid:** When a model has `inherit` pointing to a parent that already has `mail.thread`, skip injecting it. In the current spec-driven generator, this means checking if the model's explicit `inherit` target is another model in the same module that would also get mail.thread.
**Warning signs:** Duplicate `_inherit` values in generated code.

### Pitfall 2: Wizard default_get Always Uses @api.model
**What goes wrong:** The current wizard template always generates a `default_get` method with `@api.model`, so `api` is always needed in the default case.
**Why it happens:** Template hardcodes `default_get` with `@api.model` decorator.
**How to avoid:** The `needs_api` flag for wizards should default to `True` when `default_get` is present (which is always in current template). The conditional import becomes meaningful only when the wizard template is customized or when `default_get` is removed. Still worth implementing for correctness -- the current unconditional import masks real unused-import cases.
**Warning signs:** pylint W0611 (unused import) on wizard files where `@api` decorators have been manually removed.

### Pitfall 3: TransientModel ACL Format Differs from Regular Model
**What goes wrong:** Wizard ACLs should grant all CRUD to the user group (1,1,1,1) since wizards are ephemeral. Using the regular model pattern (1,1,1,0 for user / 1,1,1,1 for manager) is overly restrictive.
**Why it happens:** Copy-pasting model ACL pattern without considering TransientModel semantics.
**How to avoid:** Wizard ACL entries should grant full access (1,1,1,1) to the user group. Only one line per wizard is needed (no separate manager line).
**Warning signs:** `AccessError` when non-manager users try to open wizards.

### Pitfall 4: name_get() Returns List of Tuples, display_name Returns String
**What goes wrong:** Test assertions written for `name_get()` (returns `[(id, name)]`) don't work with `display_name` (returns string).
**Why it happens:** Different API signatures.
**How to avoid:** The replacement test should assert `self.test_record.display_name` is truthy and optionally contains expected text. Do not try to replicate the `name_get()` tuple structure.
**Warning signs:** Test assertion errors on Odoo 18.0 targets.

### Pitfall 5: Both 17.0 and 18.0 model.py.j2 Need the Same Fix
**What goes wrong:** Fixing only `shared/model.py.j2` doesn't fix mail.thread for version-specific templates.
**Why it happens:** Both `17.0/model.py.j2` and `18.0/model.py.j2` exist and override the shared template. But for TMPL-01, the mail.thread logic is in `renderer.py`'s `_build_model_context()`, NOT in the template itself. The template just uses `inherit_list`.
**How to avoid:** The fix for TMPL-01 is entirely in `renderer.py` -- the template already correctly renders whatever `inherit_list` contains. No template file changes needed for TMPL-01.

## Code Examples

### TMPL-01: Smart mail.thread Injection (renderer.py)

Current code (lines 216-221):
```python
# Phase 12: mail.thread auto-inheritance (TMPL-01)
explicit_inherit = model.get("inherit")
inherit_list = [explicit_inherit] if explicit_inherit else []
if "mail" in spec.get("depends", []):
    for mixin in ("mail.thread", "mail.activity.mixin"):
        if mixin not in inherit_list:
            inherit_list.append(mixin)
```

Fix approach -- add line item and config detection:
```python
# Detect if model is a line item (has required Many2one to another model in same module)
module_model_names = {m["name"] for m in spec.get("models", [])}
is_line_item = any(
    f.get("type") == "Many2one"
    and f.get("required")
    and f.get("comodel_name") in module_model_names
    and f.get("name", "").endswith("_id")
    for f in model.get("fields", [])
)

# Check explicit chatter flag (spec can override auto-detection)
chatter = model.get("chatter")  # None = auto, True = force, False = skip
if chatter is None:
    chatter = not is_line_item  # Default: True for top-level, False for line items

explicit_inherit = model.get("inherit")
inherit_list = [explicit_inherit] if explicit_inherit else []
if chatter and "mail" in spec.get("depends", []):
    # Skip if parent already has mail.thread
    parent_has_mail = explicit_inherit and explicit_inherit in module_model_names
    if not parent_has_mail:
        for mixin in ("mail.thread", "mail.activity.mixin"):
            if mixin not in inherit_list:
                inherit_list.append(mixin)
```

### TMPL-02: Conditional api Import for Wizards (wizard.py.j2)

Current template line 2:
```jinja
from odoo import api, fields, models
```

Fix -- add needs_api to wizard context in render_module():
```python
# In render_module(), wizard rendering section (~line 617-646)
wizard_has_api_methods = True  # default_get uses @api.model
wizard_ctx = {
    **module_context,
    "wizard": wizard,
    "wizard_var": wizard_var,
    "wizard_xml_id": wizard_xml_id,
    "wizard_class": _to_class(wizard["name"]),
    "needs_api": wizard_has_api_methods,  # NEW
}
```

Updated template:
```jinja
from odoo import {{ 'api, ' if needs_api }}fields, models
```

### TMPL-03: Wizard ACL Entries (access_csv.j2)

Current template only loops `models`. Add wizard loop:
```jinja
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
{% for model in models %}
access_{{ model.name | to_python_var }}_user,{{ model.name }}.user,{{ model.name | model_ref }},{{ module_technical_name }}.group_{{ module_technical_name }}_user,1,1,1,0
access_{{ model.name | to_python_var }}_manager,{{ model.name }}.manager,{{ model.name | model_ref }},{{ module_technical_name }}.group_{{ module_technical_name }}_manager,1,1,1,1
{% endfor %}
{% for wizard in spec_wizards %}
access_{{ wizard.name | to_python_var }}_user,{{ wizard.name }}.user,{{ wizard.name | model_ref }},{{ module_technical_name }}.group_{{ module_technical_name }}_user,1,1,1,1
{% endfor %}
```

Note: `spec_wizards` is already passed in `module_context` (renderer.py line 446).

### TMPL-04: display_name Instead of name_get() (test_model.py.j2)

Current template (lines 54-60):
```jinja
{% for field in fields %}
{% if field.name == 'name' %}
    def test_name_get(self):
        """Test that name_get returns the expected display name."""
        result = self.test_record.name_get()
        self.assertTrue(result, "name_get should return a result")
        self.assertEqual(result[0][0], self.test_record.id)
{% endif %}
{% endfor %}
```

Fix with version gate:
```jinja
{% for field in fields %}
{% if field.name == 'name' %}
{% if odoo_version >= "18.0" %}
    def test_display_name(self):
        """Test that display_name returns the expected value."""
        self.assertTrue(
            self.test_record.display_name,
            "display_name should be set",
        )
{% else %}
    def test_display_name(self):
        """Test that display_name returns the expected value."""
        self.assertTrue(
            self.test_record.display_name,
            "display_name should be set",
        )
        self.assertIn(
            str(self.test_record.id),
            str(self.test_record.name_get()[0]),
            "name_get should include record id",
        )
{% endif %}
{% endif %}
{% endfor %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `name_get()` method | `display_name` computed field | Odoo 17.0 (deprecated) / 18.0 (removed) | Tests calling `name_get()` fail on 18.0 |
| `<div class="oe_chatter">` | `<chatter/>` shorthand | Odoo 18.0 | View templates differ by version (already handled) |
| Unconditional mail.thread | Per-model chatter flag | Best practice | Reduces noise on config/line-item models |

## Open Questions

1. **Config table auto-detection heuristic**
   - What we know: Line items can be detected by required Many2one `_id` field pattern
   - What's unclear: How to auto-detect "config tables" without explicit flag. Models named `*.category`, `*.type`, `*.tag` are common config patterns, but heuristic may be brittle.
   - Recommendation: Support explicit `chatter: false` flag in model spec. Auto-detect line items only. Don't try to auto-detect config tables -- let the spec author decide.

2. **Wizard needs_api edge case**
   - What we know: Current wizard template always generates `default_get` with `@api.model`, so `api` is always needed
   - What's unclear: Whether future wizard templates might omit `default_get`
   - Recommendation: Compute `needs_api` based on whether the wizard spec implies API decorator usage (currently always true due to default_get). Still implement the conditional to be correct even if it's always true today.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | python/pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `cd python && uv run pytest tests/test_renderer.py -x -q` |
| Full suite command | `cd python && uv run pytest tests/ -x -q --ignore=tests/test_golden_path.py` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMPL-01 | mail.thread only on top-level business models | unit | `cd python && uv run pytest tests/test_renderer.py -x -q -k "mail_thread"` | Partial (existing tests verify injection, need tests for SKIP cases) |
| TMPL-02 | wizard api import conditional | unit | `cd python && uv run pytest tests/test_renderer.py -x -q -k "wizard_api"` | No |
| TMPL-03 | wizard ACL entries in csv | unit | `cd python && uv run pytest tests/test_renderer.py -x -q -k "wizard_acl"` | No |
| TMPL-04 | display_name instead of name_get | unit | `cd python && uv run pytest tests/test_renderer.py -x -q -k "display_name"` | No |

### Sampling Rate
- **Per task commit:** `cd python && uv run pytest tests/test_renderer.py -x -q`
- **Per wave merge:** `cd python && uv run pytest tests/ -x -q --ignore=tests/test_golden_path.py`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Tests for TMPL-01 skip cases: line items, config tables, wizards, already-inherited models
- [ ] Tests for TMPL-02: wizard `needs_api` conditional import
- [ ] Tests for TMPL-03: wizard ACL entries appear in rendered csv
- [ ] Tests for TMPL-04: `display_name` assertion for 17.0 and 18.0

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `renderer.py`, all `.j2` templates, `test_renderer.py` (1400+ lines)
- `BUGS_FLAWS_DEBT.md` -- BUG-H1, BUG-M6, BUG-L1, BUG-L2 with exact file locations and fix strategies
- `knowledge/models.md` -- Odoo 18.0 name_get() deprecation documented

### Secondary (MEDIUM confidence)
- Odoo official docs: mail.thread should not be on TransientModels or line items (general Odoo best practice)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, all fixes in existing code
- Architecture: HIGH - pattern is clear from codebase inspection (context-builder + template)
- Pitfalls: HIGH - all documented in BUGS_FLAWS_DEBT.md with reproduction steps
- Code examples: HIGH - derived from actual current code with precise line numbers

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- no external dependencies changing)
