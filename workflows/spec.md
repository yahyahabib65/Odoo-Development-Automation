# Specification Workflow

End-to-end workflow for `/odoo-gen:plan`. Referenced by the `odoo-scaffold` agent and the `plan` command.

## Overview

This workflow defines the complete specification pipeline:

1. **Parse Natural Language Description** -- Parse module description into a draft specification
2. **Tiered Follow-Up Questions** -- Ask targeted Odoo-specific questions to refine the spec
3. **Generate Structured Specification** -- Build the complete spec.json from answers
4. **Present Specification for Approval** -- Render as markdown, wait for user approval

Unlike the scaffold workflow (`scaffold.md`) which goes from description to code directly, this workflow produces a reviewed, committed specification as the generation contract.

---

## Phase 1: Parse Natural Language Description

Receive the module description from `$ARGUMENTS` and parse it into a draft specification.

### Steps

1. **Extract the description** from `$ARGUMENTS`:
   ```
   /odoo-gen:plan "equipment maintenance tracking with work orders and technician assignments"
   ```

2. **Infer module technical name** -- Convert the description to `snake_case`:
   - Remove stop words (a, an, the, with, and, for, of, in, to, from)
   - Take the first 2-3 key nouns as the module name
   - Convert to snake_case
   - Examples:
     - "equipment maintenance tracking" -> `equipment_maintenance`
     - "HR leave management system" -> `hr_leave_management`
     - "customer portal for invoices" -> `customer_portal`

3. **Infer module title** -- Human-readable version of the technical name:
   - `equipment_maintenance` -> "Equipment Maintenance"
   - `hr_leave_management` -> "HR Leave Management"

4. **Infer summary** -- One-line description from the user's input, trimmed and cleaned.

5. **Infer category** -- Map the description to an Odoo module category:
   | Description Domain | Odoo Category |
   |--------------------|---------------|
   | inventory, stock, warehouse | Inventory |
   | sales, quotation, deal | Sales |
   | purchase, procurement, vendor | Purchases |
   | accounting, invoice, payment, journal | Accounting |
   | HR, employee, leave, attendance, payroll | Human Resources |
   | project, task, timesheet | Project |
   | CRM, lead, opportunity, pipeline | Sales/CRM |
   | website, portal, e-commerce | Website |
   | manufacturing, production, BOM | Manufacturing |
   | maintenance, repair, equipment | Maintenance |
   | fleet, vehicle | Fleet |
   | Default (no clear match) | Uncategorized |

6. **Extract draft models** -- Identify models from nouns and noun phrases in the description:
   - Use Odoo dot-notation: `{module_prefix}.{entity}`
   - Singular form for model names (e.g., "work orders" -> `module.work_order`)
   - Examples:
     - "equipment" -> `maintenance.equipment`
     - "work orders" -> `maintenance.work_order`
     - "technician assignments" -> `maintenance.assignment`

7. **Infer draft fields for each model** -- Use the keyword-to-type mapping table to assign field types:

   | Keyword Pattern | Odoo Field Type | Default Config |
   |----------------|-----------------|----------------|
   | name, title | Char | required=True |
   | description, notes, comment, body | Text | |
   | email | Char | widget="email" |
   | phone | Char | widget="phone" |
   | url, website, link | Char | widget="url" |
   | amount, price, cost, total | Float | digits=(16,2); use Monetary if currency field present |
   | quantity, count, number, pages, age | Integer | |
   | percentage, rate, ratio | Float | digits=(5,2) |
   | date, deadline, start_date, end_date | Date | |
   | datetime, timestamp, created, updated | Datetime | |
   | active, is_*, has_* | Boolean | default=True for active |
   | image, photo, avatar | Binary | |
   | state, status | Selection | default="draft" |
   | type, kind | Selection | |
   | color | Integer | (Odoo color widget index) |
   | priority | Selection | [("0","Normal"),("1","Low"),("2","High"),("3","Urgent")] |
   | sequence | Integer | default=10 |
   | partner, customer, vendor, supplier | Many2one("res.partner") | |
   | user, responsible, assigned, salesperson | Many2one("res.users") | |
   | company | Many2one("res.company") | index=True |
   | currency | Many2one("res.currency") | |
   | tag, category (plural context) | Many2many | |
   | line, detail, item (plural context) | One2many | |

   **Always include per model:**
   - `name` (Char, required=True) -- Display name / `_rec_name`
   - `active` (Boolean, default=True) -- Archiving support

8. **Determine dependencies** -- Always start with `["base"]`, then add:
   | Description Mentions | Add Dependency |
   |---------------------|----------------|
   | notifications, messages, chatter, followers, tracking | `mail` |
   | inventory, stock, warehouse, picking | `stock` |
   | sales, quotation, sale order | `sale` |
   | purchase, vendor, supplier, procurement | `purchase` |
   | accounting, invoice, payment, journal | `account` |
   | website, portal, public | `website` |
   | HR, employee, department, leave | `hr` |
   | project, task, timesheet | `project` |
   | CRM, lead, opportunity, pipeline | `crm` |
   | product, variant, pricelist | `product` |
   | maintenance, equipment | `maintenance` |
   | fleet, vehicle | `fleet` |

   If any model will use chatter (messages, activity tracking), add `mail` to depends.

9. **Read defaults** -- Check `~/.claude/odoo-gen/defaults.json` for:
   - `odoo_version` (default: "17.0")
   - `license` (default: "LGPL-3")
   - `author` (default: "")
   - `website` (default: "")

   If `defaults.json` cannot be read, use hardcoded defaults: `17.0`, `LGPL-3`, empty author and website.

---

## Phase 2: Tiered Follow-Up Questions

Ask targeted, Odoo-specific follow-up questions to refine the draft specification. Questions are informed by the knowledge base (`@~/.claude/odoo-gen/knowledge/`) and reference real Odoo concepts.

### Tier 1 (Always Asked -- 3-5 Questions)

Present these as a numbered list and **wait for user answers** before proceeding:

1. **Models & Entities**: "Based on your description, I identified these data entities: [list inferred models with brief descriptions]. Are these the right models? Should any be added, removed, or renamed?"

2. **User Groups**: "Who will use this module? The typical Odoo pattern is a **User** group (read/write/create access) and a **Manager** group (full access including delete). Do you need different roles or additional access levels?"

3. **Module Integration**: "Should this module extend or integrate with existing Odoo apps? I inferred these dependencies: [list inferred depends]. Do you need integration with any others? Common choices:
   - `stock` (inventory/warehouse)
   - `sale` (sales orders)
   - `purchase` (purchase orders)
   - `hr` (employees/departments)
   - `account` (accounting/invoicing)
   - `website` (portal/public access)"

4. **Workflow/Status**: "Should records have a workflow? Odoo supports state-based workflows with button transitions and group-based approval. For example: **Draft -> Confirmed -> In Progress -> Done**. Describe your workflow if needed, or say 'no workflow' for simple data entry."

5. **(Conditional -- only if description mentions customer/portal/website/public)** **Portal Access**: "Should external users (customers or vendors) see this data through the Odoo portal? If so, what data should be visible and should they be able to edit it?"

### Complexity Detection

After receiving Tier 1 answers, scan the answers for complexity triggers:

| Trigger Keywords | Complexity Signal | Tier 2 Question |
|-----------------|-------------------|-----------------|
| approval, validate, confirm, sign-off | Workflow Complexity | "What are the specific states and transitions? Who can approve at each step? Should approval be restricted to managers?" |
| multi-company, branch, subsidiary, company-specific | Multi-company | "Should records be company-specific (isolated per company) or shared across companies? Odoo supports `company_id` fields with record rules for multi-company isolation." |
| extend, inherit, add field to, modify existing, customize | Inheritance | "Which specific existing Odoo models should be extended? What fields or views should be added to them? Odoo supports three inheritance patterns: classical (_inherit), prototype (_inherits), and delegation." |
| portal, website, public, customer access, vendor access | Portal Access | "What data should portal users see? Read-only or editable? Which specific fields should be visible? Should they be able to create new records?" |
| report, dashboard, KPI, analytics, statistics, chart | Reporting | "What metrics or KPIs matter most? What dimensions should data be grouped by (e.g., date, user, status)? Do you need pivot tables, charts, or both?" |
| import, export, sync, API, external, integration | External Integration | "What external systems need data exchange? What format (CSV, XML, REST API)? Inbound, outbound, or bidirectional?" |
| schedule, cron, automated, recurring, automatic, periodic | Automation | "What should happen automatically? At what frequency? What triggers the action? Odoo supports scheduled actions (ir.cron) and automated actions (base.automation)." |

### Tier 2 (Conditional -- 0-3 Questions)

Only ask Tier 2 questions for detected complexity signals. **Maximum 3 additional questions.** If no complexity is detected, skip Tier 2 entirely and proceed to Phase 3.

When selecting which Tier 2 questions to ask (if more than 3 are triggered), prioritize:
1. Workflow (affects model structure and views most)
2. Inheritance (affects model definitions fundamentally)
3. Multi-company / Portal / Reporting / Integration / Automation (by relevance to description)

### Question Guidelines

- Questions MUST be **Odoo-specific**, not generic. Reference Odoo concepts (workflow states, record rules, ir.cron, mail.thread, etc.).
- Use the knowledge base to inform questions. For example, if the user mentions "approval", reference the workflow state pattern from `knowledge/models.md`.
- **Total maximum: 8 questions** (5 Tier 1 + 3 Tier 2). Avoid interrogation fatigue.
- If user gives brief/unclear answers, **infer reasonable defaults** and show them for confirmation rather than asking more questions.

After all answers are collected, proceed to Phase 3.

---

## Phase 3: Generate Structured Specification

Build the complete `spec.json` from the parsed description (Phase 1) and user answers (Phase 2). The JSON schema **extends** the `render-module` input format and is fully backward-compatible.

### Specification JSON Schema

```json
{
  "module_name": "snake_case_name",
  "module_title": "Human Readable Name",
  "summary": "One-line module description",
  "author": "from defaults.json",
  "website": "from defaults.json",
  "license": "from defaults.json (default LGPL-3)",
  "category": "Inferred Odoo category",
  "odoo_version": "from defaults.json (default 17.0)",
  "application": true,
  "depends": ["base", "...inferred and confirmed..."],
  "models": [
    {
      "name": "module.entity",
      "description": "Human description",
      "_inherit": null,
      "inherit_mixins": [],
      "fields": [
        {
          "name": "field_name",
          "type": "FieldType",
          "string": "Label",
          "required": false,
          "default": null,
          "help": "Help text",
          "comodel_name": null,
          "inverse_name": null,
          "selection": null,
          "compute": null,
          "widget": null,
          "tracking": false,
          "copy": true,
          "index": false,
          "groups": null
        }
      ],
      "constraints": [],
      "workflow_states": [],
      "sql_constraints": []
    }
  ],
  "views": [
    {
      "model": "module.entity",
      "types": ["form", "tree", "search"],
      "custom_fields_in_tree": [],
      "custom_search_filters": []
    }
  ],
  "security_groups": [
    {
      "name": "group_module_user",
      "label": "User",
      "permissions": {"read": true, "write": true, "create": true, "unlink": false}
    },
    {
      "name": "group_module_manager",
      "label": "Manager",
      "implied_ids": ["group_module_user"],
      "permissions": {"read": true, "write": true, "create": true, "unlink": true}
    }
  ],
  "menu_structure": {
    "root_menu": "Module Title",
    "sub_menus": ["Entity One", "Entity Two"]
  },
  "demo_data_hints": ["3 sample records per model"]
}
```

### Spec Generation Rules

1. **Backward compatibility**: All new fields beyond the Phase 1 `render-module` format are **OPTIONAL** with `null` or empty defaults. An old-format spec passed to `render-module` will still work.

2. **Workflow states**: If the user described a workflow, populate `workflow_states` array with objects containing `key`, `label`, and `is_default` flag:
   ```json
   "workflow_states": [
     {"key": "draft", "label": "Draft", "is_default": true},
     {"key": "confirmed", "label": "Confirmed", "is_default": false},
     {"key": "done", "label": "Done", "is_default": false}
   ]
   ```
   Also add a `state` Selection field to the model with matching values.

3. **Inheritance**: If the user mentioned extending existing models, set `_inherit` on the model:
   ```json
   {"name": "res.partner", "_inherit": "res.partner", "fields": [...]}
   ```

4. **Chatter/tracking**: If the user wants messages, activity tracking, or chatter:
   - Add `["mail.thread", "mail.activity.mixin"]` to `inherit_mixins`
   - Add `"mail"` to `depends`
   - Set `tracking: true` on `state` and `name` fields

5. **Smart defaults**: Apply the keyword-to-type mapping from Phase 1 automatically:
   - Field named `partner_id` -> set `comodel_name: "res.partner"`
   - Field named `user_id` -> set `comodel_name: "res.users"`
   - Field named `company_id` -> set `comodel_name: "res.company"`, `index: true`
   - Field named `currency_id` -> set `comodel_name: "res.currency"`
   - Field named `state` -> set `tracking: true`, `default: "draft"`, `copy: false`
   - Field named `name` -> set `tracking: true`, `required: true`
   - Field named `active` -> set `default: true`

6. **Views**: Populate `views` array with `form` + `tree` + `search` for each model:
   - `custom_fields_in_tree`: Key fields to show in the tree view (name, state, key relational fields)
   - `custom_search_filters`: Fields to include as search filters (state, key relational fields, dates)

7. **Security groups**: Default to User/Manager hierarchy:
   - User: read, write, create (no unlink)
   - Manager: full access, `implied_ids` includes user group

8. **Menu structure**: Root menu = module title, sub-menus = one per model (using model description as label).

9. **Demo data hints**: Include `"3 sample records per model"` by default. If workflow states exist, add `"Include one record in each workflow state"`.

10. **Constraints**: If the user mentioned uniqueness or validation rules, add to `constraints` or `sql_constraints`:
    ```json
    "sql_constraints": [
      {"name": "unique_reference", "definition": "UNIQUE(reference)", "message": "Reference must be unique"}
    ]
    ```

### Validation Checks

Before proceeding to Phase 4, verify the spec:

- `module_name` is present and in `snake_case`
- All model names use dot-notation (`module.entity`)
- All field types are from the known set: `Char`, `Text`, `Integer`, `Float`, `Monetary`, `Boolean`, `Date`, `Datetime`, `Binary`, `Selection`, `Html`, `Many2one`, `One2many`, `Many2many`
- All `Many2one` fields have `comodel_name` set
- All `One2many` fields have `comodel_name` and `inverse_name` set
- All `Selection` fields have `selection` array set (or `compute` for dynamic)
- `depends` includes `"base"` at minimum
- `depends` includes `"mail"` if any model uses `inherit_mixins` with `mail.thread`

---

## Phase 4: Present Specification for Approval

Render the spec as a human-readable markdown summary and present it for user review.

### Presentation Format

Render the spec.json as structured markdown with these sections:

```markdown
## Module Specification: {module_title}

**Technical Name:** `{module_name}`
**Category:** {category}
**License:** {license}
**Odoo Version:** {odoo_version}
**Summary:** {summary}

### Dependencies

{comma-separated list of depends}

### Models

#### {model.description} (`{model.name}`)

{If _inherit is set: "Extends: `{_inherit}`"}
{If inherit_mixins is non-empty: "Mixins: {comma-separated mixins}"}

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| {field.name} | {field.type} | {Yes/No} | {default or -} | {field.help} |

{If workflow_states is non-empty:}
**Workflow:** {state1} -> {state2} -> {state3}

{If constraints is non-empty:}
**Constraints:** {list constraints}

#### {next model...}

### Security Groups

| Group | Permissions |
|-------|-------------|
| {group.label} | {read/write/create/unlink permissions} |

### Menu Structure

- {root_menu}
  - {sub_menu_1}
  - {sub_menu_2}

### Views

{For each model: form + tree + search}

### Demo Data

{demo_data_hints list}
```

### Approval Options

After presenting the summary, provide three options:

1. **Approve** -- "If this looks correct, say **approve** and I will commit the spec.json as the generation contract."
2. **Request changes** -- "Tell me what to change (e.g., 'add a priority field to work orders', 'remove the assignment model', 'change the workflow to Draft -> Review -> Approved -> Done') and I will update the spec."
3. **Edit directly** -- "You can describe modifications in natural language and I will update the spec accordingly."

**Wait for user response before proceeding.**

- On **approve**: Write `spec.json` to `./module_name/spec.json` and commit to git as the generation contract.
- On **request changes**: Update the spec based on feedback, re-run validation checks, and re-present for approval.
- On **edit directly**: Apply the user's described modifications, re-validate, and re-present.

This approval step is a **generation gate** -- no code generation begins until the user explicitly approves the specification.

---

## Error Handling

- **Empty `$ARGUMENTS`**: Prompt the user: "Please describe the module you need. For example: `/odoo-gen:plan 'equipment maintenance tracking with work orders and technician assignments'`"

- **Vague description (< 5 words)**: Infer a minimal spec and present it with: "I inferred the following from your brief description. Please confirm or provide more details so I can refine the specification."

- **defaults.json not readable**: Use hardcoded defaults:
  - `odoo_version`: "17.0"
  - `license`: "LGPL-3"
  - `author`: ""
  - `website`: ""

- **Invalid model/field names**: Automatically sanitize -- convert spaces to underscores, remove special characters, ensure dot-notation for models.

- **Conflicting answers**: If user answers contradict the draft spec (e.g., says "no workflow" but earlier mentioned "approval process"), flag the conflict and ask for clarification.

---

## References

- Agent: `agents/odoo-scaffold.md`
- Command: `commands/plan.md`
- Existing workflow: `workflows/scaffold.md` (pattern reference for quick mode)
- Knowledge base (loaded by agent for question generation):
  - `@~/.claude/odoo-gen/knowledge/MASTER.md` (global conventions)
  - `@~/.claude/odoo-gen/knowledge/models.md` (model patterns, field types, inheritance)
  - `@~/.claude/odoo-gen/knowledge/views.md` (view types, modifiers, widgets)
  - `@~/.claude/odoo-gen/knowledge/security.md` (groups, ACLs, record rules)
  - `@~/.claude/odoo-gen/knowledge/manifest.md` (manifest keys, depends)
  - `@~/.claude/odoo-gen/knowledge/inheritance.md` (inheritance patterns)
  - `@~/.claude/odoo-gen/knowledge/actions.md` (server actions, automated actions)
  - `@~/.claude/odoo-gen/knowledge/wizards.md` (transient models, wizard pattern)
  - `@~/.claude/odoo-gen/knowledge/data.md` (data files, email templates)
  - `@~/.claude/odoo-gen/knowledge/testing.md` (test patterns, TransactionCase)
  - `@~/.claude/odoo-gen/knowledge/controllers.md` (HTTP controllers, portal)
  - `@~/.claude/odoo-gen/knowledge/i18n.md` (translations, _() function)
- Defaults: `~/.claude/odoo-gen/defaults.json`
