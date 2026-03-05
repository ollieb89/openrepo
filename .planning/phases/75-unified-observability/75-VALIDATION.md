---
phase: 75
slug: unified-observability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 75 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python) + vitest (TypeScript/React) |
| **Config file** | `packages/orchestration/pyproject.toml` / `packages/dashboard/vitest.config.ts` |
| **Quick run command** | `uv run pytest packages/orchestration/tests/ -x -q` |
| **Full suite command** | `uv run pytest packages/orchestration/tests/ -v && cd packages/dashboard && pnpm test --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/orchestration/tests/ -x -q`
- **After every plan wave:** Run `uv run pytest packages/orchestration/tests/ -v && cd packages/dashboard && pnpm test --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 75-01-01 | 01 | 0 | OBSV-01 | unit | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py -v` | ❌ W0 | ⬜ pending |
| 75-01-02 | 01 | 0 | OBSV-01 | unit | `cd packages/dashboard && pnpm test --run src/lib/hooks/useMetrics.test.ts` | ❌ W0 | ⬜ pending |
| 75-01-03 | 01 | 0 | OBSV-02 | unit | `cd packages/dashboard && pnpm test --run src/components/metrics/PipelineStrip.test.tsx` | ❌ W0 | ⬜ pending |
| 75-01-04 | 01 | 1 | OBSV-01 | integration | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py -v` | ❌ W0 | ⬜ pending |
| 75-01-05 | 01 | 1 | OBSV-01 | integration | `cd packages/dashboard && pnpm test --run src/app/api/metrics/unified.test.ts` | ❌ W0 | ⬜ pending |
| 75-01-06 | 01 | 2 | OBSV-02 | unit | `cd packages/dashboard && pnpm test --run src/components/metrics/PipelineStrip.test.tsx` | ❌ W0 | ⬜ pending |
| 75-01-07 | 01 | 2 | OBSV-02 | unit | `cd packages/dashboard && pnpm test --run src/components/mission-control/TaskPulse.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/orchestration/tests/test_python_metrics_snapshot.py` — stubs for OBSV-01 (snapshot writer, lock safety, JSON schema)
- [ ] `packages/dashboard/src/app/api/metrics/unified.test.ts` — stubs for OBSV-01 (unified endpoint response shape, merging logic)
- [ ] `packages/dashboard/src/components/metrics/PipelineStrip.test.tsx` — stubs for OBSV-02 (equal-width segments, status fills, no proportional layout)
- [ ] `packages/dashboard/src/components/mission-control/TaskPulse.test.tsx` — stubs for OBSV-02 (inline expansion, keyboard accessibility)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Timeline segment timestamps accurate to within 1 second | OBSV-02 | Requires live orchestration run with known event times | Start an orchestration run, capture L1/L2/L3 timestamps from logs, compare with timeline display |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
