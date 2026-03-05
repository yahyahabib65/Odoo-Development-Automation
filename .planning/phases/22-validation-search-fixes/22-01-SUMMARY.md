---
phase: 22-validation-search-fixes
plan: 01
subsystem: validation
tags: [docker, compose, run-rm, odoo, postgresql, race-condition]

requires:
  - phase: none
    provides: standalone fix
provides:
  - "Fixed docker_install_module using run --rm pattern (no more serialization failures)"
affects: [validation, docker-runner]

tech-stack:
  added: []
  patterns: ["run --rm for all ephemeral Odoo Docker commands"]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/validation/docker_runner.py
    - python/tests/test_docker_runner.py

key-decisions:
  - "Matched docker_run_tests pattern exactly: up -d --wait db then run --rm -T odoo"

patterns-established:
  - "All Docker validation commands use run --rm (never exec) to avoid dual-process race conditions"

requirements-completed: [VALD-01]

duration: 1min
completed: 2026-03-05
---

# Phase 22 Plan 01: Fix docker_install_module Summary

**Replaced docker exec with run --rm in docker_install_module, eliminating PostgreSQL serialization race condition from dual Odoo processes**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-05T08:11:56Z
- **Completed:** 2026-03-05T08:12:49Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Changed docker_install_module to start only db service (not full Odoo stack)
- Replaced `exec` with `run --rm` for module installation (fresh container, no entrypoint conflict)
- Added TestDockerInstallUsesRunNotExec with two explicit assertion tests
- All 14 docker_runner tests pass green

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix docker_install_module to use run --rm pattern** - `7e885f3` (fix)

**Plan metadata:** `ae5ac4c` (docs: complete plan)

_Note: TDD task with single commit (test + fix combined after RED/GREEN cycle)_

## Files Created/Modified
- `python/src/odoo_gen_utils/validation/docker_runner.py` - Changed docker_install_module: up -d --wait db + run --rm instead of up -d --wait + exec
- `python/tests/test_docker_runner.py` - Added TestDockerInstallUsesRunNotExec class with db-only and run-rm assertions

## Decisions Made
- Matched docker_run_tests pattern exactly (same approach already proven for test execution)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Docker validation now uses consistent run --rm pattern for both install and test
- Ready for Phase 23 (Unified Result Type) or remaining Phase 22 plans

## Self-Check: PASSED

- FOUND: python/src/odoo_gen_utils/validation/docker_runner.py
- FOUND: python/tests/test_docker_runner.py
- FOUND: .planning/phases/22-validation-search-fixes/22-01-SUMMARY.md
- FOUND: commit 7e885f3

---
*Phase: 22-validation-search-fixes*
*Completed: 2026-03-05*
