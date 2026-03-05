# Phase 26: Monetary Field Detection - Research

**Researched:** 2026-03-05
**Domain:** Odoo fields.Monetary auto-detection + currency_id injection in spec-driven renderer
**Confidence:** HIGH

## Summary

Phase 26 is a surgical change to the existing renderer pipeline. The goal is to auto-detect fields whose names match monetary patterns (amount, fee, salary, price, cost, balance, etc.) and rewrite their type from `Float` to `Monetary`, while auto-injecting a `currency_id` Many2one companion field when one is not already present. Without this, generated modules crash at install with `AssertionError: Field X with unknown currency_field None`.

The change touches exactly 3 files: `renderer.py` (add detection logic in `_build_model_context()`), `model.py.j2` (add a Monetary field rendering branch + currency_id injection block), and corresponding test files. No new dependencies, no new templates, no new render stages. The existing pattern of enriching `_build_model_context()` with detection results (identical to how `sequence_fields`, `state_field`, and `has_company_field` work) applies directly.

**Primary recommendation:** Add a `MONETARY_FIELD_PATTERNS` frozenset in `renderer.py`, detect matching fields in `_build_model_context()`, rewrite their type to `Monetary`, inject `currency_id` if missing, and add a new template branch in `model.py.j2` for `field.type == 'Monetary'`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPEC-01 | Renderer auto-detects Monetary field patterns (amount, fee, salary, price, cost, balance) and generates `fields.Monetary` with `currency_id` injection | Detection logic in `_build_model_context()`, template branch in `model.py.j2`, currency_id injection pattern documented below |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | (existing) | Template rendering | Already in use, no changes needed |
| Python 3.12 | (existing) | Detection logic in renderer.py | Already in use |

### Supporting
No new libraries needed. This is a pure logic + template change.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pattern-matching in `_build_model_context()` | Spec-level `type: Monetary` explicit declaration | Explicit is cleaner but defeats the "auto-detect" goal; users would need to know Odoo's Monetary type exists |
| Frozen set of name suffixes/substrings | Regex patterns | Regex is overkill for simple substring/suffix matching; frozen set is simpler, faster, and more maintainable |

## Architecture Patterns

### Where Detection Happens

The detection must happen in `_build_model_context()` (renderer.py, line 162). This function already enriches the template context with derived information (computed_fields, sequence_fields, state_field, has_company_field). The monetary detection follows the exact same pattern.

**Current pipeline flow:**
```
spec JSON -> _build_model_context() -> enriched context dict -> model.py.j2 template -> .py file
```

**After change:**
```
spec JSON -> _build_model_context() [+ monetary detection + currency_id injection]
          -> enriched context dict [+ monetary_fields, has_currency_id, needs_currency_id]
          -> model.py.j2 [+ Monetary branch + currency_id block]
          -> .py file with fields.Monetary + currency_id
```

### Pattern 1: Field Name Detection

**What:** Match field names against a set of monetary patterns (substrings and suffixes).
**When to use:** During `_build_model_context()` for every field in the model.

```python
# Source: Existing pattern from SEQUENCE_FIELD_NAMES in renderer.py line 18
MONETARY_FIELD_PATTERNS: frozenset[str] = frozenset({
    "amount", "fee", "salary", "price", "cost", "balance",
    "total", "subtotal", "tax", "discount", "payment",
    "revenue", "expense", "budget", "wage", "rate",
    "charge", "premium", "debit", "credit",
})

def _is_monetary_field(field: dict[str, Any]) -> bool:
    """Check if a field name matches monetary patterns.

    Only applies to Float fields (or fields without explicit type).
    Fields already typed as Monetary are left as-is.
    """
    if field.get("type") not in ("Float", None):
        return False
    name = field.get("name", "")
    # Check if the field name contains any monetary pattern
    return any(pattern in name for pattern in MONETARY_FIELD_PATTERNS)
```

### Pattern 2: Currency ID Injection

**What:** Auto-inject a `currency_id` Many2one field pointing to `res.currency` when any monetary field is detected and no `currency_id` already exists.
**When to use:** In `_build_model_context()` after monetary field detection.

```python
# Source: Odoo Monetary field documentation + Odoo source (PR #15130)
# Odoo's resolution order: currency_id -> x_currency_id -> AssertionError

# Injected field spec:
CURRENCY_ID_FIELD = {
    "name": "currency_id",
    "type": "Many2one",
    "comodel_name": "res.currency",
    "string": "Currency",
    "default_company_currency": True,  # signals template to add default lambda
}
```

### Pattern 3: Template Rendering for Monetary Fields

**What:** A new branch in model.py.j2 that renders `fields.Monetary` with `currency_field` parameter.
**When to use:** When `field.type == 'Monetary'` in the field rendering loop.

```jinja2
{# New branch in the field rendering loop, before the catch-all else #}
{% elif field.type == 'Monetary' %}
    {{ field.name }} = fields.Monetary(
        string="{{ field.string | default(field.name | replace('_', ' ') | title) }}",
        currency_field="currency_id",
{% if field.required is defined and field.required %}
        required=True,
{% endif %}
{% if field.help is defined %}
        help="{{ field.help }}",
{% endif %}
    )
```

### Recommended Implementation Order

1. Add `MONETARY_FIELD_PATTERNS` constant and `_is_monetary_field()` helper to `renderer.py`
2. Modify `_build_model_context()` to detect monetary fields, rewrite their type, add context keys
3. Add currency_id injection logic (mutate the fields list copy, not the original)
4. Add `Monetary` branch to both `17.0/model.py.j2` and `18.0/model.py.j2`
5. Add currency_id injection block at the top of the field loop in both templates
6. Write tests

### Anti-Patterns to Avoid
- **Mutating the original spec:** Always work on copies. The spec dict may be reused across models. Use `{**field, "type": "Monetary"}` for immutable updates.
- **Hardcoding `currency_field="currency_id"` in the context builder:** Keep the template in charge of rendering parameters. The context builder should just flag `is_monetary: True` and let the template decide the parameter.
- **Injecting currency_id when one already exists:** Check `any(f["name"] == "currency_id" for f in fields)` before injecting. The user may have defined their own with a `related` to `company_id.currency_id`.
- **Only checking exact name matches:** Use substring matching (`"amount" in name`), not exact matches. Fields like `total_amount`, `tuition_fee`, `base_salary` should all match.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Monetary detection | Complex NLP/regex | Simple substring frozenset | Monetary field names follow predictable patterns in business domains; 20 patterns cover 99% of cases |
| Currency field resolution | Custom resolution logic | Odoo's built-in `currency_field` parameter defaulting to `"currency_id"` | Odoo already resolves this; just ensure the field exists |

## Common Pitfalls

### Pitfall 1: Missing currency_id Causes InstallCrash
**What goes wrong:** `fields.Monetary` without a `currency_id` field on the model triggers `AssertionError: Field X with unknown currency_field None` at module install time.
**Why it happens:** Odoo's field setup resolves `currency_field` by looking for a field named `currency_id` (or `x_currency_id`) on the model. If neither exists, it asserts and crashes.
**How to avoid:** Always inject `currency_id = fields.Many2one('res.currency', ...)` when any monetary field is detected and no currency_id exists.
**Warning signs:** Any `fields.Monetary` in generated code without a corresponding `currency_id` field.

### Pitfall 2: Float Fields Named "amount" Get Wrong Type
**What goes wrong:** A user explicitly declares `{"name": "amount", "type": "Float"}` intending a plain float, but auto-detection rewrites it to Monetary.
**Why it happens:** Overly aggressive pattern matching.
**How to avoid:** Only rewrite Float fields. If a user explicitly sets `type: "Integer"` or any non-Float type, respect it. Also consider adding an opt-out flag like `"monetary": false` on the field spec.
**Warning signs:** Tests with explicit Float types being rewritten.

### Pitfall 3: Currency ID Default Lambda
**What goes wrong:** The injected `currency_id` field has no default value, so new records have no currency and monetary fields show as 0.00 without currency symbol.
**Why it happens:** Missing default lambda.
**How to avoid:** The injected currency_id should default to `lambda self: self.env.company.currency_id` (Odoo 13+ pattern). This is the standard Odoo pattern.
**Warning signs:** Monetary fields in form views showing raw numbers without currency symbols.

### Pitfall 4: Duplicate currency_id Injection
**What goes wrong:** If two models in the same module both have monetary fields, and both get currency_id injected, the generation works fine. But if a user already defined `currency_id` manually in their spec, the auto-injection creates a duplicate.
**How to avoid:** Check `any(f.get("name") == "currency_id" for f in fields)` before injecting. This check must happen on the model's fields list, not on a global level.

### Pitfall 5: Template Branch Ordering
**What goes wrong:** The `Monetary` branch in the Jinja2 template must come before the generic `else` branch but also before the `compute` branch, since a computed monetary field needs both `compute=` and `currency_field=`.
**Why it happens:** Jinja2 if/elif chains are order-dependent.
**How to avoid:** Place Monetary branch handling within or alongside the computed field branch. Computed monetary fields need special handling: `fields.Monetary(compute="...", currency_field="currency_id", store=True)`.

## Code Examples

### Context Builder Extension (renderer.py)

```python
# Source: Follows existing SEQUENCE_FIELD_NAMES pattern at renderer.py:18
MONETARY_FIELD_PATTERNS: frozenset[str] = frozenset({
    "amount", "fee", "salary", "price", "cost", "balance",
    "total", "subtotal", "tax", "discount", "payment",
    "revenue", "expense", "budget", "wage", "rate",
    "charge", "premium", "debit", "credit",
})


def _is_monetary_field(field: dict[str, Any]) -> bool:
    """Detect if a field should be rendered as fields.Monetary based on name patterns."""
    field_type = field.get("type", "")
    if field_type == "Monetary":
        return True  # Already explicitly typed
    if field_type != "Float":
        return False  # Only auto-detect on Float fields
    name = field.get("name", "")
    return any(pattern in name for pattern in MONETARY_FIELD_PATTERNS)
```

### In _build_model_context() -- new section after sequence_fields

```python
# Phase 26: monetary field detection
monetary_fields = [f for f in fields if _is_monetary_field(f)]

# Rewrite Float -> Monetary for detected fields (immutable)
if monetary_fields:
    fields = [
        {**f, "type": "Monetary"} if _is_monetary_field(f) and f.get("type") == "Float" else f
        for f in fields
    ]

has_currency_id = any(f.get("name") == "currency_id" for f in fields)
needs_currency_id = bool(monetary_fields) and not has_currency_id
```

### Template Branch (model.py.j2)

```jinja2
{# Currency ID injection -- before field loop #}
{% if needs_currency_id %}
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
{% endif %}

{# In field loop -- new branch for Monetary #}
{% elif field.type == 'Monetary' %}
    {{ field.name }} = fields.Monetary(
        string="{{ field.string | default(field.name | replace('_', ' ') | title) }}",
        currency_field="currency_id",
{% if field.compute is defined and field.compute %}
        compute="{{ field.compute }}",
{% endif %}
{% if field.store is defined and field.store %}
        store=True,
{% endif %}
{% if field.required is defined and field.required %}
        required=True,
{% endif %}
{% if field.help is defined %}
        help="{{ field.help }}",
{% endif %}
    )
```

### Odoo fields.Monetary Behavior (verified)

```python
# Source: Odoo source (github.com/odoo/odoo/pull/15130)
# Resolution order for currency_field:
# 1. Explicit currency_field= parameter on the field
# 2. "currency_id" if exists on the model
# 3. "x_currency_id" if exists on the model
# 4. AssertionError raised

# Standard pattern:
currency_id = fields.Many2one(
    'res.currency',
    string="Currency",
    default=lambda self: self.env.company.currency_id,
)
amount = fields.Monetary(
    string="Amount",
    currency_field="currency_id",  # explicit is safest
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Spec must declare `type: Monetary` explicitly | Auto-detect from field name patterns | Phase 26 (this phase) | Users no longer need to know about fields.Monetary |
| No currency_id injection | Auto-inject when monetary fields detected | Phase 26 (this phase) | Prevents install crashes |
| `self.env.user.company_id.currency_id` | `self.env.company.currency_id` | Odoo 13+ | Shorter, preferred pattern |

## Open Questions

1. **Should we support `currency_field` pointing to a field other than `currency_id`?**
   - What we know: Odoo supports custom currency_field names via the parameter. Some modules use `company_currency_id` or `x_currency_id`.
   - What's unclear: Whether this project's specs ever need non-standard currency field names.
   - Recommendation: Default to `currency_id` for now. If a user explicitly defines a field named differently and sets `currency_field` in the spec, respect it. YAGNI for v3.1.

2. **Should `type: Float` with a monetary name be opt-out or opt-in?**
   - What we know: Auto-detection is the requirement (SPEC-01 says "auto-detects"). But some Float fields named "balance" might legitimately be plain floats (e.g., `balance_qty`).
   - What's unclear: How aggressive the substring matching should be.
   - Recommendation: Use substring matching but allow `"monetary": false` opt-out on the field spec. This is safe because the default (auto-detect) matches the requirement, and the opt-out handles edge cases.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `python/pyproject.toml` (or pytest section) |
| Quick run command | `cd python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q` |
| Full suite command | `cd python && .venv/bin/python -m pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPEC-01a | Float field named "amount" becomes fields.Monetary in context | unit | `pytest tests/test_renderer.py::TestBuildModelContextMonetary -x` | Wave 0 |
| SPEC-01b | currency_id injected when monetary fields detected | unit | `pytest tests/test_renderer.py::TestBuildModelContextMonetary -x` | Wave 0 |
| SPEC-01c | No currency_id injection when already present | unit | `pytest tests/test_renderer.py::TestBuildModelContextMonetary -x` | Wave 0 |
| SPEC-01d | Generated model.py contains `fields.Monetary` with `currency_field` | integration | `pytest tests/test_render_stages.py::TestRenderModelsMonetary -x` | Wave 0 |
| SPEC-01e | Generated model.py contains `currency_id` Many2one | integration | `pytest tests/test_render_stages.py::TestRenderModelsMonetary -x` | Wave 0 |
| SPEC-01f | Pattern matching covers common names (amount, fee, salary, price, cost, balance, total, subtotal) | unit | `pytest tests/test_renderer.py::TestMonetaryPatternDetection -x` | Wave 0 |
| SPEC-01g | Explicit `type: Integer` not rewritten | unit | `pytest tests/test_renderer.py::TestMonetaryPatternDetection -x` | Wave 0 |
| SPEC-01h | `monetary: false` opt-out respected | unit | `pytest tests/test_renderer.py::TestMonetaryPatternDetection -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q`
- **Per wave merge:** `cd python && .venv/bin/python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green (562+ tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_renderer.py::TestBuildModelContextMonetary` -- new test class for monetary detection in context builder
- [ ] `tests/test_renderer.py::TestMonetaryPatternDetection` -- new test class for `_is_monetary_field()` function
- [ ] `tests/test_render_stages.py::TestRenderModelsMonetary` -- new test class for rendered output containing `fields.Monetary`

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `renderer.py` (770 lines, 7 render stages, `_build_model_context()` at line 162)
- Codebase analysis: `17.0/model.py.j2` and `18.0/model.py.j2` (identical structure, ~123 lines each)
- Codebase analysis: `test_renderer.py` (562 tests total, `_build_model_context` test patterns)
- Codebase analysis: `test_render_stages.py` (stage function tests with `_make_spec()` helpers)
- [Odoo PR #15130](https://github.com/odoo/odoo/pull/15130/files) -- currency_field resolution: `currency_id` -> `x_currency_id` -> AssertionError

### Secondary (MEDIUM confidence)
- [Odoo Forum: AssertionError currency_field None](https://www.odoo.com/forum/help-1/assertionerror-field-s-with-unknown-currency-field-none-193965) -- confirms the crash scenario
- [Cybrosys Monetary Fields Guide](https://www.cybrosys.com/odoo/odoo-books/odoo-17-development/creating-odoo-modules/monetary-fields/) -- standard currency_id pattern with `self.env.company.currency_id`
- Milestone research SUMMARY.md -- confirms monetary detection as FLAW-04, P1 priority

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure logic change
- Architecture: HIGH -- follows exact existing pattern (`SEQUENCE_FIELD_NAMES`, `_build_model_context()`, template branching)
- Pitfalls: HIGH -- crash scenario verified via Odoo source and forum posts; 5 pitfalls documented with prevention

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain, Odoo field API unchanged since v13)
