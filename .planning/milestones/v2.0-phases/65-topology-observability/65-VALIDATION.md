---
phase: 65
slug: topology-observability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 65 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 3.2.4 |
| **Config file** | `packages/dashboard/vitest.config.ts` |
| **Quick run command** | `cd packages/dashboard && pnpm test` |
| **Full suite command** | `cd packages/dashboard && pnpm test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd packages/dashboard && pnpm test`
- **After every plan wave:** Run `cd packages/dashboard && pnpm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 65-01-01 | 01 | 0 | TOBS-01 | unit | `cd packages/dashboard && pnpm test -- tests/topology/api.test.ts` | ❌ W0 | ⬜ pending |
| 65-01-02 | 01 | 0 | TOBS-02 | unit | `cd packages/dashboard && pnpm test -- tests/topology/transform.test.ts` | ❌ W0 | ⬜ pending |
| 65-01-03 | 01 | 0 | TOBS-03 | unit | `cd packages/dashboard && pnpm test -- tests/topology/diff.test.ts` | ❌ W0 | ⬜ pending |
| 65-01-04 | 01 | 0 | TOBS-04 | unit | `cd packages/dashboard && pnpm test -- tests/topology/timeline.test.ts` | ❌ W0 | ⬜ pending |
| 65-01-05 | 01 | 0 | TOBS-05 | unit | `cd packages/dashboard && pnpm test -- tests/topology/confidence.test.ts` | ❌ W0 | ⬜ pending |
| 65-01-06 | 01 | 0 | TOBS-06 | unit | `cd packages/dashboard && pnpm test -- tests/topology/proposals.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/topology/api.test.ts` — API route data reading stubs (TOBS-01, TOBS-02)
- [ ] `tests/topology/transform.test.ts` — TopologyGraph JSON to React Flow node/edge conversion (TOBS-01, TOBS-02)
- [ ] `tests/topology/diff.test.ts` — Diff highlight classification logic (TOBS-03)
- [ ] `tests/topology/timeline.test.ts` — Changelog sort and time-travel state (TOBS-04)
- [ ] `tests/topology/confidence.test.ts` — Confidence score data transformation (TOBS-05)
- [ ] `tests/topology/proposals.test.ts` — ProposalSet parsing and archetype access (TOBS-06)
- [ ] Install `@xyflow/react` and `@dagrejs/dagre` dev dependencies

*Note: React Flow and Recharts component rendering tests are manual-only (browser visual verification). The unit tests above cover data transformation and API logic.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive DAG renders with correct visual styles | TOBS-01 | React Flow renders in browser canvas | Navigate to /topology, verify nodes display with level colors and edges with correct line styles |
| Side-by-side proposed/approved layout | TOBS-02 | Visual layout verification | With pending proposals, verify left panel shows proposed topology, right shows approved |
| Diff highlights appear on both panels | TOBS-02 | Visual color verification | Compare proposed vs approved, verify green/red/yellow highlights on correct nodes |
| Timeline card expand/collapse | TOBS-04 | Animation and interaction | Click correction events in timeline, verify structural diff expands |
| Time-travel graph updates | TOBS-04 | Interactive browser behavior | Click different timeline events, verify topology graph changes to show historical state |
| Confidence chart renders multi-series lines | TOBS-05 | Recharts SVG rendering | Verify 3 archetype lines + dashed preference_fit line render with correct colors |
| Multi-proposal comparison layout | TOBS-06 | Visual layout with rubric gauges | Verify all 3 archetype cards show side-by-side with rubric score badges |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
