# Phase 27: Relationship Patterns - Research

**Researched:** 2026-03-05
**Domain:** Odoo relationship patterns -- through-models for M2M with extra fields, self-referential M2M, hierarchical parent_id/parent_path
**Confidence:** HIGH

## Summary

Phase 27 extends the spec format with a `relationships` section that enables three advanced relationship patterns that Odoo developers frequently need but the current generator cannot produce: (1) Many2many relationships with extra fields via dedicated through-models, (2) self-referential Many2many with explicit `relation`/`column1`/`column2` parameters, and (3) hierarchical models with `parent_id`, `child_ids`, `parent_path`, and `_parent_store = True`.

The current renderer handles basic Many2one, One2many, and Many2many fields but only renders `comodel_name` and `string` parameters for relational fields. It does not support `relation`, `column1`, `column2` for Many2many, cannot generate intermediate/through-models from a relationship declaration, and has no concept of hierarchical model configuration. All three gaps require changes in both the spec-processing logic (`_build_model_context()`) and the templates (`model.py.j2`, `init_models.py.j2`, `access_csv.j2`).

The standard Odoo pattern for M2M with extra fields is to NOT use a Many2many field at all -- instead, you create a dedicated intermediate model with two Many2one fields and the extra columns, then use One2many on the parent models. This is well-established Odoo convention (how `account.move.line`, `sale.order.line`, etc. work). The spec `relationships` section should declare this intent, and the renderer should synthesize the through-model, its fields, and its ACL entries automatically.

**Primary recommendation:** Add a `relationships` section to the spec format. Process it in a new `_process_relationships()` function called before `_build_model_context()`. This function synthesizes through-models (appended to `spec["models"]`) and injects `relation`/`column1`/`column2` on self-referential M2M fields. Add `hierarchical: true` as a model-level flag processed in `_build_model_context()`. Update templates for Many2many parameters and hierarchical fields.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPEC-02 | Spec supports a `relationships` section with through-models for M2M with extra fields, self-referential M2M (with explicit relation/column params), and hierarchical parent_id patterns | Spec format design, `_process_relationships()` preprocessor, template extensions for M2M params and hierarchical fields, through-model synthesis, ACL generation |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | (existing) | Template rendering for model.py.j2, access_csv.j2, init_models.py.j2 | Already in use |
| Python 3.12 | (existing) | Relationship processing logic in renderer.py | Already in use |

### Supporting
No new libraries needed. This is a spec-processing + template change.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Through-model synthesis in renderer | User manually defines intermediate models in spec | Manual approach is error-prone (users forget ACLs, `__init__.py` imports, or use wrong field types); synthesis is the value-add |
| `_process_relationships()` as preprocessor | Inline logic in `_build_model_context()` | Preprocessor is cleaner because through-model synthesis creates NEW models, which `_build_model_context()` only processes one at a time |
| Model-level `hierarchical: true` flag | Separate `relationships` entry for hierarchy | Model-level flag is simpler since hierarchy is a property of a single model, not a cross-model relationship |

## Architecture Patterns

### Spec Format Design

The `relationships` section sits at the spec root level alongside `models` and `wizards`:

```json
{
  "module_name": "university",
  "models": [...],
  "relationships": [
    {
      "type": "m2m_through",
      "from": "university.course",
      "to": "university.student",
      "through_model": "university.enrollment",
      "through_fields": [
        {"name": "grade", "type": "Float"},
        {"name": "enrollment_date", "type": "Date", "default": "fields.Date.today"}
      ]
    },
    {
      "type": "self_m2m",
      "model": "university.course",
      "field_name": "prerequisite_ids",
      "inverse_field_name": "dependent_ids",
      "string": "Prerequisites",
      "inverse_string": "Dependent Courses"
    }
  ]
}
```

Hierarchical is a model-level flag, not a relationship entry:

```json
{
  "models": [
    {
      "name": "university.department",
      "hierarchical": true,
      "fields": [...]
    }
  ]
}
```

### Pattern 1: Through-Model Synthesis (M2M with Extra Fields)

**What:** A `m2m_through` relationship declaration generates a new model with two Many2one fields linking the `from` and `to` models, plus any extra `through_fields`.

**When to use:** When users need attributes on the relationship itself (grades on enrollment, roles on membership, etc.).

**How it works:**

```python
def _process_relationships(spec: dict[str, Any]) -> dict[str, Any]:
    """Pre-process relationships section, synthesizing through-models.

    Returns a new spec dict with:
    - Through-models appended to spec["models"]
    - Self-referential M2M fields enriched with relation/column params
    - Hierarchical model flags preserved (processed later in _build_model_context)
    """
    relationships = spec.get("relationships", [])
    if not relationships:
        return spec

    new_models = list(spec.get("models", []))

    for rel in relationships:
        if rel["type"] == "m2m_through":
            through_model = _synthesize_through_model(rel, spec)
            new_models.append(through_model)
            # Also inject One2many on parent models pointing to through-model
            _inject_one2many_links(new_models, rel)
        elif rel["type"] == "self_m2m":
            _enrich_self_referential_m2m(new_models, rel)

    return {**spec, "models": new_models}
```

**Generated through-model example:**

```python
# Generated: models/university_enrollment.py
from odoo import fields, models

class UniversityEnrollment(models.Model):
    _name = "university.enrollment"
    _description = "Course Enrollment"

    course_id = fields.Many2one(
        comodel_name="university.course",
        string="Course",
        required=True,
        ondelete="cascade",
    )
    student_id = fields.Many2one(
        comodel_name="university.student",
        string="Student",
        required=True,
        ondelete="cascade",
    )
    grade = fields.Float(
        string="Grade",
    )
    enrollment_date = fields.Date(
        string="Enrollment Date",
        default=fields.Date.today,
    )
```

**On parent models, One2many fields are injected:**

```python
# On university.course model:
enrollment_ids = fields.One2many(
    comodel_name="university.enrollment",
    inverse_name="course_id",
    string="Enrollments",
)

# On university.student model:
enrollment_ids = fields.One2many(
    comodel_name="university.enrollment",
    inverse_name="student_id",
    string="Enrollments",
)
```

### Pattern 2: Self-Referential M2M

**What:** A `self_m2m` relationship enriches Many2many fields with explicit `relation`, `column1`, `column2` parameters to prevent PostgreSQL table name collisions.

**When to use:** Course prerequisites, product alternatives, partner relations -- any M2M where comodel equals model.

**Odoo-verified parameters (from Odoo ORM source):**

```python
# Source: Odoo forum + ORM API docs
prerequisite_ids = fields.Many2many(
    comodel_name="university.course",
    relation="university_course_prerequisite_rel",  # explicit table name
    column1="course_id",                             # FK to this record
    column2="prerequisite_id",                       # FK to related record
    string="Prerequisites",
)

# Inverse field (optional, enables bidirectional navigation)
dependent_ids = fields.Many2many(
    comodel_name="university.course",
    relation="university_course_prerequisite_rel",  # SAME table
    column1="prerequisite_id",                       # REVERSED
    column2="course_id",                             # REVERSED
    string="Dependent Courses",
)
```

**Key rule:** When both fields share the same `relation` table, `column1` and `column2` must be swapped between them. The ORM enforces that two M2M fields can share a relation table only if they use the same model, comodel, and explicit relation params.

**Template change needed** -- current Many2many rendering does not output `relation`, `column1`, `column2`:

```jinja2
{% elif field.type in ('Many2one', 'One2many', 'Many2many') %}
    {{ field.name }} = fields.{{ field.type }}(
        comodel_name="{{ field.comodel_name }}",
{% if field.type == 'One2many' %}
        inverse_name="{{ field.inverse_name }}",
{% endif %}
{% if field.type == 'Many2many' and field.relation is defined %}
        relation="{{ field.relation }}",
        column1="{{ field.column1 }}",
        column2="{{ field.column2 }}",
{% endif %}
{% if field.ondelete is defined %}
        ondelete="{{ field.ondelete }}",
{% endif %}
        string="{{ field.string | default(field.name | replace('_', ' ') | title) }}",
{% if field.required is defined and field.required %}
        required=True,
{% endif %}
{% if field.help is defined %}
        help="{{ field.help }}",
{% endif %}
    )
```

### Pattern 3: Hierarchical Model (`hierarchical: true`)

**What:** A model-level `hierarchical: true` flag auto-injects `parent_id`, `child_ids`, `parent_path` fields and sets `_parent_name` and `_parent_store = True` on the class.

**Odoo-verified pattern (from ORM API docs + Odoo source):**

```python
# Source: Odoo 17.0 ORM API reference
class UniversityDepartment(models.Model):
    _name = "university.department"
    _description = "Department"
    _parent_name = "parent_id"
    _parent_store = True

    parent_id = fields.Many2one(
        comodel_name="university.department",
        string="Parent Department",
        index=True,
        ondelete="cascade",
    )
    child_ids = fields.One2many(
        comodel_name="university.department",
        inverse_name="parent_id",
        string="Child Departments",
    )
    parent_path = fields.Char(
        index=True,
        unaccent=False,
    )
```

**Key details:**
- `_parent_store = True` enables automatic `parent_path` computation
- `_parent_name = "parent_id"` is the default but should be explicit
- `parent_path` MUST have `index=True` and `unaccent=False`
- `parent_id` should have `ondelete="cascade"` and `index=True`
- `child_ids` is the inverse One2many

**Template changes:** Need new context keys `is_hierarchical`, `hierarchical_fields` and template blocks for `_parent_name`/`_parent_store` class attributes.

### Recommended Implementation Order

1. Design the spec format for `relationships` section and `hierarchical` flag
2. Implement `_process_relationships()` preprocessor function
3. Implement `_synthesize_through_model()` for m2m_through
4. Implement `_enrich_self_referential_m2m()` for self_m2m
5. Extend `_build_model_context()` with hierarchical detection and new context keys
6. Update `model.py.j2` templates (both 17.0 and 18.0) for:
   - Many2many `relation`/`column1`/`column2` rendering
   - `ondelete` parameter rendering
   - `_parent_name` and `_parent_store` class attributes
   - Hierarchical field injection
7. Update `init_models.py.j2` to include through-model imports
8. Update `access_csv.j2` to include through-model ACL entries
9. Update `render_module()` to call `_process_relationships()` before the render loop
10. Write tests for all three relationship patterns

### Anti-Patterns to Avoid

- **Mutating the original spec in `_process_relationships()`:** Return a new spec dict using `{**spec, "models": new_models}`. The preprocessor MUST be pure -- no side effects on the input spec.
- **Using the raw M2M table as a through-model (Integer FK columns):** The old Odoo pattern of creating a model on the same `_table` as the M2M relation table with Integer FK columns is fragile and undocumented. Use a proper model with Many2one fields instead (the One2many approach).
- **Forgetting `ondelete="cascade"` on through-model FKs:** If the parent record is deleted, orphaned through-model records cause integrity errors. Always cascade.
- **Forgetting `unaccent=False` on `parent_path`:** Without this, PostgreSQL's unaccent extension can corrupt path queries. Odoo explicitly sets this to False.
- **Generating `parent_path` as a visible form field:** `parent_path` is an internal index field. It should NOT appear in form/tree views. The context builder should exclude it from view-relevant field lists.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Through-model generation | Manual model definition for each M2M-with-fields | Synthesize from `relationships` spec | Through-models are boilerplate: two M2one FKs + extra fields + ACL + init import. Synthesis eliminates 4 manual steps per relationship |
| Self-referential M2M params | Users manually calculate relation table names | Auto-generate `relation`, `column1`, `column2` from model name + field name | Table name collisions are the #1 self-referential M2M bug; auto-generation prevents it |
| Hierarchical field injection | Users manually add parent_id + child_ids + parent_path | Auto-inject from `hierarchical: true` flag | Three fields + two class attributes is error-prone; forgetting `unaccent=False` on parent_path is a common bug |

**Key insight:** The value of this phase is not in generating code users could write manually -- it is in preventing the 4-5 subtle mistakes each pattern requires avoiding (cascade deletion, table name collisions, parent_path indexing, ACL entries for through-models, init imports).

## Common Pitfalls

### Pitfall 1: PostgreSQL Table Name Collision on Self-Referential M2M
**What goes wrong:** Two Many2many fields on the same model pointing to itself use the auto-generated relation table name, causing `duplicate key value violates unique constraint` or `relation already exists` errors.
**Why it happens:** Odoo auto-generates the M2M table name from `{model_table}_{comodel_table}_rel`. When model equals comodel, both fields get the same table name.
**How to avoid:** Always generate explicit `relation` parameter. Convention: `{module_name}_{model_table}_{field_name}_rel`.
**Warning signs:** PostgreSQL errors mentioning duplicate relation tables at module install.

### Pitfall 2: Through-Model Missing from `__init__.py`
**What goes wrong:** The synthesized through-model .py file exists but is not imported, so Odoo never registers it. The module installs but the through-model table is never created.
**Why it happens:** `init_models.py.j2` iterates over `spec["models"]`, but through-models were appended after the original spec was used to build the module context.
**How to avoid:** Call `_process_relationships()` BEFORE `_build_module_context()` so through-models are in the models list when `init_models.py.j2` renders.
**Warning signs:** Missing database table for through-model; Many2one fields on parent models referencing non-existent comodel.

### Pitfall 3: Through-Model Missing ACL Entry
**What goes wrong:** The through-model has no `ir.model.access.csv` entry, so users get `Access Denied` when trying to create enrollment records.
**Why it happens:** `access_csv.j2` iterates over `spec["models"]` -- if through-models are not in that list, they get no ACL.
**How to avoid:** Same fix as Pitfall 2 -- ensure through-models are in the models list before rendering. The existing `access_csv.j2` template will handle them automatically.
**Warning signs:** `AccessError: You are not allowed to access 'Course Enrollment' (university.enrollment)` at runtime.

### Pitfall 4: `parent_path` Appearing in Form Views
**What goes wrong:** The auto-injected `parent_path` field appears as a text input in the form view, confusing users.
**Why it happens:** The view template renders ALL fields from the model.
**How to avoid:** Mark `parent_path` as an internal field (e.g., `"internal": true` or `"invisible": true`) so the view template excludes it from forms. The `_build_model_context()` should filter it from the regular fields list for view rendering.
**Warning signs:** A "Parent Path" text field with values like "1/3/7/" visible in the form.

### Pitfall 5: Duplicate One2many Injection on Parent Models
**What goes wrong:** If a user already declared an `enrollment_ids` One2many on their course model, the synthesizer injects a duplicate.
**Why it happens:** No deduplication check before injection.
**How to avoid:** Check `any(f.get("name") == target_name for f in model["fields"])` before injecting the One2many field.
**Warning signs:** Duplicate field definition errors at module install.

### Pitfall 6: Through-Model Field Name Collision
**What goes wrong:** The auto-generated Many2one field names (`course_id`, `student_id`) collide with existing fields on the through-model.
**Why it happens:** The naming convention `{model_last_part}_id` may conflict with user-defined through_fields.
**How to avoid:** Derive FK field names from the model name, but check for collisions with `through_fields` names. If collision, raise a clear error at spec processing time.

## Code Examples

### Spec Format: M2M Through Relationship

```json
{
  "type": "m2m_through",
  "from": "university.course",
  "to": "university.student",
  "through_model": "university.enrollment",
  "through_fields": [
    {"name": "grade", "type": "Float", "string": "Grade"},
    {"name": "enrollment_date", "type": "Date", "default": "fields.Date.today"}
  ]
}
```

### Spec Format: Self-Referential M2M

```json
{
  "type": "self_m2m",
  "model": "university.course",
  "field_name": "prerequisite_ids",
  "inverse_field_name": "dependent_ids",
  "string": "Prerequisites",
  "inverse_string": "Dependent Courses"
}
```

### Through-Model Synthesis Function

```python
# Source: project pattern from _build_model_context, Odoo ORM conventions
def _synthesize_through_model(
    rel: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    """Synthesize a through-model dict from a m2m_through relationship.

    Returns a model dict suitable for appending to spec["models"].
    """
    from_model = rel["from"]
    to_model = rel["to"]
    through_name = rel["through_model"]

    # Derive FK field names from model names
    from_fk = _to_python_var(from_model.rsplit(".", 1)[-1]) + "_id"
    to_fk = _to_python_var(to_model.rsplit(".", 1)[-1]) + "_id"

    # Build fields list: two required M2one + extra through_fields
    through_fields = [
        {
            "name": from_fk,
            "type": "Many2one",
            "comodel_name": from_model,
            "string": from_model.rsplit(".", 1)[-1].replace("_", " ").title(),
            "required": True,
            "ondelete": "cascade",
        },
        {
            "name": to_fk,
            "type": "Many2one",
            "comodel_name": to_model,
            "string": to_model.rsplit(".", 1)[-1].replace("_", " ").title(),
            "required": True,
            "ondelete": "cascade",
        },
    ]
    through_fields.extend(rel.get("through_fields", []))

    return {
        "name": through_name,
        "description": through_name.rsplit(".", 1)[-1].replace("_", " ").title(),
        "fields": through_fields,
        "_synthesized": True,  # flag for template awareness
    }
```

### Self-Referential M2M Enrichment

```python
def _enrich_self_referential_m2m(
    models: list[dict[str, Any]], rel: dict[str, Any]
) -> None:
    """Enrich model fields list with self-referential M2M params.

    Adds/updates fields with relation, column1, column2 to prevent
    PostgreSQL table name collisions.
    """
    model_name = rel["model"]
    target_model = next((m for m in models if m["name"] == model_name), None)
    if target_model is None:
        return

    table_base = _to_python_var(model_name)
    field_name = rel["field_name"]
    relation_table = f"{table_base}_{field_name}_rel"

    # Primary field
    primary_field = {
        "name": field_name,
        "type": "Many2many",
        "comodel_name": model_name,
        "relation": relation_table,
        "column1": f"{table_base}_id",
        "column2": f"{field_name.rstrip('_ids')}_id",
        "string": rel.get("string", field_name.replace("_", " ").title()),
    }

    # Inverse field (optional)
    inverse_name = rel.get("inverse_field_name")
    inverse_field = None
    if inverse_name:
        inverse_field = {
            "name": inverse_name,
            "type": "Many2many",
            "comodel_name": model_name,
            "relation": relation_table,
            "column1": f"{field_name.rstrip('_ids')}_id",  # REVERSED
            "column2": f"{table_base}_id",                   # REVERSED
            "string": rel.get("inverse_string", inverse_name.replace("_", " ").title()),
        }

    # Replace or append fields on the target model
    fields = list(target_model.get("fields", []))
    fields = [f for f in fields if f.get("name") not in (field_name, inverse_name)]
    fields.append(primary_field)
    if inverse_field:
        fields.append(inverse_field)
    target_model["fields"] = fields
```

### Hierarchical Model Detection in `_build_model_context()`

```python
# In _build_model_context(), after Phase 26 monetary detection:

# Phase 27: hierarchical model detection
is_hierarchical = model.get("hierarchical", False)
if is_hierarchical:
    # Inject parent_id, child_ids, parent_path if not already present
    field_names = {f.get("name") for f in fields}
    hierarchical_injections = []
    if "parent_id" not in field_names:
        hierarchical_injections.append({
            "name": "parent_id",
            "type": "Many2one",
            "comodel_name": model["name"],
            "string": "Parent",
            "index": True,
            "ondelete": "cascade",
        })
    if "child_ids" not in field_names:
        hierarchical_injections.append({
            "name": "child_ids",
            "type": "One2many",
            "comodel_name": model["name"],
            "inverse_name": "parent_id",
            "string": "Children",
        })
    if "parent_path" not in field_names:
        hierarchical_injections.append({
            "name": "parent_path",
            "type": "Char",
            "index": True,
            "internal": True,  # exclude from views
        })
    if hierarchical_injections:
        fields = [*fields, *hierarchical_injections]
```

### Template: Hierarchical Class Attributes

```jinja2
{# In model.py.j2, after _inherit but before fields #}
{% if is_hierarchical %}
    _parent_name = "parent_id"
    _parent_store = True
{% endif %}
```

### Template: Many2many with relation/column params

```jinja2
{# Updated relational field branch in model.py.j2 #}
{% elif field.type in ('Many2one', 'One2many', 'Many2many') %}
    {{ field.name }} = fields.{{ field.type }}(
        comodel_name="{{ field.comodel_name }}",
{% if field.type == 'One2many' %}
        inverse_name="{{ field.inverse_name }}",
{% endif %}
{% if field.type == 'Many2many' and field.relation is defined %}
        relation="{{ field.relation }}",
        column1="{{ field.column1 }}",
        column2="{{ field.column2 }}",
{% endif %}
        string="{{ field.string | default(field.name | replace('_', ' ') | title) }}",
{% if field.required is defined and field.required %}
        required=True,
{% endif %}
{% if field.index is defined and field.index %}
        index=True,
{% endif %}
{% if field.ondelete is defined %}
        ondelete="{{ field.ondelete }}",
{% endif %}
{% if field.help is defined %}
        help="{{ field.help }}",
{% endif %}
    )
```

### Template: parent_path (Char with special params)

```jinja2
{# In the Char/generic branch, handle parent_path specially #}
{% if field.name == 'parent_path' and is_hierarchical %}
    parent_path = fields.Char(
        index=True,
        unaccent=False,
    )
{% elif ... %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual through-model creation | Synthesized from `relationships` spec | Phase 27 (this phase) | Users declare intent, generator handles boilerplate |
| No self-referential M2M support | Auto-generated relation/column params | Phase 27 (this phase) | Prevents table name collision bugs |
| Manual hierarchical model setup | `hierarchical: true` flag | Phase 27 (this phase) | Eliminates 5 manual steps (3 fields + 2 class attrs) |
| M2M template: comodel_name only | M2M template: + relation, column1, column2, ondelete | Phase 27 (this phase) | Enables all M2M parameter scenarios |

## Open Questions

1. **Should through-model names be auto-generated or user-specified?**
   - What we know: The spec format above requires `through_model` name. This is explicit and clear.
   - What's unclear: Could we auto-derive it (e.g., `{from_last}_{to_last}_rel`)?
   - Recommendation: Require `through_model` name in spec. Auto-generation would produce awkward names like `course_student_rel` instead of domain-meaningful `enrollment`. User knows the domain better.

2. **Should the inverse One2many on parent models be auto-injected or user-declared?**
   - What we know: Users need to access enrollments from both course and student. Auto-injection is convenient.
   - What's unclear: What should the injected field name be? `enrollment_ids`? `{through_model_last_part}_ids`?
   - Recommendation: Auto-inject with name `{through_model_last_part}_ids` (e.g., `enrollment_ids`). Check for duplicates before injection. Users can override by declaring the field themselves.

3. **Should `_process_relationships()` mutate models or return new ones?**
   - What we know: Project coding style mandates immutability.
   - Recommendation: Return a new spec dict with new models list. However, the self-referential M2M enrichment modifies field lists in-place for simplicity. Since the preprocessor operates on a copy of the spec, this is acceptable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `python/pyproject.toml` |
| Quick run command | `cd python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q -k relationship` |
| Full suite command | `cd python && .venv/bin/python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPEC-02a | M2M through relationship generates through-model with extra fields + two M2one links | unit | `pytest tests/test_renderer.py::TestProcessRelationshipsM2MThrough -x` | Wave 0 |
| SPEC-02b | Through-model gets One2many injected on parent models | unit | `pytest tests/test_renderer.py::TestProcessRelationshipsM2MThrough -x` | Wave 0 |
| SPEC-02c | Self-referential M2M generates relation, column1, column2 params | unit | `pytest tests/test_renderer.py::TestProcessRelationshipsSelfM2M -x` | Wave 0 |
| SPEC-02d | Self-referential M2M inverse field has reversed column params | unit | `pytest tests/test_renderer.py::TestProcessRelationshipsSelfM2M -x` | Wave 0 |
| SPEC-02e | `hierarchical: true` injects parent_id, child_ids, parent_path | unit | `pytest tests/test_renderer.py::TestBuildModelContextHierarchical -x` | Wave 0 |
| SPEC-02f | Hierarchical model has _parent_name and _parent_store in rendered output | integration | `pytest tests/test_render_stages.py::TestRenderModelsHierarchical -x` | Wave 0 |
| SPEC-02g | Through-model appears in rendered `models/__init__.py` | integration | `pytest tests/test_render_stages.py::TestRenderManifestThroughModel -x` | Wave 0 |
| SPEC-02h | Through-model has ACL entries in `ir.model.access.csv` | integration | `pytest tests/test_render_stages.py::TestRenderSecurityThroughModel -x` | Wave 0 |
| SPEC-02i | Rendered Many2many with relation/column params produces correct Python | integration | `pytest tests/test_render_stages.py::TestRenderModelsSelfM2M -x` | Wave 0 |
| SPEC-02j | Duplicate One2many injection is prevented | unit | `pytest tests/test_renderer.py::TestProcessRelationshipsM2MThrough::test_no_duplicate_injection -x` | Wave 0 |
| SPEC-02k | parent_path excluded from form view rendering | unit | `pytest tests/test_renderer.py::TestBuildModelContextHierarchical::test_parent_path_excluded_from_views -x` | Wave 0 |
| SPEC-02l | Through-model ondelete=cascade on FK fields | integration | `pytest tests/test_render_stages.py::TestRenderModelsThroughModel -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q`
- **Per wave merge:** `cd python && .venv/bin/python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_renderer.py::TestProcessRelationshipsM2MThrough` -- through-model synthesis tests
- [ ] `tests/test_renderer.py::TestProcessRelationshipsSelfM2M` -- self-referential M2M enrichment tests
- [ ] `tests/test_renderer.py::TestBuildModelContextHierarchical` -- hierarchical context key tests
- [ ] `tests/test_render_stages.py::TestRenderModelsHierarchical` -- rendered hierarchical model output
- [ ] `tests/test_render_stages.py::TestRenderManifestThroughModel` -- init.py includes through-model
- [ ] `tests/test_render_stages.py::TestRenderSecurityThroughModel` -- ACL entries for through-model
- [ ] `tests/test_render_stages.py::TestRenderModelsSelfM2M` -- M2M with relation/column rendered
- [ ] `tests/test_render_stages.py::TestRenderModelsThroughModel` -- through-model rendered output

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `renderer.py` (813 lines, `_build_model_context()` at line 193, render pipeline, template loading)
- Codebase analysis: `17.0/model.py.j2` and `18.0/model.py.j2` (identical structure, relational field branch at lines 42-54)
- Codebase analysis: `shared/access_csv.j2` (iterates `models` and `spec_wizards` -- through-models will be picked up if in models list)
- Codebase analysis: `shared/init_models.py.j2` (iterates `models` -- through-models will be auto-imported)
- [Odoo 17.0 ORM API Reference](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html) -- Many2many params, _parent_store, _parent_name
- [Odoo Forum: Self-referential M2M](https://www.odoo.com/forum/help-1/model-with-many2many-relation-to-his-self-87223) -- relation/column1/column2 pattern verified

### Secondary (MEDIUM confidence)
- [Odoo Forum: M2M with attributes](https://www.odoo.com/forum/help-1/many2many-relation-with-attributes-37710) -- through-model pattern via intermediate model with M2one fields
- [Hynsys: Hierarchical Models in Odoo](https://www.hynsys.com/blog/odoo-development-5/hierarchical-models-in-odoo-6) -- parent_id + child_ids + parent_path + _parent_store pattern
- [Odoo Forum: Multiple M2M on same model](https://www.odoo.com/forum/help-1/how-to-keep-multiple-many2many-fields-on-the-same-model-145401) -- ORM enforcement of unique relation params

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure spec-processing + template logic
- Architecture: HIGH -- follows established `_build_model_context()` enrichment pattern + preprocessor pattern; M2M params and hierarchical patterns verified against Odoo ORM docs
- Pitfalls: HIGH -- 6 pitfalls documented, all verified via Odoo forum reports and ORM source behavior

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain -- Odoo relational field API unchanged since v10)
