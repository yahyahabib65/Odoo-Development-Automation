"""Pylint-odoo and Docker auto-fix loops with escalation.

Mechanically fixes known pylint-odoo violation codes and Docker error
patterns, re-validates, and escalates remaining issues in a grouped
file:line + suggestion format.

QUAL-09: pylint auto-fix (5 fixable codes, max 2 cycles)
QUAL-10: Docker auto-fix (4 fixable patterns, max 2 cycles)
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

from odoo_gen_utils.validation.pylint_runner import run_pylint_odoo
from odoo_gen_utils.validation.types import Violation

# -------------------------------------------------------------------------
# Constants (locked per CONTEXT.md Decision E)
# -------------------------------------------------------------------------

FIXABLE_PYLINT_CODES: frozenset[str] = frozenset({
    "W8113",  # redundant string= parameter on field
    "W8111",  # renamed field parameter
    "C8116",  # superfluous manifest key
    "W8150",  # absolute import should be relative
    "C8107",  # missing required manifest key
})

MAX_FIX_CYCLES: int = 2

FIXABLE_DOCKER_PATTERNS: frozenset[str] = frozenset({
    "xml_parse_error",
    "missing_acl",
    "missing_import",
    "manifest_load_order",
})

# Map of renamed field parameters (old -> new) for W8111
_RENAMED_PARAMS: dict[str, str | None] = {
    "track_visibility": "tracking",
    "oldname": None,  # removed entirely
    "digits_compute": "digits",
    "select": "index",
}

# Default values for missing manifest keys (C8107)
_MANIFEST_KEY_DEFAULTS: dict[str, str] = {
    "license": "LGPL-3",
    "author": "",
    "website": "",
    "category": "Uncategorized",
    "version": "17.0.1.0.0",
    "application": "False",
    "installable": "True",
}

# Docker diagnosis text -> pattern ID mapping keywords
_DOCKER_PATTERN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "xml_parse_error": ("xml", "syntax error", "parse", "xmlsyntaxerror", "mismatched tag"),
    "missing_acl": ("access control", "acl", "ir.model.access", "access rights", "no access rule"),
    "missing_import": ("no module named", "importerror", "modulenotfounderror", "could not be imported"),
    "manifest_load_order": ("action", "act_window", "does not exist", "external id not found"),
}


# -------------------------------------------------------------------------
# Pylint auto-fix
# -------------------------------------------------------------------------


def is_fixable_pylint(violation: Violation) -> bool:
    """Check whether a pylint violation can be mechanically auto-fixed."""
    return violation.rule_code in FIXABLE_PYLINT_CODES


def fix_pylint_violation(violation: Violation, module_path: Path) -> bool:
    """Apply a mechanical fix for a single pylint violation.

    Reads the source file, applies the fix based on the rule_code,
    and writes the corrected content back. Uses immutable patterns:
    read content -> create new content -> write back.

    Args:
        violation: The Violation to fix.
        module_path: Root path of the Odoo module.

    Returns:
        True if fix was applied, False if not applicable or failed.
    """
    if violation.rule_code not in FIXABLE_PYLINT_CODES:
        return False

    file_path = module_path / violation.file
    if not file_path.exists():
        return False

    handlers = {
        "W8113": _fix_w8113_redundant_string,
        "W8111": _fix_w8111_renamed_parameter,
        "C8116": _fix_c8116_superfluous_manifest_key,
        "W8150": _fix_w8150_absolute_import,
        "C8107": _fix_c8107_missing_manifest_key,
    }

    handler = handlers.get(violation.rule_code)
    if handler is None:
        return False

    return handler(violation, file_path)


def _fix_w8113_redundant_string(violation: Violation, file_path: Path) -> bool:
    """W8113: Remove redundant string= parameter from field definition."""
    content = file_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    line_idx = violation.line - 1

    if line_idx < 0 or line_idx >= len(lines):
        return False

    original_line = lines[line_idx]
    # Remove string="..." or string='...' with optional trailing comma and space
    new_line = re.sub(
        r"""\s*string\s*=\s*(?:"[^"]*"|'[^']*')\s*,?\s*""",
        "",
        original_line,
    )

    # If we removed the string= at the end but there's a trailing comma before ), clean up
    new_line = re.sub(r",\s*\)", ")", new_line)
    # If we removed string= but left (,  other_param), clean up leading comma after (
    new_line = re.sub(r"\(\s*,\s*", "(", new_line)

    if new_line == original_line:
        return False

    new_lines = list(lines)
    new_lines[line_idx] = new_line
    new_content = "\n".join(new_lines)
    file_path.write_text(new_content, encoding="utf-8")
    return True


def _fix_w8111_renamed_parameter(violation: Violation, file_path: Path) -> bool:
    """W8111: Rename deprecated field parameter to its replacement."""
    content = file_path.read_text(encoding="utf-8")

    # Extract old parameter name from the violation message
    # Message format: '"track_visibility" has been renamed to "tracking"'
    match = re.search(r'"(\w+)"\s+has been renamed', violation.message)
    if not match:
        return False

    old_param = match.group(1)
    new_param = _RENAMED_PARAMS.get(old_param)

    if new_param is None and old_param in _RENAMED_PARAMS:
        # Parameter removed entirely -- remove the param=value segment
        new_content = re.sub(
            rf"""\s*{re.escape(old_param)}\s*=\s*(?:"[^"]*"|'[^']*'|\w+)\s*,?\s*""",
            "",
            content,
        )
    elif new_param is not None:
        new_content = content.replace(old_param, new_param)
    else:
        return False

    if new_content == content:
        return False

    file_path.write_text(new_content, encoding="utf-8")
    return True


def _fix_c8116_superfluous_manifest_key(violation: Violation, file_path: Path) -> bool:
    """C8116: Remove a superfluous/deprecated key from __manifest__.py."""
    content = file_path.read_text(encoding="utf-8")

    # Extract key name from message: 'Deprecated key "description" in manifest file'
    match = re.search(r'"(\w+)"', violation.message)
    if not match:
        return False

    key_name = match.group(1)

    # Remove the key-value line from the manifest dict literal
    # Handles: "key": "value", or "key": value,
    new_content = re.sub(
        rf"""^\s*"{re.escape(key_name)}"\s*:.*,?\n""",
        "",
        content,
        flags=re.MULTILINE,
    )

    if new_content == content:
        return False

    file_path.write_text(new_content, encoding="utf-8")
    return True


def _fix_w8150_absolute_import(violation: Violation, file_path: Path) -> bool:
    """W8150: Convert absolute odoo.addons import to relative import."""
    content = file_path.read_text(encoding="utf-8")

    # Replace "from odoo.addons.module_name import X" with "from . import X"
    # and "from odoo.addons.module_name.sub import X" with "from .sub import X"
    new_content = re.sub(
        r"from\s+odoo\.addons\.\w+(\.\w+)*\s+import\s+",
        lambda m: "from . import " if not m.group(1) else f"from .{m.group(1)[1:]} import ",
        content,
    )

    if new_content == content:
        return False

    file_path.write_text(new_content, encoding="utf-8")
    return True


def _fix_c8107_missing_manifest_key(violation: Violation, file_path: Path) -> bool:
    """C8107: Add a missing required key to __manifest__.py."""
    content = file_path.read_text(encoding="utf-8")

    # Extract missing key name: 'Missing required key "license" in manifest file'
    match = re.search(r'"(\w+)"', violation.message)
    if not match:
        return False

    key_name = match.group(1)
    default_value = _MANIFEST_KEY_DEFAULTS.get(key_name, "")

    # Check if key already exists
    if re.search(rf'"{re.escape(key_name)}"\s*:', content):
        return False

    # Add the key after the opening brace of the dict
    # Find the first line with a key-value pair and insert before it
    if default_value in ("True", "False"):
        insert_line = f'    "{key_name}": {default_value},\n'
    else:
        insert_line = f'    "{key_name}": "{default_value}",\n'

    # Insert after the opening { line
    new_content = re.sub(
        r"(\{\s*\n)",
        rf"\1{insert_line}",
        content,
        count=1,
    )

    if new_content == content:
        return False

    file_path.write_text(new_content, encoding="utf-8")
    return True


def fix_pylint_violations(
    violations: tuple[Violation, ...],
    module_path: Path,
) -> tuple[int, tuple[Violation, ...]]:
    """Process a batch of violations, fixing what can be fixed.

    Args:
        violations: All violations to process.
        module_path: Root path of the Odoo module.

    Returns:
        Tuple of (fixed_count, remaining_violations) where remaining
        includes non-fixable violations and failed fixes.
    """
    fixed_count = 0
    remaining: list[Violation] = []

    for violation in violations:
        if is_fixable_pylint(violation):
            if fix_pylint_violation(violation, module_path):
                fixed_count += 1
            else:
                remaining.append(violation)
        else:
            remaining.append(violation)

    return fixed_count, tuple(remaining)


def run_pylint_fix_loop(
    module_path: Path,
    pylintrc_path: Path | None = None,
) -> tuple[int, tuple[Violation, ...]]:
    """Run pylint-odoo with up to MAX_FIX_CYCLES auto-fix cycles.

    Each cycle: run pylint -> fix fixable violations -> count.
    If a cycle produces 0 fixable violations, stop early.

    Args:
        module_path: Root path of the Odoo module.
        pylintrc_path: Optional path to .pylintrc-odoo config file.

    Returns:
        Tuple of (total_fixed, remaining_violations) after all cycles.
    """
    total_fixed = 0
    remaining: tuple[Violation, ...] = ()

    for _cycle in range(MAX_FIX_CYCLES):
        violations = run_pylint_odoo(module_path, pylintrc_path=pylintrc_path)

        if not violations:
            break

        # Check if any are fixable
        has_fixable = any(is_fixable_pylint(v) for v in violations)
        if not has_fixable:
            remaining = violations
            break

        cycle_fixed, remaining = fix_pylint_violations(violations, module_path)
        total_fixed += cycle_fixed

        if cycle_fixed == 0:
            break

    return total_fixed, remaining


# -------------------------------------------------------------------------
# Docker auto-fix identification
# -------------------------------------------------------------------------


def identify_docker_fix(diagnosis: str) -> str | None:
    """Identify whether a Docker error diagnosis matches a fixable pattern.

    Matches diagnosis text against known fixable Docker error patterns
    using keyword matching against the error_patterns.json taxonomy.

    Args:
        diagnosis: A diagnosis string from diagnose_errors().

    Returns:
        The pattern ID string if fixable, None if not.
    """
    diagnosis_lower = diagnosis.lower()

    for pattern_id, keywords in _DOCKER_PATTERN_KEYWORDS.items():
        if any(kw in diagnosis_lower for kw in keywords):
            return pattern_id

    return None


# -------------------------------------------------------------------------
# Escalation formatting
# -------------------------------------------------------------------------


def format_escalation(violations: tuple[Violation, ...]) -> str:
    """Format remaining violations as a grouped escalation report.

    Groups violations by file, includes file:line reference and
    one fix suggestion per violation per CONTEXT.md Decision E.

    Args:
        violations: Remaining violations after auto-fix exhausted.

    Returns:
        Formatted escalation string, or "No remaining issues." if empty.
    """
    if not violations:
        return "No remaining issues."

    grouped: dict[str, list[Violation]] = defaultdict(list)
    for v in violations:
        grouped[v.file].append(v)

    lines: list[str] = ["Auto-fix exhausted. Remaining violations:", ""]

    for file_path in sorted(grouped.keys()):
        file_violations = sorted(grouped[file_path], key=lambda v: v.line)
        for v in file_violations:
            lines.append(f"[{v.file}:{v.line}] {v.rule_code}: {v.message}")
            if v.suggestion:
                lines.append(f"  -> {v.suggestion}")

    return "\n".join(lines)
