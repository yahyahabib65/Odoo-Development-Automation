---
phase: 24-code-quality-decomposition
plan: 01
subsystem: cli
tags: [lazy-imports, importlib-resources, docker-compose, cli-startup]

# Dependency graph
requires:
  - phase: 23-unified-result-type
    provides: Result[T] pattern used by validation functions
provides:
  - CLI with lazy imports (fast startup, no heavy deps at module level)
  - Docker compose resolution via importlib.resources with env var override
affects: [24-02, 24-03]

# Tech tracking
tech-stack:
  added: [importlib.resources]
  patterns: [lazy-import-inside-command, env-var-override-for-paths]

key-files:
  created:
    - python/tests/test_cli_lazy_imports.py
    - python/tests/test_docker_compose_path.py
    - python/src/odoo_gen_utils/data/docker-compose.yml
  modified:
    - python/src/odoo_gen_utils/cli.py
    - python/src/odoo_gen_utils/validation/docker_runner.py
    - python/pyproject.toml
    - python/tests/test_cli_validate.py
    - python/tests/test_cli_build_index.py

key-decisions:
  - "Lazy imports placed inside each command function, not using __getattr__ module-level lazy loading"
  - "Docker compose path uses importlib.resources.files() with ODOO_GEN_COMPOSE_FILE env var override"

patterns-established:
  - "Lazy import pattern: heavy deps imported inside @main.command() functions, only click/json/sys/pathlib at module level"
  - "Package data pattern: non-Python files stored in odoo_gen_utils/data/ and resolved via importlib.resources"

requirements-completed: [QUAL-01, QUAL-03]

# Metrics
duration: 5min
completed: 2026-03-05
---

# Phase 24 Plan 01: CLI Lazy Imports & Docker Compose Path Summary

**CLI startup made fast by moving 13 heavy imports into command functions; Docker compose path resolved via importlib.resources with ODOO_GEN_COMPOSE_FILE env var override**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T12:48:28Z
- **Completed:** 2026-03-05T12:53:48Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- CLI module-level imports reduced to only click, json, sys, pathlib, and __version__ -- heavy libraries (chromadb, PyGithub, gitpython, docker, validation, renderer, etc.) load only when their respective commands are invoked
- Docker compose path resolution replaced 5-level parent traversal with importlib.resources.files() lookup, adding ODOO_GEN_COMPOSE_FILE env var for explicit override
- docker-compose.yml copied into package data directory for proper wheel distribution

## Task Commits

Each task was committed atomically:

1. **Task 1: CLI lazy imports** - `3d0d584` (feat)
2. **Task 2: Docker compose path via importlib.resources** - `db8274b` (feat)

_Both tasks followed TDD: tests written first (RED), implementation added (GREEN)._

## Files Created/Modified
- `python/src/odoo_gen_utils/cli.py` - All heavy imports moved inside command functions
- `python/src/odoo_gen_utils/validation/docker_runner.py` - get_compose_file() uses importlib.resources + env var
- `python/src/odoo_gen_utils/data/docker-compose.yml` - Package data copy of compose file
- `python/pyproject.toml` - Added force-include for data directory
- `python/tests/test_cli_lazy_imports.py` - 4 tests: AST analysis + subprocess verification
- `python/tests/test_docker_compose_path.py` - 7 tests: default path, env override, no parent traversal
- `python/tests/test_cli_validate.py` - Updated mock targets from cli namespace to source modules
- `python/tests/test_cli_build_index.py` - Updated mock targets from cli namespace to source modules

## Decisions Made
- Lazy imports placed directly inside each command function body rather than using `__getattr__` module-level lazy loading -- simpler, more explicit, and compatible with Click's command registration
- Docker compose path uses `importlib.resources.files("odoo_gen_utils").joinpath("data", "docker-compose.yml")` with `Path(str(ref))` to convert Traversable to Path

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test mock targets after lazy import refactor**
- **Found during:** Task 1 (CLI lazy imports)
- **Issue:** Existing tests in test_cli_validate.py and test_cli_build_index.py patched at `odoo_gen_utils.cli.run_pylint_odoo` etc., but those names no longer exist at module level after lazy imports
- **Fix:** Changed mock targets to patch at the source module (e.g., `odoo_gen_utils.validation.run_pylint_odoo`, `odoo_gen_utils.search.get_github_token`)
- **Files modified:** python/tests/test_cli_validate.py, python/tests/test_cli_build_index.py
- **Verification:** All 18 CLI tests pass
- **Committed in:** 3d0d584 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Necessary correction for test compatibility with lazy imports. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI lazy imports complete, ready for Plan 02 (renderer decomposition) and Plan 03 (remaining code quality tasks)
- All 34 verification tests pass

---
*Phase: 24-code-quality-decomposition*
*Completed: 2026-03-05*
