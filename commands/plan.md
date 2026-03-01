---
name: odoo-gen:plan
description: Plan module architecture before generation
argument-hint: "<module description>"
---
<objective>
Create a detailed module architecture plan before generation, including model design, field specifications, view layout, security groups, and workflow states.

**This command is not yet available.** It will be implemented in Phase 4 (Input & Specification).

Run `/odoo-gen:help` to see currently available commands.
</objective>

<planned_capabilities>
When activated in Phase 4, this command will:

1. Accept a natural language module description
2. Ask targeted Odoo-specific follow-up questions about models, fields, views, inheritance, and user groups
3. Produce a structured module specification:
   - Model names and relationships
   - Field types and constraints
   - View layouts (form, list, search)
   - Security group hierarchy
   - Workflow states and transitions
4. Present the specification for user review and approval
5. Allow iterative refinement before passing to generation
</planned_capabilities>
