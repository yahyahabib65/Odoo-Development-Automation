# Phase 20: Auto-Fix AST Migration - Research

**Researched:** 2026-03-05
**Domain:** Python AST-based source code transformation
**Confidence:** HIGH

## Summary

Phase 20 replaces regex-based source modification in 5 pylint fixers and 1 unused-import detector with AST-based approaches. The current implementation in `auto_fix.py` (1167 lines) uses `re.sub()` patterns that fail on multi-line expressions (e.g., `string="Name"` spanning parenthesized field definitions). The unused import detector (`fix_unused_imports`) only checks 4 hardcoded names (`api`, `ValidationError`, `AccessError`, `_`) and conservatively assumes all other imports are used.

Python's stdlib `ast` module provides everything needed. Verified on the project's Python 3.12 runtime: `ast.parse()` gives precise `lineno`/`col_offset`/`end_lineno`/`end_col_offset` for every node including keywords, and `ast.NodeVisitor` can walk the full tree to find all `ast.Name` references. The key architectural decision is to use a **hybrid approach**: AST for node location and analysis, targeted string surgery for modification. This preserves formatting, comments, and whitespace that `ast.unparse()` destroys.

**Primary recommendation:** Use stdlib `ast` module with hybrid locate-then-splice strategy. Do NOT add LibCST or other third-party CST libraries -- the 5 fixers are simple enough that AST-located string surgery handles them cleanly.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AFIX-01 | All 5 pylint fixers use AST to parse and modify source instead of regex, handling multi-line expressions correctly | Hybrid AST-locate + string-splice approach verified on Python 3.12; AST gives precise line:col ranges for all keyword nodes, even in multi-line calls |
| AFIX-02 | Unused import detection scans full AST body for name references instead of 4-name whitelist | `ast.walk()` + `ast.Name` collection verified to find ALL name references in file body; directly replaces `_IMPORT_USAGE_PATTERNS` dict |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ast (stdlib) | Python 3.12 | Parse source, locate nodes, walk tree | Already imported in auto_fix.py; provides precise line/col positions for all nodes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | Python 3.12 | Message parsing from violations | Still needed to extract param names from violation messages |
| textwrap (stdlib) | Python 3.12 | Test fixture code | Already used in tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib ast + string splice | LibCST | Format-preserving CST, but adds ~5MB dependency for 5 simple fixers; overkill |
| stdlib ast + string splice | RedBaron | Another CST lib, less maintained than LibCST; same overkill concern |
| stdlib ast + string splice | ast.unparse() | Destroys comments, collapses multi-line to single-line; unacceptable for formatting |

**Installation:**
```bash
# No new dependencies -- stdlib ast is sufficient
```

## Architecture Patterns

### Recommended Approach: Hybrid AST-Locate + String-Splice

**What:** Parse source with `ast.parse()` to get a tree with precise positions, use `ast.walk()` or `ast.NodeVisitor` to find target nodes, then use the node's `lineno`/`col_offset`/`end_lineno`/`end_col_offset` to do targeted string replacement on the original source text.

**Why not pure AST transform + unparse:**
```python
# VERIFIED: ast.unparse() destroys formatting
code = 'name = fields.Char(\n    string="Name",\n    required=True,\n)'
tree = ast.parse(code)
ast.unparse(tree)
# Result: "name = fields.Char(string='Name', required=True)"
# Lost: multi-line formatting, double quotes -> single quotes, trailing comma
```

**Why not pure regex (current approach):**
```python
# CURRENT BUG: regex can't handle multi-line string= removal
# This regex operates on a single line and misses:
#   name = fields.Char(
#       string="Name",    <-- regex finds this line
#       required=True,    <-- but can't fix trailing comma on previous line
#   )
```

### Pattern: AST-Located String Splice

```python
# Source: Verified on Python 3.12 in project venv
import ast

def _remove_keyword_by_name(source: str, call_node: ast.Call, keyword_name: str) -> str:
    """Remove a keyword argument from a Call node using precise AST positions."""
    target_kw = None
    target_idx = -1
    for idx, kw in enumerate(call_node.keywords):
        if kw.arg == keyword_name:
            target_kw = kw
            target_idx = idx
            break
    if target_kw is None:
        return source

    lines = source.split("\n")
    # Determine splice range: from keyword start to next keyword start (or closing paren)
    # ... precise line/col surgery using target_kw.lineno, target_kw.col_offset,
    #     target_kw.end_lineno, target_kw.end_col_offset
    # Handle trailing comma, leading comma, blank line cleanup
    ...
```

### Pattern: Full-Body Import Usage Scanning

```python
# Source: Verified on Python 3.12
import ast

def _find_all_name_references(tree: ast.Module, exclude_imports: bool = True) -> set[str]:
    """Collect every ast.Name.id in the module body, excluding import statements."""
    import_lines: set[int] = set()
    if exclude_imports:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_lines.add(node.lineno)

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.lineno not in import_lines:
            names.add(node.id)
    return names
```

### Anti-Patterns to Avoid
- **Using ast.unparse() for output:** Destroys comments, whitespace, quote style, trailing commas. Only use for generating NEW code (e.g., inserting a new manifest key).
- **Operating on single lines for multi-line expressions:** The whole point of this migration. AST nodes span multiple lines; use `end_lineno`/`end_col_offset`.
- **Replacing the entire file with AST output:** Always do minimal string surgery on the original source to preserve formatting.
- **Modifying lines in-place while iterating forward:** Line number shifts break subsequent fixes. Process in reverse line order, or recalculate positions after each edit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python parsing | Custom tokenizer/parser | `ast.parse()` | Handles all Python syntax correctly |
| Node position tracking | Manual line counting | `node.lineno`, `node.end_lineno`, `node.col_offset`, `node.end_col_offset` | AST provides these for free since Python 3.8 |
| Name reference finding | String search / regex | `ast.walk()` + `ast.Name` | Distinguishes variable references from string contents, comments |
| Import statement parsing | Regex on import lines | `ast.ImportFrom` / `ast.Import` nodes | Handles `as` aliases, multi-line imports, relative imports |

**Key insight:** The stdlib `ast` module already does the hard work of parsing. The only "custom" part is the string-splice logic to modify source without losing formatting.

## Common Pitfalls

### Pitfall 1: ast.unparse() Format Destruction
**What goes wrong:** Using `ast.unparse()` to regenerate source loses comments, collapses multi-line expressions, changes quote styles, removes trailing commas.
**Why it happens:** `ast.unparse()` generates minimal valid Python, not formatted Python.
**How to avoid:** Never use `ast.unparse()` for modifying existing code. Use it only for generating new standalone expressions (e.g., a new dict key-value pair).
**Warning signs:** Tests passing but generated code looks different from template style.

### Pitfall 2: Line Number Shift After Edits
**What goes wrong:** After removing an import line (e.g., line 2), all subsequent line references in the AST are off by 1.
**Why it happens:** The AST was built from the original source; edits change line counts.
**How to avoid:** Process nodes in reverse line order (highest line number first), or re-parse after each edit. The current code already sorts `import_nodes` by `lineno` descending -- preserve this pattern.
**Warning signs:** Wrong line being modified; tests showing content from adjacent lines being corrupted.

### Pitfall 3: Comma Cleanup After Keyword Removal
**What goes wrong:** Removing `string="Name",` from `fields.Char(string="Name", required=True)` leaves `fields.Char(, required=True)` or `fields.Char( required=True)`.
**Why it happens:** The keyword's AST position includes only the keyword itself, not surrounding commas/whitespace.
**How to avoid:** After removing a keyword's text span, clean up: (a) trailing comma+whitespace if it was the last keyword, (b) leading comma+whitespace if it was the first, (c) the entire line if it becomes blank.
**Warning signs:** Syntax errors in output code; extra commas or spaces.

### Pitfall 4: Multi-Line Keyword Removal Leaving Blank Lines
**What goes wrong:** Removing a keyword that spans its own line (common in multi-line field definitions) leaves a blank line.
**Why it happens:** String splice removes content but not the newline.
**How to avoid:** After splice, check if the resulting line is blank/whitespace-only and remove it. Also consolidate consecutive blank lines.
**Warning signs:** Double blank lines in output; pylint warnings about blank lines.

### Pitfall 5: Manifest Key Values Spanning Multiple Lines
**What goes wrong:** C8116 (remove superfluous key) regex only removes single-line entries. If a manifest value spans multiple lines (e.g., a multiline string or list), partial removal corrupts the dict.
**Why it happens:** `re.sub(r'^\s*"key"\s*:.*,?\n', "", ...)` only matches one line.
**How to avoid:** Use AST to find the Dict node, get the key-value pair's full span from `key.lineno` to `value.end_lineno`, and remove that entire range.
**Warning signs:** SyntaxError when the manifest is re-parsed; missing closing braces or brackets.

## Code Examples

### Example 1: AST-Based Keyword Removal (W8113 replacement)

```python
# Replaces the current regex-based _fix_w8113_redundant_string
def _fix_w8113_redundant_string(violation: Violation, file_path: Path) -> bool:
    """Remove redundant string= parameter using AST-located splice."""
    content = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False

    target_line = violation.line
    lines = content.split("\n")

    # Find the Call node on the target line
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (node.lineno <= target_line <= (node.end_lineno or node.lineno)):
            continue

        # Find string= keyword
        for kw_idx, kw in enumerate(node.keywords):
            if kw.arg != "string":
                continue

            # Use AST positions to splice out the keyword + surrounding comma
            new_content = _splice_remove_keyword(content, node, kw_idx)
            if new_content != content:
                file_path.write_text(new_content, encoding="utf-8")
                return True

    return False
```

### Example 2: Full-Body Unused Import Detection (AFIX-02 replacement)

```python
# Replaces the current _IMPORT_USAGE_PATTERNS whitelist approach
def fix_unused_imports(file_path: Path) -> bool:
    """Detect and remove ALL unused imports using full AST body scan."""
    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        return False

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False

    # Collect ALL name references in the file body (excluding import lines)
    import_linenos: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_linenos.add(node.lineno)

    used_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.lineno not in import_linenos:
            used_names.add(node.id)

    # Check each imported name against used_names
    # ... remove unused imports via line-based splice
```

### Example 3: Manifest Key Removal with Full Span (C8116 replacement)

```python
# AST-based manifest key removal handles multi-line values
def _fix_c8116_superfluous_manifest_key(violation: Violation, file_path: Path) -> bool:
    content = file_path.read_text(encoding="utf-8")
    match = re.search(r'"(\w+)"', violation.message)
    if not match:
        return False
    key_name = match.group(1)

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key_node, val_node in zip(node.keys, node.values):
            if isinstance(key_node, ast.Constant) and key_node.value == key_name:
                # Remove from key_node.lineno to val_node.end_lineno (inclusive)
                # This handles multi-line values correctly
                lines = content.split("\n")
                start_line = key_node.lineno - 1
                end_line = val_node.end_lineno - 1
                # Remove the entire line range, including trailing comma
                new_lines = lines[:start_line] + lines[end_line + 1:]
                new_content = "\n".join(new_lines)
                if new_content != content:
                    file_path.write_text(new_content, encoding="utf-8")
                    return True
    return False
```

## Fixer-by-Fixer Migration Analysis

### _fix_w8113: Redundant string= parameter
**Current:** Regex `r'\s*string\s*=\s*(?:"[^"]*"|\'[^\']*\')\s*,?\s*'` on single line
**Bug:** Fails when `string="Name"` is on its own line in a multi-line field definition
**AST approach:** Find `ast.Call` node at violation line, locate `keyword` with `arg=="string"`, splice out using `lineno:col_offset` to `end_lineno:end_col_offset`
**AST nodes:** `ast.Call` > `ast.keyword` (arg="string")
**Complexity:** Medium -- comma cleanup logic needed

### _fix_w8111: Renamed field parameter
**Current:** Regex extracts old param name from violation message, then `content.replace(old_param, new_param)` globally
**Bug:** Global replace can rename unrelated occurrences of the parameter name in comments/strings
**AST approach:** Find `ast.Call` node, locate `keyword` with `arg==old_param`, change only `kw.arg` text at precise position
**AST nodes:** `ast.Call` > `ast.keyword` (arg=old_param)
**Complexity:** Low -- simple text replacement at precise location; or removal if param is dropped entirely

### _fix_c8116: Superfluous manifest key
**Current:** Regex `r'^\s*"key"\s*:.*,?\n'` removes single-line key-value pair
**Bug:** Fails on multi-line values (e.g., `"description": "A very\nlong\nstring"`)
**AST approach:** Parse manifest as dict literal, find key-value pair by key name, remove lines from `key.lineno` to `value.end_lineno`
**AST nodes:** `ast.Dict` > key `ast.Constant` + corresponding value node
**Complexity:** Low -- manifest is a simple dict literal

### _fix_w8150: Absolute import to relative
**Current:** Regex `r'from\s+odoo\.addons\.\w+(\.\w+)*\s+import\s+'` with lambda replacement
**Bug:** No known multi-line bug, but regex approach can match inside strings/comments
**AST approach:** Find `ast.ImportFrom` nodes where `module` starts with `"odoo.addons."`, rewrite module path to relative form using `end_lineno`/`end_col_offset`
**AST nodes:** `ast.ImportFrom` (module="odoo.addons.xxx")
**Complexity:** Low -- import statements are single-line in practice

### _fix_c8107: Missing manifest key
**Current:** Regex inserts after `{\s*\n` pattern. Uses `re.sub` with count=1
**Bug:** Minor -- if manifest has unusual formatting, regex may not match
**AST approach:** Parse manifest dict, find insertion point after opening brace, insert new key-value line
**AST nodes:** `ast.Dict` -- use `node.lineno` of first key to determine insertion point
**Complexity:** Low -- can still use string insertion, but guided by AST position

### fix_unused_imports: Full-body scan (AFIX-02)
**Current:** Hardcoded `_IMPORT_USAGE_PATTERNS` dict with 4 names; unknown names assumed used
**Bug:** Only detects unused `api`, `ValidationError`, `AccessError`, `_`. Any other unused import passes silently.
**AST approach:** `ast.walk()` to collect ALL `ast.Name` references in file body (excluding import lines), compare against imported names. Any import not referenced is unused.
**AST nodes:** `ast.ImportFrom` for imports, `ast.Name` for references
**Complexity:** Medium -- need to handle `ast.Attribute` chains (e.g., `api.constrains` uses `api` as a Name), handle star imports, handle `__all__` exports

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| regex string= removal (single-line) | AST-located splice (multi-line safe) | This phase | Fixes AFIX-01 multi-line corruption bug |
| 4-name hardcoded whitelist | Full AST body name scan | This phase | Fixes AFIX-02 false-negative missed imports |
| ast.unparse() for output | String splice preserving formatting | N/A (never used unparse) | Maintains code style consistency |

**Note on Python version:** Project requires Python >=3.12, <3.13 (`pyproject.toml`). The `ast` module in 3.12 has full `end_lineno`/`end_col_offset` support (available since 3.8). `ast.unparse()` available since 3.9. No version concerns.

## Open Questions

1. **Edge case: `from X import *` (star imports)**
   - What we know: Star imports import all names; AST cannot determine which names are used
   - What's unclear: Does the generated Odoo code ever use star imports?
   - Recommendation: If `ast.ImportFrom` has `names=[ast.alias(name='*')]`, skip that import (never remove star imports). Conservative and safe.

2. **Edge case: `__all__` exports**
   - What we know: If a module defines `__all__`, names listed there are "used" even without local references
   - What's unclear: Whether generated Odoo modules use `__all__`
   - Recommendation: If `__all__` is defined in the module, treat all names in it as used. Simple AST check.

3. **Keyword splice: trailing comma vs. no comma**
   - What we know: Python allows trailing commas in function calls. Odoo templates sometimes include them, sometimes not.
   - Recommendation: After removing a keyword, clean up commas to produce valid Python. If the removed keyword was last and had no trailing comma, remove the preceding comma.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ (via venv) |
| Config file | `python/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd python && .venv/bin/python -m pytest tests/test_auto_fix.py -x -q` |
| Full suite command | `cd python && .venv/bin/python -m pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AFIX-01 | 5 fixers use AST; multi-line expressions handled | unit | `.venv/bin/python -m pytest tests/test_auto_fix.py -x -q -k "W8113 or W8111 or C8116 or W8150 or C8107"` | Existing tests need AST-specific additions |
| AFIX-01 | Multi-line string= correctly fixed | unit | `.venv/bin/python -m pytest tests/test_auto_fix.py -x -q -k "multi_line"` | No -- Wave 0 gap |
| AFIX-02 | Full AST body scan for all imports | unit | `.venv/bin/python -m pytest tests/test_auto_fix.py -x -q -k "unused_import"` | Existing tests cover 4 hardcoded names; need tests for arbitrary names |
| AFIX-02 | Zero false positives on used imports | unit | `.venv/bin/python -m pytest tests/test_auto_fix.py -x -q -k "keeps_used"` | Partially exists |

### Sampling Rate
- **Per task commit:** `cd python && .venv/bin/python -m pytest tests/test_auto_fix.py -x -q`
- **Per wave merge:** `cd python && .venv/bin/python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_auto_fix.py::TestFixW8113MultiLine` -- test multi-line string= removal (e.g., `string="Name"` on its own line in parenthesized call)
- [ ] `tests/test_auto_fix.py::TestFixW8111MultiLine` -- test multi-line renamed param
- [ ] `tests/test_auto_fix.py::TestFixC8116MultiLineValue` -- test manifest key with multi-line value
- [ ] `tests/test_auto_fix.py::TestUnusedImportsArbitraryNames` -- test that unknown imports (not in hardcoded list) are detected as unused when not referenced
- [ ] `tests/test_auto_fix.py::TestUnusedImportsStarImport` -- test that star imports are preserved
- [ ] `tests/test_auto_fix.py::TestUnusedImportsFormattingPreserved` -- test that comments and whitespace are preserved after import removal

### Existing Test Coverage
- **61 tests** in `tests/test_auto_fix.py` covering all 5 fixers + unused imports + Docker fix loop
- **7 tests** in `tests/test_auto_fix_integration.py` covering CLI auto-fix flow
- Tests use `tempfile.TemporaryDirectory` and `tmp_path` fixtures for isolation
- Tests use `unittest.mock.patch` on `run_pylint_odoo` for fix loop tests

## Sources

### Primary (HIGH confidence)
- Python 3.12 `ast` module -- verified interactively on project venv: `ast.parse()`, `ast.walk()`, `ast.Name`, `ast.keyword` positions (lineno, col_offset, end_lineno, end_col_offset all present)
- Project source: `python/src/odoo_gen_utils/auto_fix.py` (1167 lines, 5 fixers + unused import detector + Docker fix loop)
- Project tests: `python/tests/test_auto_fix.py` (61 tests), `python/tests/test_auto_fix_integration.py` (7 tests)

### Secondary (MEDIUM confidence)
- [LibCST docs](https://libcst.readthedocs.io/en/latest/why_libcst.html) -- format-preserving CST alternative; evaluated and rejected as overkill for this use case
- [Python ast docs](https://docs.python.org/3/library/ast.html) -- official reference for node types and position attributes

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- stdlib `ast` already imported and used in the file; no new deps needed
- Architecture: HIGH -- hybrid approach verified with real code samples on project's Python 3.12
- Pitfalls: HIGH -- all pitfalls discovered by actual experimentation (ast.unparse format loss, comma cleanup, line shift)

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- stdlib ast module does not change between minor versions)
