---
phase: 66
slug: wire-rubric-scores-to-confidence-chart
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 66 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (Python) + vitest (TypeScript) |
| **Config file** | `packages/orchestration/pyproject.toml`, `packages/dashboard/vitest.config.ts` |
| **Quick run command** | `uv run pytest packages/orchestration/tests/test_approval.py packages/orchestration/tests/test_cli_propose.py packages/orchestration/tests/test_cli_approve.py -x` |
| **Full suite command** | `uv run pytest packages/orchestration/tests/ -v && cd packages/dashboard && pnpm vitest run tests/topology/confidence.test.ts` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/orchestration/tests/test_approval.py packages/orchestration/tests/test_cli_propose.py packages/orchestration/tests/test_cli_approve.py -x`
- **After every plan wave:** Run `uv run pytest packages/orchestration/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 66-01-01 | 01 | 1 | TOBS-05 | unit | `uv run pytest packages/orchestration/tests/test_approval.py -x` | ✅ | ⬜ pending |
| 66-01-02 | 01 | 1 | TOBS-05 | unit | `uv run pytest packages/orchestration/tests/test_cli_propose.py -x` | ✅ | ⬜ pending |
| 66-01-03 | 01 | 1 | TOBS-05 | unit | `uv run pytest packages/orchestration/tests/test_cli_approve.py -x` | ✅ | ⬜ pending |
| 66-01-04 | 01 | 1 | TOBS-05 | unit | `cd packages/dashboard && pnpm vitest run tests/topology/confidence.test.ts` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
