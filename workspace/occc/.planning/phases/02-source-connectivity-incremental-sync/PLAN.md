# Phase 02 Plan Index: Source Connectivity & Incremental Sync

This phase is split into five executable plans for reliable connector delivery with resumable sync and UI health visibility:

- `02-01-PLAN.md` (Wave 1): connector runtime contracts, checkpoints, health classification, and shared sync engine.
- `02-02-PLAN.md` (Wave 2): Slack workspace connect, channel scope, and incremental sync integration.
- `02-03-PLAN.md` (Wave 2): tracker connect (GitHub/Linear) and incremental issue metadata sync.
- `02-04-PLAN.md` (Wave 3): sync dashboard + compact indicator, progress telemetry, and recovery UX.
- `02-05-PLAN.md` (Wave 4): background sync scheduler for automatic periodic refreshes.

## Wave Structure

- Wave 1: `02-01-PLAN.md`
- Wave 2: `02-02-PLAN.md`, `02-03-PLAN.md` (both depend on Wave 1)
- Wave 3: `02-04-PLAN.md` (depends on Wave 2 connector surfaces)
- Wave 4: `02-05-PLAN.md` (depends on Wave 3 visibility and stable engine)

## Requirements Coverage

- `INTG-01`: `02-02-PLAN.md`
- `INTG-02`: `02-03-PLAN.md`
- `INTG-03`: `02-01-PLAN.md`, `02-02-PLAN.md`, `02-03-PLAN.md`, `02-04-PLAN.md`, `02-05-PLAN.md`
- `INTG-04`: `02-01-PLAN.md`, `02-04-PLAN.md`, `02-05-PLAN.md`
- `PERF-02`: `02-01-PLAN.md`, `02-04-PLAN.md`, `02-05-PLAN.md`
