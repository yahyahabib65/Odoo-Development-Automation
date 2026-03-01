---
name: odoo-gen:extend
description: Fork and extend an existing Odoo module
argument-hint: "<module_name or github_url>"
---
<objective>
Fork an existing Odoo module from OCA or GitHub and generate delta code to extend it with new functionality matching your specification.

**This command is not yet available.** It will be implemented in Phase 8 (Search & Fork-Extend).

Run `/odoo-gen:help` to see currently available commands.
</objective>

<planned_capabilities>
When activated in Phase 8, this command will:

1. Accept a module name or GitHub URL as the fork source
2. Clone the source module and analyze its structure (models, views, security, tests)
3. Compare the source module's features with your refined specification
4. Generate delta code to add missing functionality while preserving the original module's architecture
5. Create proper Odoo inheritance (`_inherit`) for extending existing models
6. Generate additional views, security rules, and tests for the new functionality
7. Produce a complete extended module ready for installation
</planned_capabilities>
