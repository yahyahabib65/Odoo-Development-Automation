# Phase 23: Unified Result Type - Research

**Researched:** 2026-03-05
**Domain:** Python type system, validation pipeline error handling
**Confidence:** HIGH

## Summary

Phase 23 introduces a generic `Result[T]` type to unify the inconsistent return types across four validation modules: `auto_fix`, `docker_runner`, `pylint_runner`, and `verifier`. Currently these modules return a mix of bare tuples (`tuple[int, tuple[Violation, ...]]`), booleans, domain-specific dataclasses (`InstallResult`), and lists (`list[VerificationWarning]`). Error conditions are expressed variously as empty tuples, `False` booleans, exception messages stuffed into strings, or swallowed exceptions returning empty collections.

The unified `Result[T]` type provides three fields: `success: bool`, `data: T | None`, and `errors: list[str]`. This is a standard pattern in typed Python -- a lightweight discriminated union that avoids exceptions for expected failures and provides consistent error access. Since the project already uses frozen dataclasses extensively (see `validation/types.py`), the `Result` type should follow the same pattern but use `@dataclass(frozen=True)` with a generic type parameter via `typing.Generic[T]`.

**Primary recommendation:** Add a `Result[T]` frozen dataclass to `validation/types.py`, then refactor the four target modules' public API functions to return `Result[T]` instead of their current mixed types. Keep internal/private functions unchanged -- only the boundary functions consumed by `cli.py` and `renderer.py` need the new type.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VALD-02 | Validation pipeline uses unified Result[T] type with success/data/errors fields across auto_fix, docker_runner, pylint_runner, and verifier modules | Result[T] dataclass in types.py; refactor 4 modules' public functions; update cli.py consumer code |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dataclasses (stdlib) | 3.12 | Frozen immutable Result type | Already used throughout `validation/types.py`; no dependencies |
| typing.Generic (stdlib) | 3.12 | Type parameter for Result[T] | Standard Python approach for generic containers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing.overload (stdlib) | 3.12 | Optional: typed factory methods | Only if helper constructors are needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@dataclass(frozen=True)` Result | `NamedTuple` | NamedTuple has no Generic support; dataclass is already the project pattern |
| Custom Result class | `returns` library (dry-python/returns) | External dep adds complexity; overkill for this project's needs |
| Result type | Exception-based error handling | Inconsistent with requirement for structured errors; exceptions are what we're moving away from |

## Architecture Patterns

### Where Result[T] Lives

```
python/src/odoo_gen_utils/
├── validation/
│   ├── types.py          # ADD: Result[T] here (alongside existing Violation, InstallResult, etc.)
│   ├── docker_runner.py  # MODIFY: docker_install_module, docker_run_tests return Result
│   ├── pylint_runner.py  # MODIFY: run_pylint_odoo returns Result
│   ├── __init__.py       # MODIFY: re-export Result
│   └── ...
├── auto_fix.py           # MODIFY: run_pylint_fix_loop, run_docker_fix_loop return Result
├── verifier.py           # MODIFY: verify_model_spec, verify_view_spec return Result
└── cli.py                # MODIFY: update consumer code to use Result objects
```

### Pattern 1: Generic Frozen Dataclass

**What:** A `Result[T]` type using `Generic[T]` and `@dataclass(frozen=True)`
**When to use:** Every validation pipeline function that can succeed or fail

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    """Unified result type for validation pipeline operations.

    Attributes:
        success: Whether the operation completed successfully.
        data: The operation result (None on failure).
        errors: List of human-readable error messages (empty on success).
    """

    success: bool
    data: T | None = None
    errors: tuple[str, ...] = ()

    @staticmethod
    def ok(data: T) -> Result[T]:
        """Create a successful result."""
        return Result(success=True, data=data)

    @staticmethod
    def fail(*errors: str) -> Result[T]:
        """Create a failed result."""
        return Result(success=False, data=None, errors=tuple(errors))
```

**Confidence:** HIGH -- this pattern uses only stdlib and follows project conventions.

### Pattern 2: Return Type Mapping

Current return types map to Result[T] as follows:

| Module | Function | Current Return | New Return |
|--------|----------|----------------|------------|
| `pylint_runner` | `run_pylint_odoo()` | `tuple[Violation, ...]` | `Result[tuple[Violation, ...]]` |
| `docker_runner` | `docker_install_module()` | `InstallResult` | `Result[InstallResult]` |
| `docker_runner` | `docker_run_tests()` | `tuple[TestResult, ...]` | `Result[tuple[TestResult, ...]]` |
| `auto_fix` | `run_pylint_fix_loop()` | `tuple[int, tuple[Violation, ...]]` | `Result[tuple[int, tuple[Violation, ...]]]` |
| `auto_fix` | `run_docker_fix_loop()` | `tuple[bool, str]` | `Result[tuple[bool, str]]` |
| `verifier` | `verify_model_spec()` | `list[VerificationWarning]` | `Result[list[VerificationWarning]]` |
| `verifier` | `verify_view_spec()` | `list[VerificationWarning]` | `Result[list[VerificationWarning]]` |

**Key design decision:** Keep existing domain types (`InstallResult`, `Violation`, etc.) unchanged. `Result[T]` wraps them; it does not replace them. `InstallResult` already has its own `success` field, but wrapping it in `Result` adds consistent error message access and pipeline uniformity.

### Pattern 3: Error Message Formatting

**What:** All errors go through `Result.errors` as human-readable strings.
**When to use:** Every failure path in the four modules.

```python
# Before: swallowed exception, returned empty tuple
except subprocess.TimeoutExpired:
    logger.warning("pylint-odoo timed out after %d seconds", timeout)
    return ()

# After: structured error in Result
except subprocess.TimeoutExpired:
    logger.warning("pylint-odoo timed out after %d seconds", timeout)
    return Result.fail(f"pylint-odoo timed out after {timeout} seconds for {module_path}")
```

### Anti-Patterns to Avoid
- **Don't make errors mutable lists:** Use `tuple[str, ...]` for errors (matches project's immutability pattern with frozen dataclasses).
- **Don't remove existing types:** `InstallResult`, `TestResult`, `Violation`, `VerificationWarning` remain as-is. `Result` wraps, not replaces.
- **Don't change internal/private function signatures:** Only the public API functions (7 functions listed above) get `Result` returns. Private helpers like `_dispatch_docker_fix`, `_fix_w8113_redundant_string`, etc. keep their bool returns.
- **Don't break the CLI in one step:** Refactor cli.py consumers in the same plan where the functions change, to keep the codebase buildable at every commit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Generic container type | Custom metaclass magic | `@dataclass + Generic[T]` | Stdlib, well-understood, IDE support |
| Error aggregation | String concatenation | `tuple[str, ...]` field | Immutable, iterable, serializable |
| Factory methods | Complex __init__ overloads | `Result.ok()` / `Result.fail()` static methods | Clean API, impossible to create inconsistent state |

## Common Pitfalls

### Pitfall 1: Breaking Existing Callers
**What goes wrong:** Changing return types without updating all consumers causes runtime AttributeError/TypeError.
**Why it happens:** `cli.py` directly destructures tuples from `run_pylint_fix_loop` and `run_docker_fix_loop`.
**How to avoid:** Change producer and consumer in the same commit. Search all usages with grep before committing.
**Warning signs:** Tests fail with `AttributeError: 'Result' object is not iterable` or `cannot unpack non-sequence Result`.

### Pitfall 2: Forgetting to Update __init__.py Re-exports
**What goes wrong:** `Result` is importable from `odoo_gen_utils.validation.types` but not from `odoo_gen_utils.validation`.
**Why it happens:** `validation/__init__.py` explicitly lists all re-exports.
**How to avoid:** Add `Result` to both the import and `__all__` in `validation/__init__.py`.

### Pitfall 3: TypeVar Scoping with Static Methods
**What goes wrong:** `Result.ok(data)` doesn't properly infer `T` from the argument.
**Why it happens:** Static methods on generic classes don't automatically bind the class TypeVar in Python < 3.12. With `from __future__ import annotations`, deferred evaluation can cause issues.
**How to avoid:** The project targets Python 3.12 which handles this correctly. Test that type inference works with the actual Python version.

### Pitfall 4: Frozen Dataclass with Mutable Default
**What goes wrong:** Using `list` as default for `errors` would fail with frozen dataclass.
**Why it happens:** Mutable defaults on dataclasses require `field(default_factory=...)`, but frozen dataclasses can use immutable defaults like `()`.
**How to avoid:** Use `tuple[str, ...]` with default `()` instead of `list[str]`.

### Pitfall 5: Double-Wrapping InstallResult
**What goes wrong:** `InstallResult` already has `success` and `error_message`. `Result[InstallResult]` duplicates these.
**Why it happens:** The requirement says "unified type with success/data/errors fields."
**How to avoid:** Accept the minor duplication. `Result.success` reflects pipeline success; `InstallResult.success` reflects install success. They may differ (e.g., successful pipeline execution that detected a failed install is still `Result.ok(install_result)` where `install_result.success is False`). Alternatively, treat `docker_install_module` returning a failed install as `Result.ok()` (operation completed, data available) vs `Result.fail()` (operation couldn't run at all -- Docker not available, timeout).

**Recommended approach for InstallResult:** `Result.ok(install_result)` when Docker ran (even if install failed), `Result.fail("Docker not available")` when it couldn't run. This distinguishes "we got data" from "we couldn't even try."

## Code Examples

### Result Type Definition

```python
# validation/types.py -- add alongside existing types
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    """Unified result type for validation pipeline.

    success=True means the operation ran to completion and data is available.
    success=False means the operation failed and errors describe why.
    """

    success: bool
    data: T | None = None
    errors: tuple[str, ...] = ()

    @staticmethod
    def ok(data: T) -> Result[T]:
        return Result(success=True, data=data)

    @staticmethod
    def fail(*errors: str) -> Result[T]:
        return Result(success=False, data=None, errors=tuple(errors))
```

### Refactored pylint_runner.run_pylint_odoo

```python
def run_pylint_odoo(
    module_path: Path,
    *,
    pylintrc_path: Path | None = None,
    timeout: int = 120,
) -> Result[tuple[Violation, ...]]:
    # ... cmd construction same as before ...
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        violations = parse_pylint_output(result.stdout)
        return Result.ok(violations)
    except subprocess.TimeoutExpired:
        return Result.fail(f"pylint-odoo timed out after {timeout}s for {module_path}")
    except Exception as exc:
        return Result.fail(f"pylint-odoo failed for {module_path}: {exc}")
```

### Refactored docker_runner.docker_install_module

```python
def docker_install_module(
    module_path: Path,
    compose_file: Path | None = None,
    timeout: int = 300,
) -> Result[InstallResult]:
    if not check_docker_available():
        return Result.fail("Docker not available")

    # ... setup same as before ...
    try:
        # ... run compose commands ...
        install_result = InstallResult(success=success, log_output=combined_output, error_message=error_msg)
        return Result.ok(install_result)
    except subprocess.TimeoutExpired:
        return Result.fail(f"Timeout after {timeout}s waiting for module install")
    except Exception as exc:
        return Result.fail(str(exc))
    finally:
        _teardown(compose_file, env)
```

### CLI Consumer Update

```python
# Before:
violations = run_pylint_odoo(mod_path, pylintrc_path=pylintrc_path)

# After:
pylint_result = run_pylint_odoo(mod_path, pylintrc_path=pylintrc_path)
if not pylint_result.success:
    click.echo(f"Pylint error: {'; '.join(pylint_result.errors)}", err=True)
    violations = ()
else:
    violations = pylint_result.data or ()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bare tuples for multi-value returns | Structured Result types | Python 3.10+ typing maturity | Better IDE support, clearer APIs |
| Exceptions for expected failures | Result/Either monads | Rust influence ~2020+ | No hidden control flow |
| Mutable dataclasses | Frozen dataclasses | Python 3.7+ | Thread safety, immutability |

**Note:** Python 3.12 fully supports `TypeVar` in generic dataclasses without workarounds. The project's `requires-python = ">=3.12,<3.13"` constraint means all stdlib generic features are available.

## Open Questions

1. **Should Result.errors use tuple or list?**
   - What we know: Project convention is `tuple[str, ...]` for immutable sequences in frozen dataclasses (see `ValidationReport.diagnosis`, `ValidationReport.pylint_violations`).
   - Recommendation: Use `tuple[str, ...]` to match project convention. Already decided above.

2. **Should docker_install_module returning a failed install be Result.ok or Result.fail?**
   - What we know: "Docker not available" is clearly `Result.fail`. But what about "Docker ran, install failed"?
   - Recommendation: `Result.ok(InstallResult(success=False, ...))` -- the operation completed and returned data. `Result.fail()` means "couldn't run at all." This preserves the current InstallResult semantics.

3. **How much of auto_fix.py's internal functions should be refactored?**
   - What we know: The file is 1,539 lines with ~20 internal functions. Requirement says "auto_fix module uses Result type."
   - Recommendation: Only refactor the 2 public loop functions (`run_pylint_fix_loop`, `run_docker_fix_loop`). Internal fixers (`_fix_w8113`, etc.) stay as `bool` returns. The planner should be specific about this boundary.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `python/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd python && python -m pytest tests/test_validation_types.py -x -q` |
| Full suite command | `cd python && python -m pytest tests/ -x -q --ignore=tests/fixtures` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VALD-02a | Result[T] type has success, data, errors fields | unit | `cd python && python -m pytest tests/test_validation_types.py -x -q` | Needs update |
| VALD-02b | Result.ok() and Result.fail() factory methods | unit | `cd python && python -m pytest tests/test_validation_types.py -x -q` | Needs update |
| VALD-02c | Result is frozen/immutable | unit | `cd python && python -m pytest tests/test_validation_types.py -x -q` | Needs update |
| VALD-02d | run_pylint_odoo returns Result[tuple[Violation,...]] | unit | `cd python && python -m pytest tests/test_pylint_runner.py -x -q` | Exists, needs update |
| VALD-02e | docker_install_module returns Result[InstallResult] | unit | `cd python && python -m pytest tests/test_docker_runner.py -x -q` | Exists, needs update |
| VALD-02f | docker_run_tests returns Result[tuple[TestResult,...]] | unit | `cd python && python -m pytest tests/test_docker_runner.py -x -q` | Exists, needs update |
| VALD-02g | run_pylint_fix_loop returns Result | unit | `cd python && python -m pytest tests/test_auto_fix.py -x -q` | Exists, needs update |
| VALD-02h | run_docker_fix_loop returns Result | unit | `cd python && python -m pytest tests/test_auto_fix.py -x -q` | Exists, needs update |
| VALD-02i | verifier methods return Result | unit | `cd python && python -m pytest tests/test_verifier.py -x -q` | Exists, needs update |
| VALD-02j | CLI correctly consumes Result objects | integration | `cd python && python -m pytest tests/test_cli*.py -x -q` | Exists, needs update |
| VALD-02k | Error messages are consistently formatted | unit | `cd python && python -m pytest tests/test_validation_types.py -x -q` | Needs new tests |

### Sampling Rate
- **Per task commit:** `cd python && python -m pytest tests/test_validation_types.py tests/test_pylint_runner.py tests/test_docker_runner.py tests/test_auto_fix.py tests/test_verifier.py -x -q`
- **Per wave merge:** `cd python && python -m pytest tests/ -x -q --ignore=tests/fixtures`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_validation_types.py` -- add Result[T] tests (creation, ok, fail, immutability, generic type)
- No new test files needed; existing test files need updated assertions for Result return types

## Sources

### Primary (HIGH confidence)
- Project source code: `validation/types.py`, `auto_fix.py`, `docker_runner.py`, `pylint_runner.py`, `verifier.py`, `cli.py` -- direct inspection of current return types and consumer patterns
- Python 3.12 docs: `dataclasses`, `typing.Generic` -- verified stdlib support for generic frozen dataclasses

### Secondary (MEDIUM confidence)
- Python typing best practices for Result/Either patterns -- consistent across multiple style guides and projects

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only, no external deps needed
- Architecture: HIGH - direct code inspection reveals exact functions to change and their current types
- Pitfalls: HIGH - identified from actual code patterns (InstallResult double-wrapping, cli.py tuple destructuring)

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- stdlib only, no version sensitivity)
