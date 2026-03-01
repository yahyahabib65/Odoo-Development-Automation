---
name: odoo-gen:search
description: Semantically search GitHub/OCA for existing Odoo modules similar to your description
argument-hint: "<search query>"
---
<objective>
Semantically search GitHub and OCA repositories for existing Odoo modules that match your description, using vector-based similarity matching for intent-aware results.

**This command is not yet available.** It will be implemented in Phase 8 (Search & Fork-Extend).

Run `/odoo-gen:help` to see currently available commands.
</objective>

<planned_capabilities>
When activated in Phase 8, this command will:

1. Accept a natural language search query describing the module need
2. Search OCA and GitHub repositories using semantic matching (ChromaDB + sentence-transformers)
3. Return ranked results with relevance scores and feature overlap analysis
4. Present gap analysis showing which parts of your spec are already covered
5. Allow selection of a match to fork via `/odoo-gen:extend` or choose to build from scratch
6. Maintain a local vector index of OCA/GitHub module descriptions for fast matching
</planned_capabilities>
