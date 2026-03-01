---
name: odoo-gen:validate
description: Run pylint-odoo and Docker-based validation on an Odoo module
argument-hint: "[module_path]"
---
<objective>
Run comprehensive validation on an Odoo module using pylint-odoo for static analysis and Docker-based Odoo 17.0 for installation and runtime testing.

**This command is not yet available.** It will be implemented in Phase 3 (Validation Infrastructure).

Run `/odoo-gen:help` to see currently available commands.
</objective>

<planned_capabilities>
When activated in Phase 3, this command will:

1. Run pylint-odoo on all Python and XML files in the target module
2. Report violations with file path, line number, rule code, and fix suggestions
3. Optionally spin up a Docker Odoo 17.0 + PostgreSQL environment
4. Attempt module installation on the Docker instance and report success or failure
5. Run the module's test suite on the Docker instance and report per-test results
6. Parse Odoo error logs to provide actionable diagnosis when validation fails
7. Enforce Odoo 17.0 API exclusively (flag deprecated patterns from older versions)
</planned_capabilities>
