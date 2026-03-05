---
phase: 74
slug: dashboard-streaming-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 74 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 3.2.4 |
| **Config file** | `packages/dashboard/vitest.config.ts` |
| **Quick run command** | `cd packages/dashboard && pnpm test` |
| **Full suite command** | `cd packages/dashboard && pnpm test` |
| **Estimated runtime** | ~5 seconds |

> **Note:** `vitest.config.ts` uses `environment: 'node'`. DOM component rendering tests require `jsdom`. DASH-01 and DASH-03 streaming/scroll behaviors require manual smoke-test. DASH-02 prop logic can be tested as pure TypeScript.

---

## Sampling Rate

- **After every task commit:** Run `cd packages/dashboard && pnpm test`
- **After every plan wave:** Run `cd packages/dashboard && pnpm test` + manual smoke-test checklist
- **Before `/gsd:verify-work`:** Full suite must be green + manual streaming verification complete
- **Max feedback latency:** ~5 seconds (automated) + manual checklist time

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 74-01-01 | 01 | 0 | DASH-02 | unit (prop logic) | `pnpm test -- tests/components/tasks/TaskCard.test.ts` | ❌ W0 | ⬜ pending |
| 74-01-02 | 01 | 1 | DASH-02 | unit + smoke | `pnpm test` + manual | ✅ (after W0) | ⬜ pending |
| 74-01-03 | 01 | 1 | DASH-01 | smoke (manual) | manual checklist | N/A | ⬜ pending |
| 74-01-04 | 01 | 1 | DASH-03 | unit + smoke | `pnpm test -- tests/lib/logViewer-utils.test.ts` + manual | ✅ (existing) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/components/tasks/TaskCard.test.ts` — covers DASH-02 isSelected prop: TypeScript compilation, className string output with `isSelected=true` vs `isSelected=false` (pure logic, no DOM render needed)

*Existing `tests/lib/logViewer-utils.test.ts` already covers DASH-03 merge logic — no new file needed for that.*

---

## Manual Smoke-Test Checklist

Required for DASH-01, DASH-02 visual states, and DASH-03 scroll behavior. Run at end of Wave 1 with dashboard at `http://localhost:6987` and active orchestration.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Panel appears on click within 500ms | DASH-02 | React render timing — no DOM test env | Click task card, confirm panel visible within 500ms |
| Selected card shows blue ring/tint | DASH-02 | Visual state — no DOM test env | Click task, confirm clicked card has blue visual indicator |
| Terminal panel renders with SSE stream | DASH-01 | Requires live SSE + browser | Open in_progress task, confirm "Connected" and streaming lines |
| Completed task shows stored log | DASH-01 | Requires live task + browser | Open completed task, confirm activity_log shown |
| Scroll-up pauses auto-scroll | DASH-03 | Requires browser scroll events | Scroll up in active stream, confirm "↓ scroll to resume" appears |
| Scroll-to-bottom resumes auto-scroll (no button) | DASH-03 | Requires browser scroll events | Scroll to bottom naturally, confirm indicator disappears |
| Task switch resets selected state + buffer | DASH-02/01 | Requires interaction | Click task A, scroll up, click task B — confirm panel switches, indicator gone |
| Close button dismisses panel | DASH-01 | Visual | Click ×, confirm panel gone, no task shows selected state |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s (automated); manual checklist separate
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
