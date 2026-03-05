---
phase: 26
slug: monetary-field-detection
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-05
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | python/pyproject.toml |
| **Quick run command** | `cd python && uv run pytest tests/test_renderer.py tests/test_render_stages.py -x -q -k 'monetary or currency'` |
| **Full suite command** | `cd python && uv run pytest -x -q` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | SPEC-01 | unit | `cd python && uv run pytest tests/test_renderer.py -x -q -k 'monetary'` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. test_renderer.py already exists — only needs new monetary detection test cases.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker install test | SPEC-01 | Requires running Docker daemon | `cd python && uv run pytest tests/test_golden_path.py -x -v` with Docker running |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-05
