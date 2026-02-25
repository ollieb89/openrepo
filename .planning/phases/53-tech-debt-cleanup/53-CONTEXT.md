---
phase: 53-tech-debt-cleanup
created: 2026-02-25
---

# Phase 53: Tech Debt Cleanup — Context

## Purpose

Close accumulated tech debt items identified during the v1.5 milestone audit. These are minor cleanup items that don't affect functionality but create friction (stale error messages, startup warnings, poor small-dataset UX).

## Source

Items extracted from `.planning/v1.5-MILESTONE-AUDIT.md` tech debt section:

| Item | Source Phase | Issue | Location |
|------|--------------|-------|----------|
| Stale error message | 45 | References `project_config.get_state_path()` which no longer exists | `migrate_state.py:107` |
| Residual config field | 46 | `wizard` object triggers unknown-field warning on every startup | `openclaw.json` lines 6-11 |
| Aggressive thresholds | 52 | `MIN_CLUSTER_SIZE=3` produces 0 suggestions on small datasets | `suggest.py:30` |

## Why Now

- v1.5 core requirements are complete
- These are quick fixes (estimated 15-30 minutes total)
- Cleaning debt before milestone completion keeps the codebase healthy
- No new requirements — just closing gaps from audit

## Scope

**In scope:**
- Fix stale error message in migrate_state.py
- Remove `wizard` field from openclaw.json
- Tune suggest.py thresholds for small datasets

**Out of scope:**
- Phase 52 T3 conflict panel (requires memU architectural change)
- Phase 52 T2 archive flag semantics (by design — staleness is age-based)
- Phase 50 Notion live verification (requires credentials)

## Dependencies

- Phase 49 complete (v1.5 core)
- Access to migrate_state.py, openclaw.json, suggest.py

## Success Criteria

1. `migrate_state.py` error message references `config.get_state_path()`
2. `openclaw.json` validates without unknown-field warnings
3. `suggest.py` generates suggestions on datasets with 2-9 memories

## Related Documents

- `.planning/v1.5-MILESTONE-AUDIT.md` — source of tech debt items
- `packages/orchestration/src/openclaw/cli/migrate_state.py` — file to modify
- `openclaw.json` — file to modify
- `packages/orchestration/src/openclaw/cli/suggest.py` — file to modify
