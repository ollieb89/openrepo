# Phase 01 Plan Index: Local-First Core & Privacy Guardrails

This phase is split into four executable plans to keep scope sane and reduce execution risk:

- `01-01-PLAN.md` (Wave 1): privacy guard, project-scoped consent, secure remote transport.
- `01-02-PLAN.md` (Wave 2): Privacy Center, audit log, inline badges, and explicit deny-path messaging.
- `01-03-PLAN.md` (Wave 2): metadata-minimization and provenance defaults.
- `01-04-PLAN.md` (Wave 3, gap closure): enforce runtime inference entry through privacy guard and add regression wiring coverage.

## Wave Structure

- Wave 1: `01-01-PLAN.md`
- Wave 2: `01-02-PLAN.md`, `01-03-PLAN.md` (both depend on Wave 1)
- Wave 3: `01-04-PLAN.md` (depends on Wave 2 runtime surface completion)

## Requirements Coverage

- `PRIV-01`: `01-01-PLAN.md`, `01-03-PLAN.md`
- `PRIV-02`: `01-01-PLAN.md`, `01-02-PLAN.md`, `01-04-PLAN.md`
- `PRIV-03`: `01-03-PLAN.md`
