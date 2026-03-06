# Dashboard Optimization Design

**Date:** 2026-03-06
**Scope:** OpenClaw OCCC Dashboard (`packages/dashboard/`)
**Approach:** Fix first, then build (Option A)

---

## Problem Statement

The dashboard has pervasive issues across all pages: a mix of errors/crashes and stale/wrong data. Before adding new functionality, the codebase needs a systematic audit and stabilization pass.

---

## Phase 1: Audit

A structured diagnostic sweep producing a prioritized `AUDIT.md` bug log.

**Audit steps:**
1. **Build & type check** — `tsc --noEmit` and `next build` to surface compile-time errors
2. **API route sweep** — test all 46+ API endpoints; log 404s, errors, and empty/stale responses
3. **Page-by-page walkthrough** — dev server, every page, capture console errors and broken components
4. **SSE/real-time** — verify `useLiveEvents` connects, events flow, fallback polling activates correctly
5. **Hook audit** — identify SWR hooks hitting dead or broken endpoints

**Output:** `AUDIT.md` with bugs categorized as:
- P1: Crashes / errors (blockers)
- P2: Stale or wrong data
- P3: Cosmetic / minor

---

## Phase 2: Fix

Fixes worked in priority order from the audit log.

**P1 — Errors & crashes:**
- Broken API routes repaired at source
- Component render errors fixed (null checks, prop types, undefined data)
- SSE connection failures resolved (EventSource lifecycle, reconnect logic)

**P2 — Data correctness:**
- Stale SWR fetches traced to API endpoints and fixed
- Python snapshot integration verified (metrics merge, age tracking)
- ProjectContext per-project scoping verified across all pages

**P3 — Stability hardening:**
- Silent error swallowing in metrics API replaced with visible error states
- Dark mode consistency pass

Each fix includes a test update or addition to prevent regressions.

---

## Phase 3: Features

Three new capabilities added on top of a stable foundation.

### Real-time Agent Monitoring
- Live L1/L2/L3 agent hierarchy panel with current status (idle, running, blocked)
- Container-level metrics (CPU, memory) via existing Dockerode integration
- Extends SwarmStatusPanel in Mission Control — no new pages

### Task Visibility (End-to-End)
- Task timeline: L1 dispatch → L2 assignment → L3 execution → completion
- Builds on existing PipelineSection/PipelineStrip components
- Task detail drill-down: logs, diffs, branch info, duration

### Alerting & Notifications
- In-app alert feed: agent failures, escalations, task timeouts, API errors
- Extends LiveEventFeed + AttentionQueue (no new SSE channel)
- Toast notifications for urgent events (react-toastify already installed)

---

## Constraints

- No new npm dependencies unless strictly necessary
- All new features reuse existing infrastructure (SWR, SSE, Dockerode, react-toastify)
- Each fix and feature must have test coverage

---

## Key Files

| Area | Path |
|------|------|
| Dashboard root | `packages/dashboard/` |
| API routes | `packages/dashboard/src/app/api/` |
| Components | `packages/dashboard/src/components/` |
| Hooks | `packages/dashboard/src/lib/hooks/` |
| Tests | `packages/dashboard/tests/` |
| State engine | `packages/orchestration/src/openclaw/state_engine.py` |
