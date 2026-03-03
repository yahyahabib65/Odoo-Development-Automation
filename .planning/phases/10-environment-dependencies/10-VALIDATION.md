---
phase: 10
slug: environment-dependencies
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 |
| **Config file** | `python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd python && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd python && uv run pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds (unit), ~60s (e2e subset), ~300s (e2e full) |

---

## Sampling Rate

- **After every task commit:** Run `cd python && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd python && uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | DEBT-01 | integration/e2e | `cd python && uv run pytest tests/ -x -q -m e2e` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DEBT-02 | integration/e2e | `cd python && uv run pytest tests/ -x -q -m e2e` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_e2e_github.py` — e2e tests for DEBT-01 (real GitHub API, skipped without token)
- [ ] `tests/test_e2e_index.py` — e2e tests for DEBT-02 (real ChromaDB build + query, skipped without token)
- [ ] Add `e2e` and `e2e_slow` markers to `[tool.pytest.ini_options]`

*Existing unit test infrastructure covers mocked scenarios. Wave 0 adds real-dependency tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `gh auth status` succeeds | DEBT-01 | Requires real gh CLI auth on developer machine | Run `gh auth status` and verify output shows authenticated |
| Fresh venv install completes | DEBT-02 | Requires clean venv creation (not in test harness) | Run `uv venv /tmp/test && uv pip install -e ".[search]"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
